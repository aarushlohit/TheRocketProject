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
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _preferredNameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _addressController = TextEditingController();
  final TextEditingController _countryController = TextEditingController();
  final TextEditingController _browserController =
      TextEditingController(text: 'default');
  final TextEditingController _editorController =
      TextEditingController(text: 'code');
  final TextEditingController _speechSpeedController =
      TextEditingController(text: 'normal');
  final TextEditingController _trustLevelController =
      TextEditingController(text: 'trusted');
  final TextEditingController _accessModeController =
      TextEditingController(text: 'workspace');
  final TextEditingController _workspacePathController = TextEditingController();
  final TextEditingController _gmailRefController = TextEditingController();
  final TextEditingController _githubRefController = TextEditingController();
  final TextEditingController _youtubeRefController = TextEditingController();
  final TextEditingController _googleWorkspaceRefController =
      TextEditingController();
  final TextEditingController _passwordPatternRefController =
      TextEditingController();

  final Set<DisabilityType> _selected = {
    DisabilityType.visual,
    DisabilityType.hearing,
    DisabilityType.motor,
  };
  String _credentialMode = 'already_configured';
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
  void dispose() {
    _nameController.dispose();
    _preferredNameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _addressController.dispose();
    _countryController.dispose();
    _browserController.dispose();
    _editorController.dispose();
    _speechSpeedController.dispose();
    _trustLevelController.dispose();
    _accessModeController.dispose();
    _workspacePathController.dispose();
    _gmailRefController.dispose();
    _githubRefController.dispose();
    _youtubeRefController.dispose();
    _googleWorkspaceRefController.dispose();
    _passwordPatternRefController.dispose();
    super.dispose();
  }

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
        'Tell Rocket your details. Double tap each field to edit. Double tap continue when finished.',
      );
      return;
    }

    if (_page == 1) {
      setState(() => _page = 2);
      widget.ttsService.speakOnce(
        'Choose preferred guidance. Double tap each option to select or remove it.',
      );
      return;
    }

    if (_page == 2) {
      setState(() => _page = 3);
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
        name: _nameController.text.trim(),
        preferredName: _preferredNameController.text.trim(),
        email: _emailController.text.trim(),
        phone: _phoneController.text.trim(),
        address: _addressController.text.trim(),
        country: _countryController.text.trim(),
        browser: _browserController.text.trim().isEmpty
            ? 'default'
            : _browserController.text.trim(),
        editor: _editorController.text.trim().isEmpty
            ? 'code'
            : _editorController.text.trim(),
        speechSpeed: _speechSpeedController.text.trim().isEmpty
            ? 'normal'
            : _speechSpeedController.text.trim(),
        accessibilityMode: 'blind-first',
        trustLevel: _trustLevelController.text.trim().isEmpty
            ? 'trusted'
            : _trustLevelController.text.trim(),
        accessMode: _accessModeController.text.trim().toLowerCase() == 'full'
            ? 'full'
            : 'workspace',
        credentialMode: _credentialMode,
        workspacePath: _workspacePathController.text.trim(),
        credentialRefs:
            _credentialMode == 'add_now' ? _credentialRefs() : const {},
        backupEnabled: true,
        passwordPatternRef: _passwordPatternRefController.text.trim(),
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
            1 => _buildDetails(),
            2 => _buildGuidance(),
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

  Widget _buildDetails() {
    return Padding(
      key: const ValueKey('details'),
      padding: const EdgeInsets.all(AppTheme.spacingL),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            header: true,
            child: const Text('Your details', style: AppTheme.headingLarge),
          ),
          const SizedBox(height: AppTheme.spacingS),
          Text(
            'Rocket uses this once to personalize blind-first execution.',
            style: AppTheme.bodyLarge.copyWith(color: AppTheme.textSecondary),
          ),
          const SizedBox(height: AppTheme.spacingM),
          Expanded(
            child: ListView(
              children: [
                _ProfileField(label: 'Name', controller: _nameController),
                _ProfileField(
                  label: 'Preferred name',
                  controller: _preferredNameController,
                ),
                _ProfileField(label: 'Email', controller: _emailController),
                _ProfileField(label: 'Phone', controller: _phoneController),
                _ProfileField(label: 'Address', controller: _addressController),
                _ProfileField(label: 'Country', controller: _countryController),
                _ProfileField(label: 'Browser', controller: _browserController),
                _ProfileField(label: 'Editor', controller: _editorController),
                _ProfileField(
                  label: 'Speech speed',
                  controller: _speechSpeedController,
                ),
                _ProfileField(
                  label: 'Trust level',
                  controller: _trustLevelController,
                ),
                _ProfileField(
                  label: 'Access mode',
                  controller: _accessModeController,
                ),
                _ProfileField(
                  label: 'Workspace path',
                  controller: _workspacePathController,
                ),
                _CredentialModePicker(
                  value: _credentialMode,
                  onChanged: _setCredentialMode,
                ),
                if (_credentialMode == 'add_now') ...[
                  _ProfileField(
                    label: 'Gmail credential reference',
                    controller: _gmailRefController,
                  ),
                  _ProfileField(
                    label: 'GitHub credential reference',
                    controller: _githubRefController,
                  ),
                  _ProfileField(
                    label: 'YouTube credential reference',
                    controller: _youtubeRefController,
                  ),
                  _ProfileField(
                    label: 'Google Workspace credential reference',
                    controller: _googleWorkspaceRefController,
                  ),
                ],
                _ProfileField(
                  label: 'Password pattern reference',
                  controller: _passwordPatternRefController,
                ),
              ],
            ),
          ),
          const SizedBox(height: AppTheme.spacingM),
          _DoubleTapButton(
            label: 'Double tap to continue',
            semanticLabel: 'Profile details ready. Double tap to continue.',
            onTap: () {
              widget.ttsService.speakOnce('Profile details. Double tap to continue.');
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

  void _setCredentialMode(String mode) {
    setState(() => _credentialMode = mode);
    final label = switch (mode) {
      'add_now' => 'Add credential references now',
      'skip' => 'Skip credentials for now',
      _ => 'Already configured in OpenCode',
    };
    widget.ttsService.speakOnce('$label selected.');
    widget.hapticService.selection();
  }

  Map<String, String> _credentialRefs() {
    final refs = <String, String>{};
    void addRef(String key, TextEditingController controller) {
      final value = controller.text.trim();
      if (value.isNotEmpty) refs[key] = value;
    }

    addRef('gmail', _gmailRefController);
    addRef('github', _githubRefController);
    addRef('youtube', _youtubeRefController);
    addRef('google_workspace', _googleWorkspaceRefController);
    return refs;
  }
}

class _CredentialModePicker extends StatelessWidget {
  const _CredentialModePicker({
    required this.value,
    required this.onChanged,
  });

  final String value;
  final ValueChanged<String> onChanged;

  static const _options = [
    ('already_configured', 'Already configured in OpenCode'),
    ('add_now', 'Add credential references now'),
    ('skip', 'Skip credentials for now'),
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppTheme.spacingM),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Credentials', style: AppTheme.headingSmall),
          const SizedBox(height: AppTheme.spacingS),
          for (final option in _options)
            _CredentialOption(
              value: option.$1,
              label: option.$2,
              selected: value == option.$1,
              onSelected: onChanged,
            ),
        ],
      ),
    );
  }
}

