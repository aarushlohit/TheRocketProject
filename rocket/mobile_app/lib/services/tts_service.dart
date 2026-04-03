import 'dart:async';
import 'dart:collection';

import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// Priority levels for TTS messages
enum TtsPriority {
  low,
  normal,
  high,
  critical, // Interrupts current speech
}

/// A queued TTS message with priority
class TtsMessage {
  const TtsMessage({
    required this.text,
    this.priority = TtsPriority.normal,
  });

  final String text;
  final TtsPriority priority;
}

/// Text-to-Speech service with priority queue and single-utterance support
class TtsService extends ChangeNotifier {
  TtsService() {
    _init();
  }

  final FlutterTts _tts = FlutterTts();
  final Queue<TtsMessage> _queue = Queue<TtsMessage>();
  final Set<String> _spokenCache = {}; // Track what's been spoken
  bool _isSpeaking = false;
  bool _initialized = false;
  String? _currentText;

  bool get isSpeaking => _isSpeaking;
  bool get isInitialized => _initialized;
  String? get currentText => _currentText;

  Future<void> _init() async {
    try {
      await _tts.setLanguage('en-US');
      await _tts.setSpeechRate(0.5);
      await _tts.setVolume(1.0);
      await _tts.setPitch(1.0);

      _tts.setCompletionHandler(() {
        _isSpeaking = false;
        _currentText = null;
        notifyListeners();
        _processQueue();
      });

      _tts.setErrorHandler((msg) {
        debugPrint('[TTS ERROR] $msg');
        _isSpeaking = false;
        _currentText = null;
        notifyListeners();
        _processQueue();
      });

      _tts.setCancelHandler(() {
        _isSpeaking = false;
        _currentText = null;
        notifyListeners();
      });

      _initialized = true;
      notifyListeners();
    } catch (e) {
      debugPrint('[TTS] Init failed: $e');
    }
  }

  /// Speak a message ONLY ONCE per session/navigation
  /// Will not repeat if the same text has already been spoken
  /// Call [clearSpokenCache] on navigation to reset
  Future<void> speakOnce(String text, {TtsPriority priority = TtsPriority.normal}) async {
    final cacheKey = text.toLowerCase().trim();
    if (_spokenCache.contains(cacheKey)) {
      debugPrint('[TTS] Skipping duplicate: $text');
      return;
    }
    _spokenCache.add(cacheKey);
    await speak(text, priority: priority);
  }

  /// Clear the spoken cache (call on navigation change)
  void clearSpokenCache() {
    _spokenCache.clear();
  }

  /// Speak a message with the given priority (can repeat)
  Future<void> speak(String text, {TtsPriority priority = TtsPriority.normal}) async {
    if (!_initialized || text.trim().isEmpty) return;

    final message = TtsMessage(text: text, priority: priority);

    if (priority == TtsPriority.critical) {
      await stop();
      _queue.addFirst(message);
    } else if (priority == TtsPriority.high) {
      _queue.addFirst(message);
    } else {
      _queue.add(message);
    }

    _processQueue();
  }

  void _processQueue() {
    if (_isSpeaking || _queue.isEmpty) return;
    final message = _queue.removeFirst();
    _speakNow(message.text);
  }

  Future<void> _speakNow(String text) async {
    if (!_initialized) return;

    _isSpeaking = true;
    _currentText = text;
    notifyListeners();

    try {
      await _tts.speak(text);
    } catch (e) {
      debugPrint('[TTS] Speak error: $e');
      _isSpeaking = false;
      _currentText = null;
      notifyListeners();
      _processQueue();
    }
  }

  /// Stop current speech and clear queue
  Future<void> stop() async {
    _queue.clear();
    await _tts.stop();
    _isSpeaking = false;
    _currentText = null;
    notifyListeners();
  }

  /// Clear the queue but let current speech finish
  void clearQueue() {
    _queue.clear();
  }

  /// Convenience methods
  Future<void> speakFeedback(String text) => speak(text, priority: TtsPriority.normal);
  Future<void> speakResult(String text) => speak(text, priority: TtsPriority.high);
  Future<void> speakError(String text) => speak(text, priority: TtsPriority.critical);
  Future<void> speakConfirmation(String text) => speak(text, priority: TtsPriority.critical);

  @override
  void dispose() {
    _tts.stop();
    super.dispose();
  }
}
