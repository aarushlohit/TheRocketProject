import 'package:flutter/material.dart';

import '../models/app_theme.dart';

/// Elegant splash/loading screen shown on first launch
class SplashScreen extends StatefulWidget {
  const SplashScreen({
    required this.onComplete,
    super.key,
  });

  final VoidCallback onComplete;

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeIn;
  late Animation<double> _scaleUp;
  late Animation<double> _loadingFade;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      duration: const Duration(milliseconds: 1800),
      vsync: this,
    );

    // Logo fade in (0-40%)
    _fadeIn = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.0, 0.4, curve: Curves.easeOut),
      ),
    );

    // Logo scale up (0-50%)
    _scaleUp = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.0, 0.5, curve: Curves.elasticOut),
      ),
    );

    // Loading indicator fade in (40-60%)
    _loadingFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.4, 0.6, curve: Curves.easeIn),
      ),
    );

    _controller.forward();

    // Navigate after animation + brief delay
    Future.delayed(const Duration(milliseconds: 2200), () {
      if (mounted) {
        widget.onComplete();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: Center(
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            return Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Logo with fade + scale
                Transform.scale(
                  scale: _scaleUp.value,
                  child: Opacity(
                    opacity: _fadeIn.value,
                    child: Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.rocket_launch_rounded,
                        size: 64,
                        color: AppTheme.primary,
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: AppTheme.spacingL),

                // App name
                Opacity(
                  opacity: _fadeIn.value,
                  child: Text(
                    'Rocket',
                    style: AppTheme.headingLarge.copyWith(
                      color: AppTheme.textPrimary,
                      letterSpacing: 1.5,
                    ),
                  ),
                ),

                const SizedBox(height: AppTheme.spacingS),

                // Tagline
                Opacity(
                  opacity: _fadeIn.value,
                  child: Text(
                    'Accessibility First',
                    style: AppTheme.bodyMedium.copyWith(
                      color: AppTheme.textMuted,
                    ),
                  ),
                ),

                const SizedBox(height: AppTheme.spacingXXL),

                // Loading indicator
                Opacity(
                  opacity: _loadingFade.value,
                  child: SizedBox(
                    width: 32,
                    height: 32,
                    child: CircularProgressIndicator(
                      strokeWidth: 3,
                      valueColor: AlwaysStoppedAnimation(
                        AppTheme.primary.withValues(alpha: 0.7),
                      ),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