class _CredentialOption extends StatelessWidget {
  const _CredentialOption({
    required this.value,
    required this.label,
    required this.selected,
    required this.onSelected,
  });

  final String value;
  final String label;
  final bool selected;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      hint: 'Double tap to select.',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => onSelected(value),
        onDoubleTap: () => onSelected(value),
        child: Container(
          width: double.infinity,
          constraints: const BoxConstraints(minHeight: 72),
          margin: const EdgeInsets.only(bottom: AppTheme.spacingS),
          padding: const EdgeInsets.symmetric(
            horizontal: AppTheme.spacingM,
            vertical: AppTheme.spacingS,
          ),
          decoration: AppTheme.cardDecoration(
            backgroundColor: Colors.white,
            isSelected: selected,
          ),
          child: Row(
            children: [
              Icon(
                selected
                    ? Icons.radio_button_checked_rounded
                    : Icons.radio_button_unchecked_rounded,
                color: selected ? AppTheme.primary : AppTheme.textMuted,
              ),
              const SizedBox(width: AppTheme.spacingM),
              Expanded(child: Text(label, style: AppTheme.bodyLarge)),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProfileField extends StatelessWidget {
  const _ProfileField({
    required this.label,
    required this.controller,
  });

  final String label;
  final TextEditingController controller;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppTheme.spacingM),
      child: Semantics(
        textField: true,
        label: label,
        hint: 'Double tap to edit.',
        child: TextField(
          controller: controller,
          style: AppTheme.bodyLarge,
          minLines: label == 'Address' ? 2 : 1,
          maxLines: label == 'Address' ? 3 : 1,
          decoration: InputDecoration(
            labelText: label,
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
            ),
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
