import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import '../models/pairing_config.dart';

enum NovaConnectionStatus {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
}

class NovaSocketService extends ChangeNotifier {
  PairingConfig? _config;
  WebSocket? _socket;
  Timer? _reconnectTimer;
  Map<String, dynamic>? _lastResponse;
  NovaConnectionStatus _status = NovaConnectionStatus.disconnected;
  bool _shouldReconnect = false;

  PairingConfig? get config => _config;
  Map<String, dynamic>? get lastResponse => _lastResponse;
  NovaConnectionStatus get status => _status;

  String get statusLabel => switch (_status) {
        NovaConnectionStatus.disconnected => 'Disconnected',
        NovaConnectionStatus.connecting => 'Connecting',
        NovaConnectionStatus.connected => 'Connected',
        NovaConnectionStatus.reconnecting => 'Reconnecting',
        NovaConnectionStatus.error => 'Connection error',
      };

  Future<void> setPairing(PairingConfig? config) async {
    _shouldReconnect = false;
    await disconnect();
    _config = config;
    _lastResponse = null;
    if (_config != null) {
      _shouldReconnect = true;
      unawaited(connect());
    } else {
      _updateStatus(NovaConnectionStatus.disconnected);
    }
  }

  Future<void> connect() async {
    if (_config == null) {
      return;
    }
    if (_socket != null) {
      return;
    }
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
      socket.listen(
        _handleMessage,
        onDone: _handleSocketClosed,
        onError: _handleSocketError,
        cancelOnError: true,
      );
    } catch (error) {
      _lastResponse = <String, dynamic>{
        'status': 'error',
        'message': 'Connection failed: $error',
      };
      _updateStatus(NovaConnectionStatus.error);
      _scheduleReconnect();
    }
  }

  Future<void> sendDrawing(Uint8List imageBytes) async {
    if (_socket == null) {
      await connect();
    }
    final WebSocket? activeSocket = _socket;
    if (activeSocket == null) {
      throw const SocketException('WebSocket is not connected');
    }
    activeSocket.add(imageBytes);
  }

  Future<void> disconnect() async {
    _reconnectTimer?.cancel();
    final WebSocket? activeSocket = _socket;
    _socket = null;
    if (activeSocket != null) {
      await activeSocket.close();
    }
    _updateStatus(NovaConnectionStatus.disconnected);
  }

  void _handleMessage(dynamic data) {
    if (data is String) {
      try {
        final dynamic decoded = jsonDecode(data);
        if (decoded is Map<String, dynamic>) {
          _lastResponse = decoded;
          if (decoded['status'] == 'connected') {
            _updateStatus(NovaConnectionStatus.connected);
          }
          notifyListeners();
        }
      } on FormatException {
        _lastResponse = <String, dynamic>{
          'status': 'error',
          'message': 'Server returned non-JSON data',
        };
        notifyListeners();
      }
    }
  }

  void _handleSocketClosed() {
    _socket = null;
    if (_shouldReconnect) {
      _scheduleReconnect();
    } else {
      _updateStatus(NovaConnectionStatus.disconnected);
    }
  }

  void _handleSocketError(Object error) {
    _lastResponse = <String, dynamic>{
      'status': 'error',
      'message': 'Socket error: $error',
    };
    _socket = null;
    _updateStatus(NovaConnectionStatus.error);
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
    if (_status == nextStatus) {
      return;
    }
    _status = nextStatus;
    notifyListeners();
  }

  @override
  void dispose() {
    _reconnectTimer?.cancel();
    _shouldReconnect = false;
    unawaited(disconnect());
    super.dispose();
  }
}
