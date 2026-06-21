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
  bool _strokeHasInk = false;
  int _tapCount = 0;
  Timer? _tapTimer;
  String? _lastSpokenTask;

  @override
  void initState() {
    super.initState();
    widget.socketService.addListener(_handleSocketUpdate);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.socketService.tts.speakOnce(
        'Drawing mode. Draw your command, then double tap anywhere on the canvas to send.',
      );
      widget.socketService.haptic.executionStart();
    });
  }

  @override
  void dispose() {
    widget.socketService.removeListener(_handleSocketUpdate);
    _tapTimer?.cancel();
    super.dispose();
  }

  void _handleSocketUpdate() {
    final task = widget.socketService.lastTask;
    if (task == null ||
        task.source != 'drawing' ||
        task.task == _lastSpokenTask) {
      return;
    }
    _lastSpokenTask = task.task;
    widget.socketService.tts.speakResult('Intent recognized. ${task.task}');
    widget.socketService.tts.speakFeedback('Task sent');
    widget.socketService.haptic.success();
  }

  void _addPoint(Offset point) {
    setState(() {
      _points.add(point);
      _strokeHasInk = true;
    });
  }

  void _finishStroke() {
    setState(() {
      _points.add(null);
      if (_strokeHasInk) {
        _strokeHasInk = false;
      }
    });
  }

  void _clearCanvas() {
    setState(() {
      _points.clear();
      _strokeHasInk = false;
    });
    widget.socketService.tts.speakOnce('Canvas cleared');
    widget.socketService.haptic.tap();
  }

  void _undoLastStroke() {
    if (_points.isEmpty) return;
    setState(() {
      while (_points.isNotEmpty && _points.last == null) {
        _points.removeLast();
      }
      while (_points.isNotEmpty && _points.last != null) {
        _points.removeLast();
      }
      _strokeHasInk = false;
    });
    widget.socketService.tts.speakOnce('Undo');
    widget.socketService.haptic.tap();
  }

  void _handleCanvasTap(Size size) {
    _tapCount += 1;
    _tapTimer?.cancel();
    _tapTimer = Timer(const Duration(milliseconds: 320), () {
      final count = _tapCount;
      _tapCount = 0;
      if (count >= 4) {
        _clearCanvas();
      } else if (count == 3) {
        _undoLastStroke();
      } else if (count == 2) {
        _sendDrawing(size);
      }
    });
  }

  Future<void> _sendDrawing(Size size) async {
    if (_points.every((point) => point == null) || _sending) {
      await widget.socketService.tts
          .speakOnce('Nothing to send. Please draw first.');
      await widget.socketService.haptic.error();
      return;
    }

    setState(() {
      _sending = true;
    });

    try {
      await widget.socketService.tts.speakFeedback('Drawing received');
      final imageBytes = await _renderPng(size);
      await widget.socketService.sendDrawing(imageBytes);
      if (!mounted) return;
      setState(() {
        _points.clear();
        _strokeHasInk = false;
      });
    } catch (error) {
      if (!mounted) return;
      await widget.socketService.tts.speakError('Send failed: $error');
      await widget.socketService.haptic.error();
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  Future<Uint8List> _renderPng(Size size) async {
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);
    final backgroundPaint = Paint()..color = Colors.white;
    final strokePaint = Paint()
      ..color = AppTheme.textPrimary
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    canvas.drawRect(Offset.zero & size, backgroundPaint);
    for (int index = 0; index < _points.length - 1; index += 1) {
      final current = _points[index];
      final next = _points[index + 1];
      if (current != null && next != null) {
        canvas.drawLine(current, next, strokePaint);
      }
    }

    final image = await recorder
        .endRecording()
        .toImage(size.width.ceil(), size.height.ceil());
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    if (byteData == null) {
      throw StateError('Could not encode drawing');
    }
    return byteData.buffer.asUint8List();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Stack(
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                final canvasSize =
                    Size(constraints.maxWidth, constraints.maxHeight);
                return Semantics(
                  label:
                      'Drawing canvas. Double tap to analyze. Triple tap to undo. Quadruple tap to clear.',
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onPanStart: (details) => _addPoint(details.localPosition),
                    onPanUpdate: (details) => _addPoint(details.localPosition),
                    onPanEnd: (_) => _finishStroke(),
                    onDoubleTap: () => _sendDrawing(canvasSize),
                    onTap: () => _handleCanvasTap(canvasSize),
                    child: CustomPaint(
                      size: Size.infinite,
                      painter: _DrawingPainter(_points),
                    ),
                  ),
                );
              },
            ),
            Positioned(
              top: AppTheme.spacingM,
              left: AppTheme.spacingM,
              right: AppTheme.spacingM,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _buildIconButton(
                    icon: Icons.arrow_back_rounded,
                    label: 'Go back',
                    onTap: () {
                      widget.socketService.haptic.tap();
                      Navigator.of(context).pop();
                    },
                  ),
                  _buildIconButton(
                    icon: Icons.delete_outline_rounded,
                    label: 'Clear canvas',
                    onTap: _clearCanvas,
                  ),
                ],
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
          constraints: const BoxConstraints(minWidth: 56, minHeight: 56),
          decoration: BoxDecoration(
            color: AppTheme.textPrimary,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: Colors.white, size: 28),
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
    final gridPaint = Paint()
      ..color = Colors.black.withValues(alpha: 0.06)
      ..strokeWidth = 1;
    const step = 32.0;
    for (double x = 0; x <= size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (double y = 0; y <= size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    final paint = Paint()
      ..color = AppTheme.textPrimary
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    for (int index = 0; index < points.length - 1; index += 1) {
      final current = points[index];
      final next = points[index + 1];
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
