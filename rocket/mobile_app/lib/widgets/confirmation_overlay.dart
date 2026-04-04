import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/app_theme.dart';
import '../services/nova_socket_service.dart';
import '../services/tts_service.dart';

/// Accessible overlay for confirmation requests
class ConfirmationOverlay extends StatefulWidget {
  const ConfirmationOverlay({
    required this.socketService,
    required this.request,
    super.key,
  });

  final NovaSocketService socketService;
  final ConfirmationRequest request;

  @override
  State<ConfirmationOverlay> createState() => _ConfirmationOverlayState();
}

class _ConfirmationOverlayState extends State<ConfirmationOverlay>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;
  double _remainingTime = 30.0;
  bool _responded = false;
  bool _announced = false;

  final List<DateTime> _confirmTapTimestamps = <DateTime>[];

  static const int _requiredConfirmTaps = 3;
  static const Duration _confirmTapWindow = Duration(seconds: 2);

  @override
  void initState() {
    super.initState();
    _remainingTime = widget.request.timeout;

    _animationController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _scaleAnimation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.elasticOut,
    );
    _animationController.forward();

    _startCountdown();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_announced) return;
      _announced = true;
      widget.socketService.tts.speak(
        'Confirmation required. ${widget.request.action}. '
        'Triple tap to confirm or cancel.',
        priority: TtsPriority.critical,
      );
      widget.socketService.haptic.confirmation();
    });
  }

  void _startCountdown() {
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 1));
      if (!mounted || _responded) return false;

      setState(() {
        _remainingTime -= 1;
      });

      if (_remainingTime <= 0) {
        _handleTimeout();
        return false;
      }

      if (_remainingTime == 10 || _remainingTime == 5) {
        widget.socketService.tts.speak('${_remainingTime.toInt()} seconds');
      }

      return true;
    });
  }

  void _handleTimeout() {
    if (_responded) return;
    _responded = true;
    widget.socketService.cancelConfirmation(
      widget.request.confirmationId,
      source: widget.request.source,
    );
    widget.socketService.tts.speakError('Timed out. Action cancelled.');
    widget.socketService.haptic.error();
  }

  void _confirm() {
    if (_responded) return;
    _responded = true;
    HapticFeedback.heavyImpact();
    widget.socketService.sendConfirmation(
      widget.request.confirmationId,
      true,
      source: widget.request.source,
    );
  }

  void _cancel() {
    if (_responded) return;
    _responded = true;
    HapticFeedback.mediumImpact();
    widget.socketService.sendConfirmation(
      widget.request.confirmationId,
      false,
      source: widget.request.source,
    );
  }

  void _registerConfirmTap() {
    if (_responded) return;

    final now = DateTime.now();
    _confirmTapTimestamps.removeWhere(
      (timestamp) => now.difference(timestamp) > _confirmTapWindow,
    );
    _confirmTapTimestamps.add(now);

    final remaining = _requiredConfirmTaps - _confirmTapTimestamps.length;
    if (remaining <= 0) {
      _confirmTapTimestamps.clear();
      _confirm();
      return;
    }

    widget.socketService.haptic.selection();
    if (remaining == 1) {
      widget.socketService.tts.speakOnce('One more tap to confirm');
    } else {
      widget.socketService.tts.speakOnce('$remaining more taps to confirm');
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.textPrimary.withOpacity(0.9),
      child: SafeArea(
        child: ScaleTransition(
          scale: _scaleAnimation,
          child: GestureDetector(
            onHorizontalDragEnd: (details) {
              if (details.primaryVelocity != null &&
                  details.primaryVelocity!.abs() > 200) {
                _cancel();
              }
            },
            child: Semantics(
              liveRegion: true,
              label: 'Confirmation required. ${widget.request.action}. '
                  'Triple tap confirm or cancel.',
              child: Padding(
                padding: const EdgeInsets.all(AppTheme.spacingL),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: AppTheme.warning.withOpacity(0.2),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.warning_amber_rounded,
                        size: 64,
                        color: AppTheme.warning,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacingXL),
                    Text(
                      'Confirmation Required',
                      style: AppTheme.headingMedium.copyWith(
                        color: Colors.white,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: AppTheme.spacingM),
                    Container(
                      padding: const EdgeInsets.all(AppTheme.spacingM),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Text(
                        widget.request.action,
                        style: AppTheme.bodyLarge.copyWith(
                          color: Colors.white,
                          fontFamily: 'monospace',
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacingL),
                    Text(
                      '${_remainingTime.toInt()} seconds',
                      style: AppTheme.headingSmall.copyWith(
                        color: _remainingTime <= 10
                            ? AppTheme.warning
                            : Colors.white70,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacingS),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: _remainingTime / widget.request.timeout,
                        backgroundColor: Colors.white.withOpacity(0.2),
                        valueColor: AlwaysStoppedAnimation(
                          _remainingTime <= 10
                              ? AppTheme.warning
                              : AppTheme.primary,
                        ),
                        minHeight: 6,
                      ),
                    ),
                    const SizedBox(height: AppTheme.spacingXL),
                    Row(
                      children: [
                        Expanded(
                          child: Semantics(
                            button: true,
                            label: 'Cancel action',
                            child: GestureDetector(
                              onTap: () {
                                widget.socketService.tts.speakOnce('Double tap to cancel');
                                widget.socketService.haptic.selection();
                              },
                              onDoubleTap: _cancel,
                              child: Container(
                                padding: const EdgeInsets.symmetric(vertical: 18),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(16),
                                  border: Border.all(
                                    color: Colors.white.withOpacity(0.3),
                                    width: 2,
                                  ),
                                ),
                                child: Center(
                                  child: Text(
                                    'Cancel',
                                    style: AppTheme.buttonText.copyWith(
                                      color: Colors.white,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: AppTheme.spacingM),
                        Expanded(
                          child: Semantics(
                            button: true,
                            label: 'Confirm action with triple tap',
                            child: GestureDetector(
                              onTap: _registerConfirmTap,
                              child: Container(
                                padding: const EdgeInsets.symmetric(vertical: 18),
                                decoration: BoxDecoration(
                                  color: AppTheme.success,
                                  borderRadius: BorderRadius.circular(16),
                                  boxShadow: [
                                    BoxShadow(
                                      color: AppTheme.success.withOpacity(0.4),
                                      blurRadius: 16,
                                      offset: const Offset(0, 4),
                                    ),
                                  ],
                                ),
                                child: const Center(
                                  child: Text(
                                    'Confirm',
                                    style: AppTheme.buttonText,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppTheme.spacingL),
                    Text(
                      'Triple tap to confirm - Swipe to cancel',
                      style: AppTheme.bodySmall.copyWith(
                        color: Colors.white54,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
