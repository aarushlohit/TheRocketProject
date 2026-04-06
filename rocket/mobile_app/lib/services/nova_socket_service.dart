import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import '../models/pairing_config.dart';
import '../models/user_profile.dart';
import 'backend_api_service.dart';
import 'haptic_service.dart';
import 'tts_service.dart';

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
    this.source = 'websocket',
  });

  final String confirmationId;
  final String action;
  final double timeout;
  final String source;

  factory ConfirmationRequest.fromJson(Map<String, dynamic> json) {
    final dynamic rawId = json['confirmation_id'] ?? json['id'];
    final dynamic rawAction = json['action'] ?? json['text'];

    return ConfirmationRequest(
      confirmationId: rawId?.toString() ?? '',
      action: rawAction?.toString() ?? 'Unknown action',
      timeout: (json['timeout'] as num?)?.toDouble() ?? 30.0,
      source: (json['source'] as String?) ?? 'websocket',
    );
  }

  factory ConfirmationRequest.fromApiResponse(Map<String, dynamic> json) {
    final action =
        json['action']?.toString() ??
        json['original_intent']?.toString() ??
        'Dangerous action';

    return ConfirmationRequest(
      confirmationId:
          json['confirmation_id']?.toString() ??
          'api-${DateTime.now().millisecondsSinceEpoch}',
      action: action,
      timeout: (json['timeout'] as num?)?.toDouble() ?? 30.0,
      source: 'api',
    );
  }
}

/// WebSocket service with full message handling, TTS, and haptics
class NovaSocketService extends ChangeNotifier {
  NovaSocketService({
    TtsService? ttsService,
    HapticService? hapticService,
  }) : _tts = ttsService ?? TtsService(),
      _haptic = hapticService ?? HapticService(),
      _api = BackendApiService();

  final TtsService _tts;
  final HapticService _haptic;
  final BackendApiService _api;

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
  UserProfile? _localProfile;
  bool _localOnboardingDone = false;

  // Triple-tap detection state (global, not UI-bound)
  int _tapCount = 0;
  Timer? _tapTimer;

  // Getters
  PairingConfig? get config => _config;
  Map<String, dynamic>? get lastResponse => _lastResponse;
  NovaConnectionStatus get status => _status;
  TtsService get tts => _tts;
  HapticService get haptic => _haptic;
  bool get requiresOnboarding => _requiresOnboarding;
  ConfirmationRequest? get pendingConfirmation {
    print("[GET PENDING CONFIRMATION] Accessing pendingConfirmation: ${_pendingConfirmation?.confirmationId ?? 'null'}");
    return _pendingConfirmation;
  }
  Map<String, dynamic>? get userProfile => _userProfile;

  @override
  void notifyListeners() {
    print("[NOTIFY LISTENERS] Called from NovaSocketService");
    print("[NOTIFY LISTENERS] Current _pendingConfirmation: ${_pendingConfirmation?.confirmationId ?? 'null'}");
    super.notifyListeners();
    print("[NOTIFY LISTENERS] Completed");
  }

  String get statusLabel => switch (_status) {
        NovaConnectionStatus.disconnected => 'Disconnected',
        NovaConnectionStatus.connecting => 'Connecting',
        NovaConnectionStatus.connected => 'Connected',
        NovaConnectionStatus.reconnecting => 'Reconnecting',
        NovaConnectionStatus.error => 'Connection error',
      };

  // ============ CONNECTION MANAGEMENT ============

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
    _api.setBaseUrl(_config?.httpBaseUrl ?? 'http://localhost:8000');
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
    print("[SEND JSON] Attempting to send: ${data['type']}");
    print("[SEND JSON] Full data: $data");
    
    final WebSocket? socket = _socket;
    if (socket == null) {
      print("[SEND JSON] ERROR: WebSocket is null! Cannot send.");
      return;
    }
    
