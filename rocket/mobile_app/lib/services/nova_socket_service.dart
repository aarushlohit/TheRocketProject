import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import '../models/pairing_config.dart';
import 'tts_service.dart';
import 'haptic_service.dart';

enum NovaConnectionStatus {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
}

/// Message types from backend
enum NovaMessageType {
  connected,
  onboardingComplete,
  feedback,
  confirmationRequest,
  result,
  error,
  pong,
  unknown,
}

/// Confirmation request from backend
class ConfirmationRequest {
  const ConfirmationRequest({
    required this.confirmationId,
    required this.action,
    required this.timeout,
  });

  final String confirmationId;
  final String action;
  final double timeout;

  factory ConfirmationRequest.fromJson(Map<String, dynamic> json) {
    return ConfirmationRequest(
      confirmationId: json['confirmation_id'] as String? ?? '',
      action: json['action'] as String? ?? 'Unknown action',
      timeout: (json['timeout'] as num?)?.toDouble() ?? 30.0,
    );
  }
}

/// WebSocket service with full message handling, TTS, and haptics
class NovaSocketService extends ChangeNotifier {
  NovaSocketService({
    TtsService? ttsService,
    HapticService? hapticService,
  }) : _tts = ttsService ?? TtsService(),
       _haptic = hapticService ?? HapticService();

  final TtsService _tts;
  final HapticService _haptic;

  PairingConfig? _config;
  WebSocket? _socket;
  Timer? _reconnectTimer;
  Timer? _pingTimer;
  Map<String, dynamic>? _lastResponse;
  NovaConnectionStatus _status = NovaConnectionStatus.disconnected;
  bool _shouldReconnect = false;
  bool _requiresOnboarding = false;
  ConfirmationRequest? _pendingConfirmation;
  Map<String, dynamic>? _userProfile;

  // Getters
  PairingConfig? get config => _config;
  Map<String, dynamic>? get lastResponse => _lastResponse;
  NovaConnectionStatus get status => _status;
  TtsService get tts => _tts;
  HapticService get haptic => _haptic;
  bool get requiresOnboarding => _requiresOnboarding;
  ConfirmationRequest? get pendingConfirmation => _pendingConfirmation;
  Map<String, dynamic>? get userProfile => _userProfile;

  String get statusLabel => switch (_status) {
        NovaConnectionStatus.disconnected => 'Disconnected',
        NovaConnectionStatus.connecting => 'Connecting',
        NovaConnectionStatus.connected => 'Connected',
        NovaConnectionStatus.reconnecting => 'Reconnecting',
        NovaConnectionStatus.error => 'Connection error',
      };

  // ============ CONNECTION MANAGEMENT ============

  Future<void> setPairing(PairingConfig? config) async {
    _shouldReconnect = false;
    await disconnect();
    _config = config;
    _lastResponse = null;
    _requiresOnboarding = false;
    _pendingConfirmation = null;
    if (_config != null) {
      _shouldReconnect = true;
      unawaited(connect());
    } else {
      _updateStatus(NovaConnectionStatus.disconnected);
    }
  }

  Future<void> connect() async {
    if (_config == null) return;
    if (_socket != null) return;
    _shouldReconnect = true;

    _reconnectTimer?.cancel();
    _updateStatus(
      _lastResponse == null
          ? NovaConnectionStatus.connecting
          : NovaConnectionStatus.reconnecting,
    );

    try {
      final WebSocket socket = await WebSocket.connect(_config!.websocketUrl);
      _socket = socket;
      _updateStatus(NovaConnectionStatus.connected);
      _startPingTimer();
      socket.listen(
        _handleMessage,
        onDone: _handleSocketClosed,
        onError: _handleSocketError,
        cancelOnError: true,
      );
    } catch (error) {
      _lastResponse = <String, dynamic>{
        'type': 'error',
        'message': 'Connection failed: $error',
      };
      _updateStatus(NovaConnectionStatus.error);
      await _tts.speakError('Connection failed');
      await _haptic.error();
      _scheduleReconnect();
    }
  }

