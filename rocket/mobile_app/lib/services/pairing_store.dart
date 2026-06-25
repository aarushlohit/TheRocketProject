import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/pairing_config.dart';
import '../models/user_profile.dart';

class PairingStore {
  static const String _pairingKey = 'rocket_pairing_config';
  static const String _profileKey = 'rocket_user_profile';
  static const String _onboardingKey = 'rocket_onboarding_done';
  static const String _legacyPairingKey = 'nova_pairing_config';
  static const String _legacyProfileKey = 'nova_user_profile';
  static const String _legacyOnboardingKey = 'nova_onboarding_done';

  // ============ PAIRING CONFIG ============

  Future<PairingConfig?> load() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final String? rawValue = await _readMigratedString(
      prefs,
      currentKey: _pairingKey,
      legacyKey: _legacyPairingKey,
    );
    if (rawValue == null || rawValue.isEmpty) {
      return null;
    }

    final dynamic decoded = jsonDecode(rawValue);
    if (decoded is! Map<String, dynamic>) {
      return null;
    }

    return PairingConfig.fromJson(decoded);
  }

  Future<void> save(PairingConfig config) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setString(_pairingKey, jsonEncode(config.toJson()));
    await prefs.remove(_legacyPairingKey);
  }

  Future<void> clear() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.remove(_pairingKey);
    await prefs.remove(_legacyPairingKey);
  }

  // ============ USER PROFILE ============

  Future<UserProfile?> loadProfile() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final String? rawValue = await _readMigratedString(
      prefs,
      currentKey: _profileKey,
      legacyKey: _legacyProfileKey,
    );
    if (rawValue == null || rawValue.isEmpty) {
      return null;
    }

    try {
      return UserProfile.fromJsonString(rawValue);
    } catch (e) {
      return null;
    }
  }

  Future<void> saveProfile(UserProfile profile) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setString(_profileKey, profile.toJsonString());
    await prefs.setBool(_onboardingKey, true);
    await prefs.remove(_legacyProfileKey);
    await prefs.remove(_legacyOnboardingKey);
  }

  Future<void> clearProfile() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.remove(_profileKey);
    await prefs.remove(_onboardingKey);
    await prefs.remove(_legacyProfileKey);
    await prefs.remove(_legacyOnboardingKey);
  }

  // ============ ONBOARDING STATUS ============

  Future<bool> isOnboardingComplete() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final bool? currentValue = prefs.getBool(_onboardingKey);
    if (currentValue != null) {
      return currentValue;
    }

    final bool? legacyValue = prefs.getBool(_legacyOnboardingKey);
    if (legacyValue != null) {
      await prefs.setBool(_onboardingKey, legacyValue);
      await prefs.remove(_legacyOnboardingKey);
      return legacyValue;
    }

    return false;
  }

  Future<String?> _readMigratedString(
    SharedPreferences prefs, {
    required String currentKey,
    required String legacyKey,
  }) async {
    final String? currentValue = prefs.getString(currentKey);
    if (currentValue != null && currentValue.isNotEmpty) {
      return currentValue;
    }

    final String? legacyValue = prefs.getString(legacyKey);
    if (legacyValue != null && legacyValue.isNotEmpty) {
      await prefs.setString(currentKey, legacyValue);
      await prefs.remove(legacyKey);
      return legacyValue;
    }

    return null;
  }
}
