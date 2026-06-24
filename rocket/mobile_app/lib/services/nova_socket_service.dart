import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import '../models/pairing_config.dart';
import '../models/user_profile.dart';
import 'haptic_service.dart';
import 'tts_service.dart';

enum NovaConnectionStatus {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
}

class RocketTask {
  const RocketTask({
    required this.source,
    required this.task,
    required this.latencyMs,
  });

  final String source;
  final String task;
  final int latencyMs;

  factory RocketTask.fromJson(Map<String, dynamic> json) {
    return RocketTask(
      source: json['source']?.toString() ?? 'unknown',
      task: json['task']?.toString() ?? '',
      latencyMs: (json['latency_ms'] as num?)?.toInt() ?? 0,
    );
  }
}

class RocketExecutionResult {
  const RocketExecutionResult({
    required this.task,
    required this.success,
    required this.executor,
    required this.message,
    required this.verification,
  });

  final String task;
  final bool success;
  final String executor;
  final String message;
  final String verification;

  factory RocketExecutionResult.fromJson(Map<String, dynamic> json) {
    return RocketExecutionResult(
      task: json['task']?.toString() ?? '',
      success: json['success'] == true,
      executor: json['executor']?.toString() ?? 'rocket-runtime',
      message: json['message']?.toString() ?? '',
      verification: json['verification']?.toString() ?? '',
    );
  }

  String get spokenMessage {
    final prefix = success ? 'Completed.' : 'Failed.';
    final evidence = verification.trim().isEmpty ? message : verification;
    return '$prefix $evidence';
  }
}

class NovaSocketService extends ChangeNotifier {
  NovaSocketService({
    TtsService? ttsService,
    HapticService? hapticService,
  })  : _tts = ttsService ?? TtsService(),
        _haptic = hapticService ?? HapticService();

  final TtsService _tts;
  final HapticService _haptic;

  PairingConfig? _config;
  WebSocket? _socket;
  Timer? _reconnectTimer;
  Timer? _pingTimer;
  NovaConnectionStatus _status = NovaConnectionStatus.disconnected;
  bool _shouldReconnect = false;
  RocketTask? _lastTask;
  RocketExecutionResult? _lastExecutionResult;
  String? _lastTryAgainMessage;
  Map<String, dynamic>? _lastResponse;
  UserProfile? _localProfile;
  bool _localOnboardingDone = false;

  PairingConfig? get config => _config;
  RocketTask? get lastTask => _lastTask;
  RocketExecutionResult? get lastExecutionResult => _lastExecutionResult;
  String? get lastTryAgainMessage => _lastTryAgainMessage;
  Map<String, dynamic>? get lastResponse => _lastResponse;
  NovaConnectionStatus get status => _status;
  TtsService get tts => _tts;
  HapticService get haptic => _haptic;

  String get statusLabel => switch (_status) {
        NovaConnectionStatus.disconnected => 'Disconnected',
        NovaConnectionStatus.connecting => 'Connecting',
        NovaConnectionStatus.connected => 'Connected',
        NovaConnectionStatus.reconnecting => 'Reconnecting',
        NovaConnectionStatus.error => 'Connection error',
      };

  void setLocalOnboardingState({
    required UserProfile? profile,
    required bool isOnboardingDone,
  }) {
    _localProfile = profile;
    _localOnboardingDone = isOnboardingDone;
  }

  Future<void> setPairing(PairingConfig? config) async {
    _shouldReconnect = false;
    await disconnect();
    _config = config;
    _lastResponse = null;
    _lastTask = null;
    _lastExecutionResult = null;
    _lastTryAgainMessage = null;
    if (_config != null) {
      _shouldReconnect = true;
      unawaited(connect());
    } else {
      _updateStatus(NovaConnectionStatus.disconnected);
    }
  }

  Future<void> connect() async {
    if (_config == null || _socket != null) return;
    _shouldReconnect = true;
    _reconnectTimer?.cancel();
    _updateStatus(_lastResponse == null
        ? NovaConnectionStatus.connecting
        : NovaConnectionStatus.reconnecting);

    try {
      debugPrint('[RocketSocket] Connecting to ${_config!.websocketUrl}');
      final socket = await WebSocket.connect(_config!.websocketUrl);
      _socket = socket;
      _startPingTimer();
      socket.listen(
        _handleMessage,
        onDone: _handleSocketClosed,
        onError: _handleSocketError,
        cancelOnError: true,
      );
    } catch (error) {
      debugPrint('[RocketSocket] Connect failed: $error');
      _lastResponse = {'type': 'error', 'message': 'Connection failed: $error'};
      _updateStatus(NovaConnectionStatus.error);
      await _tts.speakError('Connection failed');
      await _haptic.error();
      _scheduleReconnect();
    }
  }

  Future<void> disconnect() async {
    _reconnectTimer?.cancel();
    _pingTimer?.cancel();
    final activeSocket = _socket;
    _socket = null;
    if (activeSocket != null) {
      await activeSocket.close();
    }
    _updateStatus(NovaConnectionStatus.disconnected);
  }

  Future<void> sendAudio(Uint8List audioBytes) async {
    await _ensureConnected();
    await _tts.speakFeedback('Processing voice');
    _sendJson({
      'type': 'audio',
      'data': base64Encode(audioBytes),
    });
    await _haptic.executionStart();
  }

