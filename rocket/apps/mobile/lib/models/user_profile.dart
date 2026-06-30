import 'dart:convert';

/// Disability types for accessibility preferences
enum DisabilityType {
  visual,
  hearing,
  motor,
  cognitive,
}

extension DisabilityTypeExtension on DisabilityType {
  String get label => switch (this) {
        DisabilityType.visual => 'Voice guidance',
        DisabilityType.hearing => 'Haptic guidance',
        DisabilityType.motor => 'Large controls',
        DisabilityType.cognitive => 'Simple mode',
      };

  String get description => switch (this) {
        DisabilityType.visual => 'Speak every important action aloud',
        DisabilityType.hearing => 'Use vibration feedback for actions',
        DisabilityType.motor => 'Use bigger controls and simpler gestures',
        DisabilityType.cognitive => 'Use shorter prompts and simpler screens',
      };

  int get id => switch (this) {
        DisabilityType.visual => 1,
        DisabilityType.hearing => 2,
        DisabilityType.motor => 3,
        DisabilityType.cognitive => 4,
      };
}

/// User accessibility profile
class UserProfile {
  const UserProfile({
    required this.disabilities,
    this.name = '',
    this.preferredName = '',
    this.email = '',
    this.phone = '',
    this.address = '',
    this.country = '',
    this.browser = 'default',
    this.editor = 'code',
    this.speechSpeed = 'normal',
    this.accessibilityMode = 'blind-first',
    this.trustLevel = 'trusted',
    this.accessMode = 'workspace',
    this.credentialMode = 'already_configured',
    this.workspacePath = '',
    this.credentialRefs = const {},
    this.backupEnabled = true,
    this.passwordPatternRef = '',
    this.voiceFeedback = true,
    this.hapticFeedback = true,
    this.confirmationRequired = true,
    this.onboardingCompleted = false,
  });

  final Set<DisabilityType> disabilities;
  final String name;
  final String preferredName;
  final String email;
  final String phone;
  final String address;
  final String country;
  final String browser;
  final String editor;
  final String speechSpeed;
  final String accessibilityMode;
  final String trustLevel;
  final String accessMode;
  final String credentialMode;
  final String workspacePath;
  final Map<String, String> credentialRefs;
  final bool backupEnabled;
  final String passwordPatternRef;
  final bool voiceFeedback;
  final bool hapticFeedback;
  final bool confirmationRequired;
  final bool onboardingCompleted;

  /// Check if user has specific disability
  bool hasDisability(DisabilityType type) => disabilities.contains(type);
  bool get isVisuallyImpaired => hasDisability(DisabilityType.visual);
  bool get isHearingImpaired => hasDisability(DisabilityType.hearing);
  bool get hasMotorDisability => hasDisability(DisabilityType.motor);
  bool get hasCognitiveSupport => hasDisability(DisabilityType.cognitive);

  /// Get selections as list of IDs for backend
  List<int> get selectionIds => disabilities.map((d) => d.id).toList()..sort();

