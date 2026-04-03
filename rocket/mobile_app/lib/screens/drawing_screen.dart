import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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

  void _addPoint(Offset point) {
    setState(() {
      _points.add(point);
    });
  }

  void _finishStroke() {
    setState(() {
      _points.add(null);
    });
  }

  Future<void> _sendDrawing(Size size) async {
    if (_points.every((Offset? point) => point == null) || _sending) {
      return;
    }

    setState(() {
      _sending = true;
    });

    HapticFeedback.heavyImpact();

    try {
      final Uint8List imageBytes = await _renderPng(size);
      await widget.socketService.sendDrawing(imageBytes);
      if (!mounted) {
        return;
      }
      setState(() {
        _points.clear();
      });
      final String message =
          widget.socketService.lastResponse?['message']?.toString() ??
              'Drawing sent';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message)),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Send failed: $error')),
      );
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
      ..color = Colors.black
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
    return Scaffold(
      backgroundColor: Colors.white,
      body: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final Size canvasSize = Size(
            constraints.maxWidth,
            constraints.maxHeight,
          );

          return GestureDetector(
            behavior: HitTestBehavior.opaque,
            onPanStart: (DragStartDetails details) => _addPoint(details.localPosition),
            onPanUpdate: (DragUpdateDetails details) =>
                _addPoint(details.localPosition),
            onPanEnd: (_) => _finishStroke(),
            onDoubleTap: () => _sendDrawing(canvasSize),
            child: CustomPaint(
              size: Size.infinite,
              painter: _DrawingPainter(_points),
            ),
          );
        },
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
      ..color = Colors.black
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
