import 'package:flutter/material.dart';

import '../models/app_theme.dart';
import '../models/user_profile.dart';
import '../services/haptic_service.dart';
import '../services/tts_service.dart';

class _GuidanceOption {
  const _GuidanceOption({
    required this.type,
    required this.icon,
    required this.color,
  });

  final DisabilityType type;
  final IconData icon;
  final Color color;
}

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({
    required this.ttsService,
    required this.hapticService,
    required this.onComplete,
    super.key,
  });

  final TtsService ttsService;
  final HapticService hapticService;
  final void Function(UserProfile profile) onComplete;

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final Set<DisabilityType> _selected = {
    DisabilityType.visual,
    DisabilityType.hearing,
    DisabilityType.motor,
  };
  int _page = 0;
  bool _completionScheduled = false;

  static const List<_GuidanceOption> _options = [
    _GuidanceOption(
      type: DisabilityType.visual,
      icon: Icons.record_voice_over_rounded,
      color: AppTheme.cardVisual,
    ),
    _GuidanceOption(
      type: DisabilityType.hearing,
      icon: Icons.vibration_rounded,
      color: AppTheme.cardHearing,
    ),
    _GuidanceOption(
      type: DisabilityType.cognitive,
      icon: Icons.lightbulb_outline_rounded,
      color: AppTheme.cardCognitive,
    ),
    _GuidanceOption(
      type: DisabilityType.motor,
      icon: Icons.touch_app_rounded,
      color: AppTheme.cardMotor,
    ),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.ttsService.speakOnce(
        'Welcome to Rocket. Double tap to continue.',
      );
      widget.hapticService.executionStart();
    });
  }

  void _goNext() {
    widget.hapticService.tap();
    if (_page == 0) {
      setState(() => _page = 1);
      widget.ttsService.speakOnce(
        'Choose preferred guidance. Double tap each option to select or remove it.',
      );
      return;
    }

    if (_page == 1) {
      setState(() => _page = 2);
      widget.ttsService.speakOnce('Setup complete. Launching Rocket.');
      _scheduleComplete();
    }
  }

  void _scheduleComplete() {
    if (_completionScheduled) return;
    _completionScheduled = true;
    Future<void>.delayed(const Duration(milliseconds: 1500), () {
      if (!mounted) return;
      final profile = UserProfile(
        disabilities: _selected,
        voiceFeedback: _selected.contains(DisabilityType.visual),
        hapticFeedback: _selected.contains(DisabilityType.hearing),
        confirmationRequired: true,
        onboardingCompleted: true,
      );
      widget.hapticService.success();
      widget.onComplete(profile);
    });
  }

  void _toggleOption(DisabilityType type) {
    setState(() {
      if (_selected.contains(type)) {
        _selected.remove(type);
      } else {
        _selected.add(type);
      }
    });
    final isSelected = _selected.contains(type);
    widget.ttsService.speakOnce(
      '${type.label} ${isSelected ? "selected" : "removed"}.',
    );
    widget.hapticService.selection();
  }

  void _focusOption(DisabilityType type) {
    final isSelected = _selected.contains(type);
    widget.ttsService.speakOnce(
      '${type.label}. ${type.description}. '
      '${isSelected ? "Selected" : "Not selected"}. Double tap to change.',
    );
    widget.hapticService.selection();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          child: switch (_page) {
            0 => _buildWelcome(),
            1 => _buildGuidance(),
            _ => _buildComplete(),
          },
        ),
      ),
    );
  }

  Widget _buildWelcome() {
    return Padding(
      key: const ValueKey('welcome'),
      padding: const EdgeInsets.all(AppTheme.spacingL),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Spacer(),
          Semantics(
            header: true,
            label: 'Rocket Logo. Welcome to Rocket.',
            child: Center(
              child: Container(
                width: 128,
                height: 128,
                decoration: const BoxDecoration(
                  color: AppTheme.primary,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.rocket_launch_rounded,
                  color: Colors.white,
                  size: 72,
                ),
              ),
            ),
          ),
          const SizedBox(height: AppTheme.spacingXL),
          const Text('Welcome to Rocket', style: AppTheme.headingLarge),
          const SizedBox(height: AppTheme.spacingM),
          Text(
            'Rocket helps blind users control computers.',
            style: AppTheme.bodyLarge.copyWith(color: AppTheme.textSecondary),
          ),
          const Spacer(),
          _DoubleTapButton(
            label: 'Double tap to continue',
            semanticLabel: 'Double tap to continue',
            onTap: () {
              widget.ttsService.speakOnce('Double tap to continue.');
              widget.hapticService.selection();
            },
            onDoubleTap: _goNext,
          ),
        ],
      ),
    );
  }

  Widget _buildGuidance() {
    return Padding(
      key: const ValueKey('guidance'),
      padding: const EdgeInsets.all(AppTheme.spacingL),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            header: true,
            child: const Text(
              'Choose preferred guidance',
              style: AppTheme.headingLarge,
            ),
          ),
          const SizedBox(height: AppTheme.spacingS),
          Text(
            'Multiple selections are allowed.',
            style: AppTheme.bodyLarge.copyWith(color: AppTheme.textSecondary),
          ),
          const SizedBox(height: AppTheme.spacingL),
          Expanded(
            child: GridView.count(
              crossAxisCount: 2,
              mainAxisSpacing: AppTheme.spacingM,
              crossAxisSpacing: AppTheme.spacingM,
              childAspectRatio: 0.92,
              children: _options.map((option) {
                final isSelected = _selected.contains(option.type);
                return Semantics(
                  button: true,
                  selected: isSelected,
                  label: '${option.type.label}. ${option.type.description}. '
                      '${isSelected ? "Selected" : "Not selected"}.',
                  hint: 'Double tap to change selection.',
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => _focusOption(option.type),
                    onDoubleTap: () => _toggleOption(option.type),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 160),
                      padding: const EdgeInsets.all(AppTheme.spacingM),
                      decoration: AppTheme.cardDecoration(
                        backgroundColor: option.color,
                        isSelected: isSelected,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Icon(option.icon, size: 34),
                              Icon(
                                isSelected
                                    ? Icons.check_circle_rounded
                                    : Icons.radio_button_unchecked_rounded,
                                color: isSelected
                                    ? AppTheme.primary
                                    : AppTheme.textMuted,
                                size: 30,
                              ),
                            ],
                          ),
                          Text(
                            option.type.label,
                            style: AppTheme.headingSmall,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: AppTheme.spacingM),
          _DoubleTapButton(
            label: 'Double tap to continue',
            semanticLabel: '${_selected.length} guidance options selected. '
                'Double tap to continue.',
            onTap: () {
              widget.ttsService.speakOnce('Double tap to continue.');
              widget.hapticService.selection();
            },
            onDoubleTap: _goNext,
          ),
        ],
      ),
    );
  }

  Widget _buildComplete() {
    return Padding(
      key: const ValueKey('complete'),
      padding: const EdgeInsets.all(AppTheme.spacingL),
      child: Center(
        child: Semantics(
          liveRegion: true,
          header: true,
          label: 'Setup complete. Launching Rocket.',
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.check_circle_rounded,
                color: AppTheme.success,
                size: 96,
              ),
              const SizedBox(height: AppTheme.spacingL),
              const Text('Setup complete', style: AppTheme.headingLarge),
              const SizedBox(height: AppTheme.spacingS),
              Text(
                'Launching Rocket.',
                style: AppTheme.bodyLarge.copyWith(
                  color: AppTheme.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DoubleTapButton extends StatelessWidget {
  const _DoubleTapButton({
    required this.label,
    required this.semanticLabel,
    required this.onTap,
    required this.onDoubleTap,
  });

  final String label;
  final String semanticLabel;
  final VoidCallback onTap;
  final VoidCallback onDoubleTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: semanticLabel,
      hint: 'Single tap hears this button. Double tap activates it.',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        onDoubleTap: onDoubleTap,
        child: Container(
          width: double.infinity,
          constraints: const BoxConstraints(minHeight: 120),
          alignment: Alignment.center,
          decoration: AppTheme.primaryButtonDecoration,
          child: Text(label, style: AppTheme.buttonText),
        ),
      ),
    );
  }
}
