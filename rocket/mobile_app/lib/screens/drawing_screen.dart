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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.socketService.tts.speakOnce(
        'Drawing mode. Draw your command, then double tap anywhere on the canvas to send.',
      );
      widget.socketService.haptic.executionStart();
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
    if (_points.every((point) => point == null) || _sending) {
      await widget.socketService.tts.speakOnce('Nothing to send. Please draw first.');
      await widget.socketService.haptic.error();
      return;
    }

    setState(() {
      _sending = true;
    });

    try {
      await widget.socketService.tts.speakFeedback('Drawing sent');
      final imageBytes = await _renderPng(size);
      await widget.socketService.sendDrawing(imageBytes);
      if (!mounted) return;
      setState(() {
        _points.clear();
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

    final image = await recorder.endRecording().toImage(size.width.ceil(), size.height.ceil());
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
                final canvasSize = Size(constraints.maxWidth, constraints.maxHeight);
                return Semantics(
                  label: 'Drawing canvas. Double tap to send.',
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onPanStart: (details) => _addPoint(details.localPosition),
                    onPanUpdate: (details) => _addPoint(details.localPosition),
                    onPanEnd: (_) => _finishStroke(),
                    onDoubleTap: () => _sendDrawing(canvasSize),
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
            if (_sending)
              Positioned.fill(
                child: Container(
                  color: AppTheme.textPrimary.withValues(alpha: 0.72),
                  child: Center(
                    child: Text(
                      'Processing...',
                      style: AppTheme.headingSmall.copyWith(color: Colors.white),
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
          constraints: const BoxConstraints(minWidth: 56, minHeight: 56),
          decoration: BoxDecoration(
            color: AppTheme.textPrimary,
            borderRadius: BorderRadius.circular(12),
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
