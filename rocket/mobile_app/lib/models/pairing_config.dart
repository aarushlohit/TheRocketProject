import 'dart:convert';

class PairingConfig {
  const PairingConfig({
    required this.ip,
    required this.port,
    required this.token,
    this.httpPort = 8000,
  });

  final String ip;
  final int port;
  final String token;
  final int httpPort;

  String get websocketUrl => 'ws://$ip:$port?token=$token';
  String get httpBaseUrl => 'http://$ip:$httpPort';

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'ip': ip,
      'port': port,
      'token': token,
      'http_port': httpPort,
    };
  }

  factory PairingConfig.fromJson(Map<String, dynamic> json) {
    final dynamic ipValue = json['ip'];
    final dynamic portValue = json['port'];
    final dynamic tokenValue = json['token'];
    final dynamic httpPortValue = json['http_port'];

    if (ipValue is! String || ipValue.trim().isEmpty) {
      throw const FormatException('Pairing payload is missing a valid ip');
    }
    if (tokenValue is! String || tokenValue.trim().isEmpty) {
      throw const FormatException('Pairing payload is missing a valid token');
    }

    final int? parsedPort = switch (portValue) {
      int value => value,
      String value => int.tryParse(value),
      _ => null,
    };

    if (parsedPort == null) {
      throw const FormatException('Pairing payload is missing a valid port');
    }

    final int httpPort = switch (httpPortValue) {
      int value => value,
      String value => int.tryParse(value) ?? 8000,
      _ => 8000,
    };

    return PairingConfig(
      ip: ipValue.trim(),
      port: parsedPort,
      token: tokenValue.trim(),
      httpPort: httpPort,
    );
  }

  factory PairingConfig.fromQrPayload(String rawPayload) {
    final dynamic decoded = jsonDecode(rawPayload);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('QR payload must decode to a JSON object');
    }
    return PairingConfig.fromJson(decoded);
  }
}