  Future<void> sendDrawing(Uint8List imageBytes) async {
    await _ensureConnected();
    await _tts.speakFeedback('Drawing sent. Image processing.');
    _socket!.add(imageBytes);
    await _haptic.executionStart();
  }

  Future<void> sendBraille(String text) async {
    await _ensureConnected();
    await _tts.speakFeedback('Processing braille');
    _sendJson({
      'type': 'braille',
      'text': text,
    });
    await _haptic.executionStart();
  }

  void announceTaskSent() {
    unawaited(_tts.speakFeedback('Task sent to laptop'));
  }

  Future<void> _ensureConnected() async {
    if (_socket == null) {
      await connect();
    }
    if (_socket == null) {
      throw const SocketException('WebSocket is not connected');
    }
  }

  void _sendJson(Map<String, dynamic> data) {
    _socket?.add(jsonEncode(data));
  }

  void _startPingTimer() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      _sendJson({'type': 'ping'});
    });
  }

  void _handleMessage(dynamic data) {
    if (data is! String) return;
    try {
      final decoded = jsonDecode(data);
      if (decoded is! Map<String, dynamic>) return;
      _lastResponse = decoded;
      final type = decoded['type']?.toString();

      if (type == 'connected') {
        _updateStatus(NovaConnectionStatus.connected);
        _tts.speakFeedback(
            decoded['message']?.toString() ?? 'Connection established');
        _haptic.success();
        if (_localOnboardingDone && _localProfile != null) {
          debugPrint('[Rocket] Local accessibility profile active.');
          _sendJson({
            'type': 'profile',
            'profile': _localProfile!.toJson(),
            'system_prompt':
                'Blind-first. Context-aware intent. Prefer installed apps. Keep follow-up commands inside the active app.',
          });
          _sendJson({
            'type': 'setup',
            'setup': {
              'setup_complete': _localProfile!.onboardingCompleted,
              'access_mode': _localProfile!.accessMode,
              'credential_mode': _localProfile!.credentialMode,
              'workspace_path': _localProfile!.workspacePath,
              'credential_refs': _localProfile!.credentialRefs,
              'backup_enabled': _localProfile!.backupEnabled,
            },
          });
        }
      } else if (type == 'task') {
        _lastTask = RocketTask.fromJson(decoded);
        _tts.speakResult('Task generated. ${_lastTask!.task}');
        _haptic.success();
        announceTaskSent();
      } else if (type == 'execution_result') {
        _lastExecutionResult = RocketExecutionResult.fromJson(decoded);
        if (_lastExecutionResult!.success) {
          _tts.speakResult(_lastExecutionResult!.spokenMessage);
          _haptic.success();
        } else {
          _tts.speakError(_lastExecutionResult!.spokenMessage);
          _haptic.error();
        }
      } else if (type == 'try_again') {
        _lastTryAgainMessage = decoded['message']?.toString() ??
            'I could not understand. Please try again.';
        _tts.speakError(_lastTryAgainMessage!);
        _haptic.error();
      } else if (type == 'error') {
        final message = decoded['message']?.toString() ?? 'Rocket error';
        debugPrint('[RocketSocket] Server error: $message');
        if (message.toLowerCase().contains('token')) {
          _shouldReconnect = false;
          _socket = null;
          _pingTimer?.cancel();
          _updateStatus(NovaConnectionStatus.error);
        }
        _tts.speakError(message);
        _haptic.error();
      }
      notifyListeners();
    } on FormatException {
      _lastResponse = {
        'type': 'error',
        'message': 'Server returned invalid data'
      };
      notifyListeners();
    }
  }

  void _handleSocketClosed() {
    debugPrint(
        '[RocketSocket] Socket closed. shouldReconnect=$_shouldReconnect');
    _socket = null;
    _pingTimer?.cancel();
    if (_shouldReconnect) {
      _tts.speakFeedback('Connection lost. Reconnecting.');
      _scheduleReconnect();
    } else {
      _updateStatus(NovaConnectionStatus.disconnected);
    }
  }

  void _handleSocketError(Object error) {
    debugPrint('[RocketSocket] Socket error: $error');
    _lastResponse = {'type': 'error', 'message': 'Socket error: $error'};
    _socket = null;
    _pingTimer?.cancel();
    _updateStatus(NovaConnectionStatus.error);
    _tts.speakError('Connection error');
    _haptic.error();
    if (_shouldReconnect) {
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_config == null) {
      _updateStatus(NovaConnectionStatus.disconnected);
      return;
    }
    _reconnectTimer?.cancel();
    _updateStatus(NovaConnectionStatus.reconnecting);
    _reconnectTimer = Timer(
      const Duration(seconds: 3),
      () => unawaited(connect()),
    );
  }

  void _updateStatus(NovaConnectionStatus nextStatus) {
    if (_status == nextStatus) return;
    _status = nextStatus;
    notifyListeners();
  }

  @override
  void dispose() {
    _reconnectTimer?.cancel();
    _pingTimer?.cancel();
    _shouldReconnect = false;
    unawaited(disconnect());
    _tts.dispose();
    _haptic.dispose();
    super.dispose();
  }
}