  UserProfile copyWith({
    Set<DisabilityType>? disabilities,
    String? name,
    String? preferredName,
    String? email,
    String? phone,
    String? address,
    String? country,
    String? browser,
    String? editor,
    String? speechSpeed,
    String? accessibilityMode,
    String? trustLevel,
    String? accessMode,
    String? credentialMode,
    String? workspacePath,
    Map<String, String>? credentialRefs,
    bool? backupEnabled,
    String? passwordPatternRef,
    bool? voiceFeedback,
    bool? hapticFeedback,
    bool? confirmationRequired,
    bool? onboardingCompleted,
  }) {
    return UserProfile(
      disabilities: disabilities ?? this.disabilities,
      name: name ?? this.name,
      preferredName: preferredName ?? this.preferredName,
      email: email ?? this.email,
      phone: phone ?? this.phone,
      address: address ?? this.address,
      country: country ?? this.country,
      browser: browser ?? this.browser,
      editor: editor ?? this.editor,
      speechSpeed: speechSpeed ?? this.speechSpeed,
      accessibilityMode: accessibilityMode ?? this.accessibilityMode,
      trustLevel: trustLevel ?? this.trustLevel,
      accessMode: accessMode ?? this.accessMode,
      credentialMode: credentialMode ?? this.credentialMode,
      workspacePath: workspacePath ?? this.workspacePath,
      credentialRefs: credentialRefs ?? this.credentialRefs,
      backupEnabled: backupEnabled ?? this.backupEnabled,
      passwordPatternRef: passwordPatternRef ?? this.passwordPatternRef,
      voiceFeedback: voiceFeedback ?? this.voiceFeedback,
      hapticFeedback: hapticFeedback ?? this.hapticFeedback,
      confirmationRequired: confirmationRequired ?? this.confirmationRequired,
      onboardingCompleted: onboardingCompleted ?? this.onboardingCompleted,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'disabilities': disabilities.map((d) => d.name).toList(),
      'name': name,
      'preferred_name': preferredName,
      'email': email,
      'phone': phone,
      'address': address,
      'country': country,
      'browser': browser,
      'editor': editor,
      'speech_speed': speechSpeed,
      'accessibility_mode': accessibilityMode,
      'trust_level': trustLevel,
      'access_mode': accessMode,
      'credential_mode': credentialMode,
      'workspace_path': workspacePath,
      'credential_refs': credentialRefs,
      'backup_enabled': backupEnabled,
      'password_pattern_ref': passwordPatternRef,
      'voice_feedback': voiceFeedback,
      'haptic_feedback': hapticFeedback,
      'confirmation_required': confirmationRequired,
      'onboarding_completed': onboardingCompleted,
    };
  }

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    final disabilityNames = (json['disabilities'] as List<dynamic>?) ?? [];
    final disabilities = disabilityNames
        .map((name) => DisabilityType.values.firstWhere(
              (d) => d.name == name,
              orElse: () => DisabilityType.visual,
            ))
        .toSet();

    return UserProfile(
      disabilities: disabilities,
      name: json['name']?.toString() ?? '',
      preferredName: json['preferred_name']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      phone: json['phone']?.toString() ?? '',
      address: json['address']?.toString() ?? '',
      country: json['country']?.toString() ?? '',
      browser: json['browser']?.toString() ?? 'default',
      editor: json['editor']?.toString() ?? 'code',
      speechSpeed: json['speech_speed']?.toString() ?? 'normal',
      accessibilityMode:
          json['accessibility_mode']?.toString() ?? 'blind-first',
      trustLevel: json['trust_level']?.toString() ?? 'trusted',
      accessMode: 'workspace',
      credentialMode:
          json['credential_mode']?.toString() ?? 'already_configured',
      workspacePath: json['workspace_path']?.toString() ?? '',
      credentialRefs: _stringMap(json['credential_refs']),
      backupEnabled: json['backup_enabled'] as bool? ?? true,
      passwordPatternRef: json['password_pattern_ref']?.toString() ?? '',
      voiceFeedback: json['voice_feedback'] as bool? ?? true,
      hapticFeedback: json['haptic_feedback'] as bool? ?? true,
      confirmationRequired: json['confirmation_required'] as bool? ?? true,
      onboardingCompleted: json['onboarding_completed'] as bool? ?? false,
    );
  }

  String toJsonString() => jsonEncode(toJson());

  factory UserProfile.fromJsonString(String jsonString) {
    return UserProfile.fromJson(jsonDecode(jsonString) as Map<String, dynamic>);
  }

  /// Empty profile for new users
  static const UserProfile empty = UserProfile(
    disabilities: {},
    onboardingCompleted: false,
  );
}

Map<String, String> _stringMap(Object? value) {
  if (value is! Map) return const {};
  return {
    for (final entry in value.entries)
      if (entry.key != null && entry.value != null)
        entry.key.toString(): entry.value.toString(),
  };
}
