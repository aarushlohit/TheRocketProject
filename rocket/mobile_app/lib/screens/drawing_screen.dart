import 'dart:async';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/app_theme.dart';
import '../services/nova_socket_service.dart';

class DrawingScreen extends StatefulWidget {
  const DrawingScreen({
    required this.socketService,
    super.key,
  });

  final NovaSocketService socketService;

  @override
  State<DrawingScreen> createState() => _DrawingScreenState();
}

class _DrawingScreenState extends State<DrawingScreen> {
  final List<Offset?> _points = <Offset?>[];
  bool _sending = false;
  bool _announced = false;
  
  // Triple-tap confirmation state (only UI state, tap counting in service)
  bool _waitingForConfirmation = false;
  String _confirmationMessage = '';

  @override
  void initState() {
    super.initState();
    print("[DRAWING SCREEN] initState - adding listener to socket service");
    
    // Clear cache and announce once
    widget.socketService.tts.clearSpokenCache();
    
    // Listen for confirmation requests
    widget.socketService.addListener(_onSocketUpdate);
    print("[DRAWING SCREEN] Listener added successfully");
    
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_announced) {
        _announced = true;
        widget.socketService.tts.speakOnce(
          'Drawing mode. Draw your command, then double tap to send.',
        );
        widget.socketService.haptic.executionStart();
      }
    });
  }
  
  @override
  void dispose() {
    widget.socketService.removeListener(_onSocketUpdate);
    super.dispose();
  }
  
  /// Handle socket service updates for confirmation requests
  void _onSocketUpdate() {
    final pendingConfirmation = widget.socketService.pendingConfirmation;
    print("[SOCKET UPDATE] Pending confirmation: ${pendingConfirmation?.confirmationId}");
    
    if (pendingConfirmation != null) {
      print("[SOCKET UPDATE] Setting waiting for confirmation to TRUE");
      setState(() {
        _waitingForConfirmation = true;
        _confirmationMessage = pendingConfirmation.action;
      });
      
      // Speak the confirmation request
      widget.socketService.tts.speak(
        'Triple tap the canvas to confirm ${pendingConfirmation.action}',
      );
      return;
    }

    if (_waitingForConfirmation) {
      print("[SOCKET UPDATE] Clearing waiting for confirmation");
      setState(() {
        _waitingForConfirmation = false;
        _confirmationMessage = '';
      });
    }
  }
  
  /// Handle tap for triple-tap detection (delegates to service for rebuild safety)
  void _onCanvasTap() {
    print("[TAP] Canvas tapped. Waiting for confirmation: $_waitingForConfirmation");
    
    if (!_waitingForConfirmation) {
      print("[TAP] Ignoring tap - not waiting for confirmation");
      return;
    }
    
    // Delegate to service for global tap counting (rebuild-safe)
    widget.socketService.registerTap(() {
      _confirmAction();
    });
  }
  
  /// Confirm the pending action via triple tap
  void _confirmAction() {
    final pendingConfirmation = widget.socketService.pendingConfirmation;
    if (pendingConfirmation == null) {
      print("[TRIPLE TAP] No pending confirmation found");
      setState(() {
        _waitingForConfirmation = false;
      });
      return;
    }
    
    print("[TRIPLE TAP] Sending confirmation for ID: ${pendingConfirmation.confirmationId}");
    widget.socketService.sendTripleTapConfirm(
      pendingConfirmation.confirmationId,
      source: pendingConfirmation.source,
    );
    
    setState(() {
      _waitingForConfirmation = false;
      _confirmationMessage = '';
    });
  }

  void _addPoint(Offset point) {
    setState(() {
      _points.add(point);
    });
  }

  void _finishStroke() {
    setState(() {
      _points.add(null);
    });
    widget.socketService.haptic.selection();
  }

  void _clearCanvas() {
    setState(() {
      _points.clear();
    });
    widget.socketService.tts.speakOnce('Canvas cleared');
    widget.socketService.haptic.tap();
  }

  Future<void> _sendDrawing(Size size) async {
    if (_waitingForConfirmation) {
      widget.socketService.tts.speakConfirmation(
        'Confirmation is pending. Triple tap in the drawing canvas to continue.',
      );
      widget.socketService.haptic.confirmation();
      return;
    }

    if (_points.every((Offset? point) => point == null) || _sending) {
      widget.socketService.tts.speakOnce('Nothing to send. Please draw first.');
      widget.socketService.haptic.error();
      return;
    }

    setState(() {
      _sending = true;
    });

    try {
      widget.socketService.tts.speak('Analyzing drawing');
      final Uint8List imageBytes = await _renderPng(size);
      await widget.socketService.sendDrawing(imageBytes);
      if (!mounted) return;
      setState(() {
        _points.clear();
      });
    } catch (error) {
      if (!mounted) return;
      widget.socketService.tts.speakError('Send failed: $error');
      widget.socketService.haptic.error();
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  Future<Uint8List> _renderPng(Size size) async {
    final ui.PictureRecorder recorder = ui.PictureRecorder();
    final Canvas canvas = Canvas(recorder);
    final Paint backgroundPaint = Paint()..color = Colors.white;
    final Paint strokePaint = Paint()
      ..color = AppTheme.textPrimary
      ..strokeWidth = 6
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    canvas.drawRect(Offset.zero & size, backgroundPaint);

    for (int index = 0; index < _points.length - 1; index += 1) {
      final Offset? current = _points[index];
      final Offset? next = _points[index + 1];
      if (current != null && next != null) {
        canvas.drawLine(current, next, strokePaint);
      }
    }

    final ui.Image image = await recorder
        .endRecording()
        .toImage(size.width.ceil(), size.height.ceil());
    final ByteData? byteData = await image.toByteData(
      format: ui.ImageByteFormat.png,
    );
    if (byteData == null) {
      throw StateError('Could not encode drawing');
    }
    return byteData.buffer.asUint8List();
  }

  @override
  Widget build(BuildContext context) {
    print("[BUILD] Drawing screen building. _waitingForConfirmation = $_waitingForConfirmation");
    print("[BUILD] _confirmationMessage = $_confirmationMessage");
    
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Stack(
          children: [
            // Drawing canvas
            LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final Size canvasSize = Size(
                  constraints.maxWidth,
                  constraints.maxHeight,
                );

                return Semantics(
                  label: _waitingForConfirmation
                      ? 'Confirmation required. Triple tap to confirm.'
                      : 'Drawing canvas. Double tap to send.',
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onPanStart: (details) {
                      if (_waitingForConfirmation) {
                        // When waiting for confirmation, treat any tap-like gesture as tap
                        print("[PAN START] Treating as tap during confirmation");
                        _onCanvasTap();
                      } else {
                        _addPoint(details.localPosition);
                      }
                    },
                    onPanUpdate: (details) {
                      if (!_waitingForConfirmation) {
                        _addPoint(details.localPosition);
                      }
                    },
                    onPanEnd: (_) {
                      if (!_waitingForConfirmation) {
                        _finishStroke();
                      }
                    },
                    onDoubleTap: () => _sendDrawing(canvasSize),
                    onTap: () {
                      print("[ON TAP] Direct tap detected");
                      _onCanvasTap();
                    },
                    child: CustomPaint(
                      size: Size.infinite,
                      painter: _DrawingPainter(_points),
                    ),
                  ),
                );
              },
            ),

            // Top bar
            Positioned(
              top: AppTheme.spacingM,
              left: AppTheme.spacingM,
              right: AppTheme.spacingM,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // Back button
                  _buildIconButton(
                    icon: Icons.arrow_back_rounded,
                    label: 'Go back',
                    onTap: () {
                      widget.socketService.haptic.tap();
                      Navigator.of(context).pop();
                    },
                  ),

                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Confirmation status indicator (small dot)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: _waitingForConfirmation
                              ? AppTheme.success
                              : Colors.grey.shade700,
                          borderRadius: BorderRadius.circular(20),
                          boxShadow: [
                            BoxShadow(
                              color: (_waitingForConfirmation
                                      ? AppTheme.success
                                      : Colors.grey.shade700)
                                  .withOpacity(0.3),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              _waitingForConfirmation
                                  ? Icons.check_circle
                                  : Icons.circle,
                              color: Colors.white,
                              size: 16,
                            ),
                            if (_waitingForConfirmation) ...[
                              const SizedBox(width: 6),
                              Text(
                                'Tap 3x',
                                style: AppTheme.bodySmall.copyWith(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      
                      // Connection status
                      ListenableBuilder(
                        listenable: widget.socketService,
                        builder: (context, _) {
                          final connected = widget.socketService.status ==
                              NovaConnectionStatus.connected;
                          return Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 8,
                            ),
                            decoration: BoxDecoration(
                              color: connected
                                  ? AppTheme.success
                                  : AppTheme.error,
                              borderRadius: BorderRadius.circular(20),
                              boxShadow: [
                                BoxShadow(
                                  color: (connected ? AppTheme.success : AppTheme.error)
                                      .withOpacity(0.3),
                                  blurRadius: 8,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  connected ? Icons.wifi : Icons.wifi_off,
                                  color: Colors.white,
                                  size: 16,
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Sending indicator
            if (_sending)
              Positioned.fill(
                child: Container(
                  color: AppTheme.textPrimary.withOpacity(0.7),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const CircularProgressIndicator(
                          color: AppTheme.primary,
                          strokeWidth: 3,
                        ),
                        const SizedBox(height: AppTheme.spacingM),
                        Text(
                          'Processing...',
                          style: AppTheme.bodyLarge.copyWith(
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildIconButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return Semantics(
      button: true,
      label: label,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppTheme.textPrimary,
            borderRadius: BorderRadius.circular(14),
            boxShadow: [
              BoxShadow(
                color: AppTheme.textPrimary.withOpacity(0.3),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Icon(
            icon,
            color: Colors.white,
            size: 22,
          ),
        ),
      ),
    );
  }
}

class _DrawingPainter extends CustomPainter {
  const _DrawingPainter(this.points);

  final List<Offset?> points;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = AppTheme.textPrimary
      ..strokeWidth = 6
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    for (int index = 0; index < points.length - 1; index += 1) {
      final Offset? current = points[index];
      final Offset? next = points[index + 1];
      if (current != null && next != null) {
        canvas.drawLine(current, next, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _DrawingPainter oldDelegate) {
    return oldDelegate.points != points;
  }
}
