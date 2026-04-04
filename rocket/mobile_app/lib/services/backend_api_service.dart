import 'dart:convert';

import 'package:http/http.dart' as http;

/// Lightweight REST client for backend process/confirm endpoints.
class BackendApiService {
  BackendApiService({
    String baseUrl = 'http://localhost:8000',
    http.Client? client,
  }) : _baseUrl = baseUrl,
       _client = client ?? http.Client(),
       _ownsClient = client == null;

  final http.Client _client;
  final bool _ownsClient;
  String _baseUrl;

  String get baseUrl => _baseUrl;

  void setBaseUrl(String baseUrl) {
    _baseUrl = baseUrl;
  }

  Future<Map<String, dynamic>> processInput(String userInput) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/process'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'input': userInput}),
    );

    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> confirmPendingAction() async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/confirm'),
      headers: const {'Content-Type': 'application/json'},
      body: '{}',
    );

    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> getStatus() async {
    final response = await _client.get(
      Uri.parse('$_baseUrl/status'),
      headers: const {'Content-Type': 'application/json'},
    );

    return _decodeResponse(response);
  }

  Map<String, dynamic> _decodeResponse(http.Response response) {
    final dynamic decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('Backend response must be a JSON object');
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = decoded['message']?.toString() ?? 'Backend request failed';
      throw Exception(message);
    }

    return decoded;
  }

  void dispose() {
    if (_ownsClient) {
      _client.close();
    }
  }
}