  void _startPingTimer() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      _sendJson({'type': 'ping'});
    });
  }

  Future<void> disconnect() async {
    _reconnectTimer?.cancel();
    _pingTimer?.cancel();
    final WebSocket? activeSocket = _socket;
    _socket = null;
    if (activeSocket != null) {
      await activeSocket.close();
    }
    _updateStatus(NovaConnectionStatus.disconnected);
  }

  // ============ MESSAGE SENDING ============

  void _sendJson(Map<String, dynamic> data) {
    final WebSocket? socket = _socket;
    if (socket == null) return;
    socket.add(jsonEncode(data));
  }

  /// Send drawing as binary data
  Future<void> sendDrawing(Uint8List imageBytes) async {
    if (_socket == null) {
      await connect();
    }
    final WebSocket? activeSocket = _socket;
    if (activeSocket == null) {
      throw const SocketException('WebSocket is not connected');
    }
    activeSocket.add(imageBytes);
    await _tts.speakFeedback('Sending drawing');
    await _haptic.executionStart();
  }

  /// Send onboarding selections
  void sendOnboarding(List<int> selections) {
    _sendJson({
      'type': 'onboarding',
      'selections': selections,
    });
    _tts.speakFeedback('Sending preferences');
  }

  /// Send confirmation response
  void sendConfirmation(String confirmationId, bool confirmed) {
    _sendJson({
      'type': 'confirmation',
      'confirmation_id': confirmationId,
      'confirmed': confirmed,
    });
    _pendingConfirmation = null;
    notifyListeners();
    
    if (confirmed) {
      _tts.speakFeedback('Confirmed');
    } else {
      _tts.speakFeedback('Cancelled');
    }
  }

  /// Cancel a pending confirmation
  void cancelConfirmation(String confirmationId) {
    _sendJson({
      'type': 'cancel',
      'confirmation_id': confirmationId,
    });
    _pendingConfirmation = null;
    notifyListeners();
    _tts.speakFeedback('Action cancelled');
  }

  // ============ MESSAGE HANDLING ============

  void _handleMessage(dynamic data) {
    if (data is String) {
      try {
        final dynamic decoded = jsonDecode(data);
        if (decoded is Map<String, dynamic>) {
          _lastResponse = decoded;
          _routeMessage(decoded);
          notifyListeners();
        }
      } on FormatException {
        _lastResponse = <String, dynamic>{
          'type': 'error',
          'message': 'Server returned non-JSON data',
        };
        notifyListeners();
      }
    }
  }

  /// Route message to appropriate handler based on type
  void _routeMessage(Map<String, dynamic> message) {
    final type = _parseMessageType(message['type'] as String?);
    debugPrint('[WS RECEIVE] type=$type');

    switch (type) {
      case NovaMessageType.connected:
        _handleConnected(message);
      case NovaMessageType.onboardingComplete:
        _handleOnboardingComplete(message);
      case NovaMessageType.feedback:
        _handleFeedback(message);
      case NovaMessageType.confirmationRequest:
        _handleConfirmationRequest(message);
      case NovaMessageType.result:
        _handleResult(message);
      case NovaMessageType.error:
        _handleError(message);
      case NovaMessageType.pong:
        // Heartbeat response, no action needed
        break;
      case NovaMessageType.unknown:
        debugPrint('[WS] Unknown message type: ${message['type']}');
    }
  }

  NovaMessageType _parseMessageType(String? type) {
    return switch (type) {
      'connected' => NovaMessageType.connected,
      'onboarding_complete' => NovaMessageType.onboardingComplete,
      'feedback' => NovaMessageType.feedback,
      'confirmation_request' => NovaMessageType.confirmationRequest,
      'result' => NovaMessageType.result,
      'error' => NovaMessageType.error,
      'pong' => NovaMessageType.pong,
      _ => NovaMessageType.unknown,
    };
  }

  // ---- Handler: connected ----
  void _handleConnected(Map<String, dynamic> message) {
    _updateStatus(NovaConnectionStatus.connected);
    _requiresOnboarding = message['requires_onboarding'] == true;
    
    final welcomeMsg = message['message'] as String? ?? 'Connected to Rocket';
    _tts.speakFeedback(welcomeMsg);
    _haptic.success();
    
    if (_requiresOnboarding) {
      _tts.speak('Please complete onboarding setup', priority: TtsPriority.high);
    }
    notifyListeners();
  }

  // ---- Handler: onboarding_complete ----
  void _handleOnboardingComplete(Map<String, dynamic> message) {
    _requiresOnboarding = false;
    _userProfile = message['profile'] as Map<String, dynamic>?;
    
    _tts.speakFeedback('Onboarding complete. You are ready to use Rocket.');
    _haptic.success();
    notifyListeners();
  }

  // ---- Handler: feedback ----
  void _handleFeedback(Map<String, dynamic> message) {
    final text = message['text'] as String? ?? '';
    final priority = message['priority'] as String? ?? 'normal';
    final modes = message['mode'] as List<dynamic>? ?? ['voice', 'haptic'];
    final hapticPattern = message['haptic_pattern'] as Map<String, dynamic>?;

    // Determine TTS priority
    final ttsPriority = switch (priority) {
      'critical' => TtsPriority.critical,
      'high' => TtsPriority.high,
      'low' => TtsPriority.low,
      _ => TtsPriority.normal,
    };

    // Voice feedback
    if (modes.contains('voice') && text.isNotEmpty) {
      _tts.speak(text, priority: ttsPriority);
    }

    // Haptic feedback
    if (modes.contains('haptic')) {
      if (hapticPattern != null) {
        _haptic.customPattern(hapticPattern);
      } else {
        _haptic.tap();
      }
    }
  }

  // ---- Handler: confirmation_request ----
  void _handleConfirmationRequest(Map<String, dynamic> message) {
    final request = ConfirmationRequest.fromJson(message);
    _pendingConfirmation = request;
    
    // Critical speech + strong haptic
    _tts.speakConfirmation(
      'Confirmation required. ${request.action}. Double tap to confirm, or swipe to cancel.'
    );
    _haptic.confirmation();
    notifyListeners();
  }

  // ---- Handler: result ----
  void _handleResult(Map<String, dynamic> message) {
    final status = message['status'] as String? ?? 'unknown';
    final intent = message['intent'] as String? ?? '';
    final resultMessage = message['message'] as String? ?? '';
    final verified = message['verified'] == true;

    if (status == 'success') {
      final announcement = resultMessage.isNotEmpty 
          ? resultMessage 
          : 'Action $intent completed successfully';
      _tts.speakResult(announcement);
      
      if (verified) {
        _haptic.executionVerified();
      } else {
        _haptic.success();
      }
    } else {
      _tts.speakError('Action failed: $resultMessage');
      _haptic.error();
    }
  }

  // ---- Handler: error ----
  void _handleError(Map<String, dynamic> message) {
    final errorMsg = message['message'] as String? ?? 'An error occurred';
    _tts.speakError(errorMsg);
    _haptic.error();
  }

  // ============ SOCKET LIFECYCLE ============

  void _handleSocketClosed() {
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
    _lastResponse = <String, dynamic>{
      'type': 'error',
      'message': 'Socket error: $error',
    };
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
