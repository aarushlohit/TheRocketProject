import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/pairing_config.dart';
import '../models/user_profile.dart';

class PairingStore {
  static const String _pairingKey = 'nova_pairing_config';
  static const String _profileKey = 'nova_user_profile';
  static const String _onboardingKey = 'nova_onboarding_done';

  // ============ PAIRING CONFIG ============

  Future<PairingConfig?> load() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final String? rawValue = prefs.getString(_pairingKey);
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
  }

  Future<void> clear() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.remove(_pairingKey);
  }

  // ============ USER PROFILE ============

  Future<UserProfile?> loadProfile() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final String? rawValue = prefs.getString(_profileKey);
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
  }

  Future<void> clearProfile() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.remove(_profileKey);
    await prefs.remove(_onboardingKey);
  }

  // ============ ONBOARDING STATUS ============

  Future<bool> isOnboardingComplete() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_onboardingKey) ?? false;
  }
}
