import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:vibration/vibration.dart';

/// Haptic pattern types matching backend definitions
enum HapticPattern {
  /// Short-pause-short (200ms-100ms-200ms) - Action succeeded
  success,
  
  /// Long vibration (500ms) - Error occurred
  error,
  
  /// Rapid 5x vibration (100ms each) - Dangerous action
  danger,
  
  /// Medium-long-medium - Confirmation requested
  confirmation,
  
  /// Single short (150ms) - Execution started
  executionStart,
  
  /// Triple short (100ms each) - Execution verified
  executionVerified,
  
  /// Long-pause-long - Model failure
  modelFailure,
  
  /// Light tap - Selection/navigation
  selection,
  
  /// Medium impact - Button press
  tap,
}

/// Haptic/vibration service for accessibility feedback
class HapticService extends ChangeNotifier {
  HapticService() {
    _init();
  }

  bool _hasVibrator = false;
  bool _hasAmplitudeControl = false;
  bool _initialized = false;
  bool _enabled = true;

  bool get isInitialized => _initialized;
  bool get hasVibrator => _hasVibrator;
  bool get hasAmplitudeControl => _hasAmplitudeControl;
  bool get isEnabled => _enabled;

  set enabled(bool value) {
    _enabled = value;
    notifyListeners();
  }

  Future<void> _init() async {
    try {
      _hasVibrator = await Vibration.hasVibrator() ?? false;
      _hasAmplitudeControl = await Vibration.hasAmplitudeControl() ?? false;
      _initialized = true;
      notifyListeners();
    } catch (e) {
      debugPrint('[HAPTIC] Init failed: $e');
      _hasVibrator = false;
      _initialized = true;
      notifyListeners();
    }
  }

  /// Execute a predefined haptic pattern
  Future<void> pattern(HapticPattern type) async {
    if (!_enabled || !_hasVibrator) {
      // Fallback to system haptics
      _systemFallback(type);
      return;
    }

    try {
      switch (type) {
        case HapticPattern.success:
          // Short-pause-short (200ms-100ms-200ms)
          await Vibration.vibrate(pattern: [0, 200, 100, 200]);
          
        case HapticPattern.error:
          // Long vibration (500ms)
          await Vibration.vibrate(duration: 500);
          
        case HapticPattern.danger:
          // Rapid 5x (100ms each with 50ms pause)
          await Vibration.vibrate(pattern: [0, 100, 50, 100, 50, 100, 50, 100, 50, 100]);
          
        case HapticPattern.confirmation:
          // Medium-long-medium (200ms-300ms-200ms)
          await Vibration.vibrate(pattern: [0, 200, 100, 400, 100, 200]);
          
        case HapticPattern.executionStart:
          // Single short (150ms)
          await Vibration.vibrate(duration: 150);
          
        case HapticPattern.executionVerified:
          // Triple short (100ms each)
          await Vibration.vibrate(pattern: [0, 100, 50, 100, 50, 100]);
          
        case HapticPattern.modelFailure:
          // Long-pause-long (400ms-200ms-400ms)
          await Vibration.vibrate(pattern: [0, 400, 200, 400]);
          
        case HapticPattern.selection:
          // Light tap
          await Vibration.vibrate(duration: 50, amplitude: 64);
          
        case HapticPattern.tap:
          // Medium impact
          await Vibration.vibrate(duration: 100, amplitude: 128);
      }
    } catch (e) {
      debugPrint('[HAPTIC] Pattern failed: $e');
      _systemFallback(type);
    }
  }

  /// Use system haptic feedback as fallback
  void _systemFallback(HapticPattern type) {
    switch (type) {
      case HapticPattern.success:
      case HapticPattern.executionVerified:
        HapticFeedback.mediumImpact();
        
      case HapticPattern.error:
      case HapticPattern.danger:
      case HapticPattern.modelFailure:
        HapticFeedback.heavyImpact();
        
      case HapticPattern.confirmation:
        HapticFeedback.heavyImpact();
        
      case HapticPattern.executionStart:
      case HapticPattern.selection:
        HapticFeedback.lightImpact();
        
      case HapticPattern.tap:
        HapticFeedback.mediumImpact();
    }
  }

  /// Custom vibration with duration in milliseconds
  Future<void> vibrate({int duration = 200, int? amplitude}) async {
    if (!_enabled) return;
    
    if (_hasVibrator) {
      try {
        if (amplitude != null && _hasAmplitudeControl) {
          await Vibration.vibrate(duration: duration, amplitude: amplitude);
        } else {
          await Vibration.vibrate(duration: duration);
        }
      } catch (e) {
        debugPrint('[HAPTIC] Vibrate failed: $e');
        HapticFeedback.mediumImpact();
      }
    } else {
      HapticFeedback.mediumImpact();
    }
  }

  /// Custom pattern from backend haptic_pattern JSON
  Future<void> customPattern(Map<String, dynamic> hapticData) async {
    if (!_enabled || !_hasVibrator) return;

    try {
      final patternList = hapticData['pattern'] as List<dynamic>?;
      if (patternList != null && patternList.isNotEmpty) {
        final intPattern = patternList.cast<int>();
        await Vibration.vibrate(pattern: intPattern);
      } else {
        final duration = hapticData['duration'] as int? ?? 200;
        await Vibration.vibrate(duration: duration);
      }
    } catch (e) {
      debugPrint('[HAPTIC] Custom pattern failed: $e');
    }
  }

  /// Convenience methods
  Future<void> success() => pattern(HapticPattern.success);
  Future<void> error() => pattern(HapticPattern.error);
  Future<void> danger() => pattern(HapticPattern.danger);
  Future<void> confirmation() => pattern(HapticPattern.confirmation);
  Future<void> executionStart() => pattern(HapticPattern.executionStart);
  Future<void> executionVerified() => pattern(HapticPattern.executionVerified);
  Future<void> modelFailure() => pattern(HapticPattern.modelFailure);
  Future<void> selection() => pattern(HapticPattern.selection);
  Future<void> tap() => pattern(HapticPattern.tap);

  @override
  void dispose() {
    Vibration.cancel();
    super.dispose();
  }
}
