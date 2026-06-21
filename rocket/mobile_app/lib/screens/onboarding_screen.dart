import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/app_theme.dart';
import '../models/user_profile.dart';
import '../services/haptic_service.dart';
import '../services/tts_service.dart';

/// Disability selection card data
class _DisabilityCard {
  const _DisabilityCard({
    required this.type,
    required this.icon,
    required this.color,
  });

  final DisabilityType type;
  final IconData icon;
  final Color color;
}

/// Elegant onboarding screen for disability selection
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
  final Set<DisabilityType> _selected = {};
  bool _announced = false;

  static const List<_DisabilityCard> _cards = [
    _DisabilityCard(
      type: DisabilityType.visual,
      icon: Icons.visibility_rounded,
      color: AppTheme.cardVisual,
    ),
    _DisabilityCard(
      type: DisabilityType.hearing,
      icon: Icons.hearing_rounded,
      color: AppTheme.cardHearing,
    ),
    _DisabilityCard(
      type: DisabilityType.motor,
      icon: Icons.accessibility_new_rounded,
      color: AppTheme.cardMotor,
    ),
    _DisabilityCard(
      type: DisabilityType.cognitive,
      icon: Icons.psychology_rounded,
      color: AppTheme.cardCognitive,
    ),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_announced) {
        _announced = true;
        widget.ttsService.speakOnce(
          'Welcome to Rocket. Tell me how you want guidance. '
          'You can choose one or more options. Tap to select, double tap to continue.',
        );
      }
    });
  }

  void _toggleSelection(DisabilityType type) {
    setState(() {
      if (_selected.contains(type)) {
        _selected.remove(type);
        widget.ttsService.speakOnce('${type.label} deselected');
      } else {
        _selected.add(type);
        widget.ttsService.speakOnce('${type.label} selected');
      }
    });
    widget.hapticService.tap();
  }

  void _announceCard(DisabilityType type) {
    final isSelected = _selected.contains(type);
    widget.ttsService.speakOnce(
      '${type.label}. ${type.description}. '
      '${isSelected ? "Selected" : "Not selected"}. Tap to toggle.',
    );
    widget.hapticService.selection();
  }

  void _onContinue() {
    if (_selected.isEmpty) {
      widget.ttsService.speak('Please select at least one option');
      widget.hapticService.error();
      return;
    }

    final profile = UserProfile(
      disabilities: _selected,
      voiceFeedback: true,
      hapticFeedback: true,
      confirmationRequired: true,
      onboardingCompleted: true,
    );

    widget.hapticService.success();
    widget.onComplete(profile);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppTheme.spacingL),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: AppTheme.spacingL),

              // Header
              Semantics(
                header: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: const Icon(
                            Icons.rocket_launch_rounded,
                            color: AppTheme.primary,
                            size: 28,
                          ),
                        ),
                        const SizedBox(width: AppTheme.spacingM),
                        const Text('Rocket', style: AppTheme.headingMedium),
                      ],
                    ),
                    const SizedBox(height: AppTheme.spacingL),
                    const Text(
                      'Tell Rocket\nHow To Help',
                      style: AppTheme.headingLarge,
                    ),
                    const SizedBox(height: AppTheme.spacingS),
                    Text(
                      'Choose one or more options that match how you want to use the app',
                      style: AppTheme.bodyMedium.copyWith(
                        color: AppTheme.textMuted,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: AppTheme.spacingXL),

              // Disability cards grid
              Expanded(
                child: GridView.count(
                  crossAxisCount: 2,
                  mainAxisSpacing: AppTheme.spacingM,
                  crossAxisSpacing: AppTheme.spacingM,
                  childAspectRatio: 1.0,
                  children: _cards.map((card) {
                    final isSelected = _selected.contains(card.type);
                    return _buildCard(card, isSelected);
                  }).toList(),
                ),
              ),

              const SizedBox(height: AppTheme.spacingL),

              // Continue button
              Semantics(
                button: true,
                label: 'Continue with ${_selected.length} options selected',
                child: GestureDetector(
                  onTap: () {
                    HapticFeedback.mediumImpact();
                    widget.ttsService.speakOnce('Double tap to continue');
                  },
                  onDoubleTap: _onContinue,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 18),
                    decoration: _selected.isEmpty
                        ? AppTheme.secondaryButtonDecoration
                        : AppTheme.primaryButtonDecoration,
                    child: Center(
                      child: Text(
                        _selected.isEmpty
                            ? 'Select options to continue'
                            : 'Continue',
                        style: AppTheme.buttonText.copyWith(
                          color: _selected.isEmpty
                              ? AppTheme.primary
                              : Colors.white,
                        ),
                      ),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: AppTheme.spacingM),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCard(_DisabilityCard card, bool isSelected) {
    return Semantics(
      selected: isSelected,
      button: true,
      label: '${card.type.label}. ${card.type.description}. '
          '${isSelected ? "Selected" : "Not selected"}',
      child: GestureDetector(
        onTap: () => _toggleSelection(card.type),
        onLongPress: () => _announceCard(card.type),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: AppTheme.cardDecoration(
            backgroundColor: card.color,
            isSelected: isSelected,
          ),
          padding: const EdgeInsets.all(AppTheme.spacingL),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Icon(
                    card.icon,
                    size: 32,
                    color: AppTheme.textPrimary.withValues(alpha: 0.8),
                  ),
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 28,
                    height: 28,
                    decoration: BoxDecoration(
                      color: isSelected ? AppTheme.primary : Colors.transparent,
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: isSelected ? AppTheme.primary : AppTheme.textMuted,
                        width: 2,
                      ),
                    ),
                    child: isSelected
                        ? const Icon(
                            Icons.check,
                            size: 18,
                            color: Colors.white,
                          )
                        : null,
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    card.type.label,
                    style: AppTheme.headingSmall,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    card.type.description,
                    style: AppTheme.bodySmall,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
