import 'dart:convert';

class PairingConfig {
  const PairingConfig({
    required this.ip,
    required this.port,
    required this.token,
  });

  final String ip;
  final int port;
  final String token;

  String get websocketUrl => 'ws://$ip:$port?token=$token';

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'ip': ip,
      'port': port,
      'token': token,
    };
  }

  factory PairingConfig.fromJson(Map<String, dynamic> json) {
    final dynamic ipValue = json['ip'];
    final dynamic portValue = json['port'];
    final dynamic tokenValue = json['token'];

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

    return PairingConfig(
      ip: ipValue.trim(),
      port: parsedPort,
      token: tokenValue.trim(),
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
