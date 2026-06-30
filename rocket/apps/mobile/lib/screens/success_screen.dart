import 'dart:async';
import 'package:flutter/material.dart';

import '../models/app_theme.dart';
import '../services/haptic_service.dart';
import '../services/tts_service.dart';

/// Success screen with animated checkmark and voice countdown
class SuccessScreen extends StatefulWidget {
  const SuccessScreen({
    required this.ttsService,
    required this.hapticService,
    required this.onComplete,
    super.key,
  });

  final TtsService ttsService;
  final HapticService hapticService;
  final VoidCallback onComplete;

  @override
  State<SuccessScreen> createState() => _SuccessScreenState();
}

class _SuccessScreenState extends State<SuccessScreen>
    with TickerProviderStateMixin {
  late AnimationController _checkController;
  late AnimationController _pulseController;
  late Animation<double> _checkScale;
  late Animation<double> _checkOpacity;
  late Animation<double> _strokeAnimation;
  late Animation<double> _pulseAnimation;
  
  int _countdown = 3;
  bool _countdownStarted = false;

  @override
  void initState() {
    super.initState();

    // Checkmark animation
    _checkController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );

    _checkScale = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _checkController,
        curve: const Interval(0.0, 0.6, curve: Curves.elasticOut),
      ),
    );

    _checkOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _checkController,
        curve: const Interval(0.0, 0.3, curve: Curves.easeOut),
      ),
    );

    _strokeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _checkController,
        curve: const Interval(0.3, 1.0, curve: Curves.easeInOut),
      ),
    );

    // Pulse animation
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    // Start animations
    _checkController.forward().then((_) {
      _pulseController.repeat(reverse: true);
      _startCountdown();
    });

    // Initial haptic
    widget.hapticService.success();
  }

  void _startCountdown() {
    if (_countdownStarted) return;
    _countdownStarted = true;

    // Speak success message first
    widget.ttsService.speak(
      'Setup complete. Moving to home in 3, 2, 1.',
      priority: TtsPriority.high,
    );

    // Start visual countdown after brief delay
    Future.delayed(const Duration(milliseconds: 1000), () {
      _runCountdown();
    });
  }

  void _runCountdown() {
    Timer.periodic(const Duration(milliseconds: 800), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }

      if (_countdown > 0) {
        setState(() => _countdown--);
        widget.hapticService.tap();
      } else {
        timer.cancel();
        widget.onComplete();
      }
    });
  }

  @override
  void dispose() {
    _checkController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Animated checkmark
              AnimatedBuilder(
                animation: Listenable.merge([_checkController, _pulseController]),
                builder: (context, child) {
                  return Transform.scale(
                    scale: _checkScale.value * _pulseAnimation.value,
                    child: Opacity(
                      opacity: _checkOpacity.value,
                      child: Container(
                        width: 140,
                        height: 140,
                        decoration: BoxDecoration(
                          color: AppTheme.success.withValues(alpha: 0.1),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: AppTheme.success.withValues(alpha: 0.2),
                              blurRadius: 30,
                              spreadRadius: 5,
                            ),
                          ],
                        ),
                        child: CustomPaint(
                          painter: _CheckmarkPainter(
                            progress: _strokeAnimation.value,
                            color: AppTheme.success,
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),

              const SizedBox(height: AppTheme.spacingXL),

              // Success text
              Text(
                'Setup Complete',
                style: AppTheme.headingLarge.copyWith(
                  color: AppTheme.textPrimary,
                ),
              ),

              const SizedBox(height: AppTheme.spacingS),

              Text(
                'Your accessibility preferences are saved',
                style: AppTheme.bodyMedium.copyWith(
                  color: AppTheme.textMuted,
                ),
                textAlign: TextAlign.center,
              ),

              const SizedBox(height: AppTheme.spacingXXL),

              // Countdown
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 300),
                transitionBuilder: (child, animation) {
                  return ScaleTransition(scale: animation, child: child);
                },
                child: _countdown > 0
                    ? Column(
                        key: ValueKey(_countdown),
                        children: [
                          Text(
                            'Going to Home in',
                            style: AppTheme.bodyMedium.copyWith(
                              color: AppTheme.textMuted,
                            ),
                          ),
                          const SizedBox(height: AppTheme.spacingS),
                          Container(
                            width: 64,
                            height: 64,
                            decoration: BoxDecoration(
                              color: AppTheme.primary.withValues(alpha: 0.1),
                              shape: BoxShape.circle,
                            ),
                            child: Center(
                              child: Text(
                                '$_countdown',
                                style: AppTheme.headingLarge.copyWith(
                                  color: AppTheme.primary,
                                  fontSize: 36,
                                ),
                              ),
                            ),
                          ),
                        ],
                      )
                    : const SizedBox(height: 100),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Custom painter for animated checkmark
class _CheckmarkPainter extends CustomPainter {
  const _CheckmarkPainter({
    required this.progress,
    required this.color,
  });

  final double progress;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 6
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    final center = Offset(size.width / 2, size.height / 2);
    final checkSize = size.width * 0.35;

    // Define checkmark path
    final start = Offset(center.dx - checkSize * 0.4, center.dy);
    final mid = Offset(center.dx - checkSize * 0.1, center.dy + checkSize * 0.35);
    final end = Offset(center.dx + checkSize * 0.5, center.dy - checkSize * 0.3);

    final path = Path();
    path.moveTo(start.dx, start.dy);

    if (progress <= 0.5) {
      // First stroke (start to mid)
      final t = progress * 2;
      final current = Offset.lerp(start, mid, t)!;
      path.lineTo(current.dx, current.dy);
    } else {
      // First stroke complete, draw second
      path.lineTo(mid.dx, mid.dy);
      final t = (progress - 0.5) * 2;
      final current = Offset.lerp(mid, end, t)!;
      path.lineTo(current.dx, current.dy);
    }

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _CheckmarkPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