    final jsonString = jsonEncode(data);
    print("[SEND JSON] Encoded JSON: $jsonString");
    socket.add(jsonString);
    print("[SEND JSON] Message sent successfully to WebSocket");
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
    await _haptic.executionStart();
  }

  /// Send onboarding selections
  void sendOnboarding(List<int> selections, {bool announce = true}) {
    _sendJson({
      'type': 'onboarding',
      'selections': selections,
    });
    if (announce) {
      _tts.speakFeedback('Saving your preferences');
    }
  }

  /// Send confirmation response
  void sendConfirmation(
    String confirmationId,
    bool confirmed, {
    String source = 'websocket',
  }) {
    if (source == 'api') {
      if (confirmed) {
        unawaited(_confirmViaApi());
      } else {
        _pendingConfirmation = null;
        notifyListeners();
        _tts.speakFeedback('Cancelled');
      }
      return;
    }

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

  void sendTripleTapConfirm(
    String confirmationId, {
    String source = 'websocket',
  }) {
    print("[SEND TRIPLE TAP] confirmationId=$confirmationId, source=$source");
    
    if (source == 'api') {
      unawaited(_confirmViaApi());
      _pendingConfirmation = null;
      notifyListeners();
      _tts.speakFeedback('Confirmation received');
      _haptic.confirmation();
      return;
    }

    print("[SEND TRIPLE TAP] Sending WebSocket message: triple_tap_confirm");
    _sendJson({
      'type': 'triple_tap_confirm',
      'confirmation_id': confirmationId,
    });
    _pendingConfirmation = null;
    notifyListeners();
    _tts.speakFeedback('Confirmation received');
    _haptic.confirmation();
  }

  /// Register a tap for triple-tap detection (global state, rebuild-safe)
  void registerTap(VoidCallback onTripleTap) {
    _tapCount++;
    print("[TAP SERVICE] Count: $_tapCount");
    
    _haptic.selection(); // Haptic feedback on each tap
    
    // Cancel existing timer
    _tapTimer?.cancel();
    
    // Check if we've reached 3+ taps
    if (_tapCount >= 3) {
      print("[TAP SERVICE] Triple tap detected! Calling callback...");
      _tapCount = 0;
      _tapTimer?.cancel();
      onTripleTap();
      return;
    }
    
    // Start timer to reset count if no more taps
    print("[TAP SERVICE] Starting timer to reset count after 2000ms");
    _tapTimer = Timer(const Duration(milliseconds: 2000), () {
      print("[TAP SERVICE] Timer expired. Resetting tap count from $_tapCount to 0");
      _tapCount = 0;
    });
  }

  /// Cancel a pending confirmation
  void cancelConfirmation(String confirmationId, {String source = 'websocket'}) {
    if (source == 'api') {
      _pendingConfirmation = null;
      notifyListeners();
      _tts.speakFeedback('Action cancelled');
      return;
    }

    _sendJson({
      'type': 'cancel',
      'confirmation_id': confirmationId,
    });
    _pendingConfirmation = null;
    notifyListeners();
    _tts.speakFeedback('Action cancelled');
  }

  Future<Map<String, dynamic>> processInputViaApi(String userInput) async {
    final trimmed = userInput.trim();
    if (trimmed.isEmpty) {
      throw Exception('Input cannot be empty');
    }

    final response = await _api.processInput(trimmed);
    final data = response;

    if (data['intent'] == 'CONFIRMATION_REQUIRED' ||
        data['status'] == 'confirmation_required') {
      _pendingConfirmation = ConfirmationRequest.fromApiResponse(data);
      _tts.speakConfirmation(
        'Triple tap in the drawing canvas to confirm action '
        '${_formatActionForSpeech(_pendingConfirmation!.action)}.',
      );
      _haptic.confirmation();
    } else {
      final message = data['message']?.toString() ?? 'Action completed';
      _tts.speakResult(message);
      if (data['status'] == 'success') {
        _haptic.executionVerified();
      } else {
        _haptic.error();
      }
    }

    _lastResponse = data;
    notifyListeners();
    return data;
  }

  Future<void> _confirmViaApi() async {
    try {
      final data = await _api.confirmPendingAction();
      _pendingConfirmation = null;
      _lastResponse = data;

      final status = data['status']?.toString() ?? 'unknown';
      final message = data['message']?.toString() ?? 'Confirmation processed';

      if (status == 'success') {
        _tts.speakResult(message);
        _haptic.executionVerified();
      } else {
        _tts.speakError(message);
        _haptic.error();
      }
      notifyListeners();
    } catch (error) {
      _tts.speakError('Confirmation failed: $error');
      _haptic.error();
    }
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
    print('[WS ROUTE] Routing message type=$type');
    print('[WS ROUTE] Full message: $message');

    switch (type) {
      case NovaMessageType.connected:
        print('[WS ROUTE] -> Calling _handleConnected');
        _handleConnected(message);
      case NovaMessageType.onboardingComplete:
        print('[WS ROUTE] -> Calling _handleOnboardingComplete');
        _handleOnboardingComplete(message);
      case NovaMessageType.feedback:
        print('[WS ROUTE] -> Calling _handleFeedback');
        _handleFeedback(message);
      case NovaMessageType.confirmationRequest:
        print('[WS ROUTE] -> Calling _handleConfirmationRequest');
        _handleConfirmationRequest(message);
      case NovaMessageType.result:
        print('[WS ROUTE] -> Calling _handleResult');
        _handleResult(message);
      case NovaMessageType.error:
        print('[WS ROUTE] -> Calling _handleError');
        _handleError(message);
      case NovaMessageType.pong:
        print('[WS ROUTE] -> Pong received');
        // Heartbeat response, no action needed
        break;
      case NovaMessageType.unknown:
        print('[WS ROUTE] -> Unknown message type: ${message['type']}');
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
    
    if (_localOnboardingDone && _localProfile != null) {
      _requiresOnboarding = false;
      sendOnboarding(_localProfile!.selectionIds, announce: false);
    } else if (_requiresOnboarding) {
      _tts.speak('Please complete onboarding setup', priority: TtsPriority.high);
    }
    notifyListeners();
  }

  // ---- Handler: onboarding_complete ----
  void _handleOnboardingComplete(Map<String, dynamic> message) {
    _requiresOnboarding = false;
    _localOnboardingDone = true;
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
    final event = message['event'] as String? ?? '';
    final hapticPattern = message['haptic_pattern'] as String?;
    final hapticData = message['haptic_data'] as List<dynamic>?;

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
      if (hapticData != null && hapticData.isNotEmpty) {
        _haptic.customPattern(<String, dynamic>{
          'pattern': hapticData.cast<int>(),
        });
      } else {
        _playNamedHaptic(hapticPattern ?? event);
      }
    }
  }

  // ---- Handler: confirmation_request ----
  void _handleConfirmationRequest(Map<String, dynamic> message) {
    print("[CONFIRMATION REQUEST] Received confirmation request");
    print("[CONFIRMATION REQUEST] Message: $message");
    
    final request = ConfirmationRequest.fromJson(message);
    _pendingConfirmation = request;
    
    print("[CONFIRMATION REQUEST] Created request with ID: ${request.confirmationId}");
    print("[CONFIRMATION REQUEST] Action: ${request.action}");
    print("[CONFIRMATION REQUEST] Source: ${request.source}");
    print("[CONFIRMATION REQUEST] Calling notifyListeners()");
    
    _tts.speakConfirmation(
      'Triple tap in the drawing canvas to confirm action '
      '${_formatActionForSpeech(request.action)}.'
    );
    _haptic.vibrate(duration: 220);
    notifyListeners();
    
    print("[CONFIRMATION REQUEST] Listeners notified. _pendingConfirmation is now: ${_pendingConfirmation?.confirmationId}");
  }

  // ---- Handler: result ----
  void _handleResult(Map<String, dynamic> message) {
    final status = message['status'] as String? ?? 'unknown';
    final intent = message['intent'] as String? ?? '';
    final resultMessage = message['message'] as String? ?? '';
    final verified = message['verified'] == true;

    if (status == 'confirmation_required' || intent == 'CONFIRMATION_REQUIRED') {
      _pendingConfirmation = ConfirmationRequest.fromApiResponse(message);
      _tts.speakConfirmation(
        'Triple tap in the drawing canvas to confirm action '
        '${_formatActionForSpeech(_pendingConfirmation!.action)}.',
      );
      _haptic.confirmation();
      notifyListeners();
      return;
    }

    _pendingConfirmation = null;

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
    _pendingConfirmation = null;
    _tts.speakError(errorMsg);
    _haptic.error();
  }

  String _formatActionForSpeech(String rawAction) {
    final cleaned = rawAction
        .replaceAll(RegExp(r'[{}_\[\]]'), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    return cleaned.isEmpty ? 'the pending action' : cleaned.toLowerCase();
  }

  Future<void> _playNamedHaptic(String? eventName) {
    switch (eventName) {
      case 'confirmation_required':
      case 'confirmation_waiting':
        return _haptic.confirmation();
      case 'danger_detected':
        return _haptic.danger();
      case 'execution_start':
      case 'model_processing':
      case 'input_received':
      case 'drawing_received':
        return _haptic.executionStart();
      case 'execution_verified':
        return _haptic.executionVerified();
      case 'execution_success':
      case 'model_success':
      case 'system_ready':
      case 'connection_open':
        return _haptic.success();
      case 'execution_failure':
      case 'model_failure':
      case 'system_error':
      case 'safety_blocked':
        return _haptic.error();
      default:
        return _haptic.tap();
    }
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
    _api.dispose();
    _tts.dispose();
    _haptic.dispose();
    super.dispose();
  }
}
