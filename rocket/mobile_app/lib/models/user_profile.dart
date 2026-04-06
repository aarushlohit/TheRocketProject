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
    DisabilityType.visual => 'I can see',
    DisabilityType.hearing => 'I can hear',
    DisabilityType.motor => 'I have difficulty touching',
    DisabilityType.cognitive => 'I need simple guidance',
  };

  String get description => switch (this) {
    DisabilityType.visual => 'Use visual guidance and standard touch controls',
    DisabilityType.hearing => 'Voice guidance works well for me',
    DisabilityType.motor => 'Use larger touch targets and simpler gestures',
    DisabilityType.cognitive => 'Use clearer prompts and a simpler flow',
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
    this.voiceFeedback = true,
    this.hapticFeedback = true,
    this.confirmationRequired = true,
    this.onboardingCompleted = false,
  });

  final Set<DisabilityType> disabilities;
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
    bool? voiceFeedback,
    bool? hapticFeedback,
    bool? confirmationRequired,
    bool? onboardingCompleted,
  }) {
    return UserProfile(
      disabilities: disabilities ?? this.disabilities,
      voiceFeedback: voiceFeedback ?? this.voiceFeedback,
      hapticFeedback: hapticFeedback ?? this.hapticFeedback,
      confirmationRequired: confirmationRequired ?? this.confirmationRequired,
      onboardingCompleted: onboardingCompleted ?? this.onboardingCompleted,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'disabilities': disabilities.map((d) => d.name).toList(),
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
