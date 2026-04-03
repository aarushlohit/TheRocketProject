import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/pairing_config.dart';

class PairingStore {
  static const String _pairingKey = 'nova_pairing_config';

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
}
