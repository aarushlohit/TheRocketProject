import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'browser_bridge.dart' as browser;

void main() {
  runApp(const RocketBackendWebApp());
}

class RocketBackendWebApp extends StatelessWidget {
  const RocketBackendWebApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Rocket Backend',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0F63D8),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFF070A0F),
      ),
      home: const DashboardScreen(),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Timer? _timer;
  String _status = 'Checking';
  String _pairing = 'Loading pairing details...';
  String _websocket = 'ws://0.0.0.0:8765';
  String _message = 'Rocket Backend dashboard is starting.';
  bool _healthy = false;

  @override
  void initState() {
    super.initState();
    unawaited(_refresh());
    _timer = Timer.periodic(
      const Duration(seconds: 3),
      (_) => unawaited(_refresh()),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final uri = Uri.parse('${browser.origin}/api/status');
      final response = await http.get(uri).timeout(const Duration(seconds: 2));
      if (response.statusCode != 200) {
        throw StateError('Status ${response.statusCode}');
      }
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _healthy = data['running'] == true;
        _status = _healthy ? 'Running' : 'Starting';
        _websocket = data['websocket']?.toString() ?? _websocket;
        _pairing = data['pairing']?.toString() ?? _pairing;
        _message = data['message']?.toString() ?? 'Backend status loaded.';
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _healthy = false;
        _status = 'Disconnected';
        _message = 'Dashboard could not reach backend: $error';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.rocket_launch_rounded, size: 48),
                  const SizedBox(width: 16),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Rocket Backend',
                          style: TextStyle(
                            fontSize: 34,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        Text('No-Visual-Studio bundled backend software app'),
                      ],
                    ),
                  ),
                  _StatusPill(status: _status, healthy: _healthy),
                ],
              ),
              const SizedBox(height: 28),
              _InfoCard(
                title: 'Mobile Pairing',
                icon: Icons.qr_code_2_rounded,
                children: [
                  SelectableText(
                    _pairing,
                    style: const TextStyle(fontFamily: 'Consolas'),
                  ),
                  const SizedBox(height: 10),
                  Text('WebSocket: $_websocket'),
                  const SizedBox(height: 10),
                  const Text(
                    'Open Rocket mobile settings and scan the QR shown by the backend window/logs.',
                  ),
                ],
              ),
              const SizedBox(height: 18),
              _InfoCard(
                title: 'Runtime',
                icon: Icons.memory_rounded,
                children: [
                  Text(_message),
                  const SizedBox(height: 10),
                  const Text(
                    'Bundled pieces: Python backend, Python dependencies, Flutter web dashboard, OpenCode powers, and OpenCode CLI when available during packaging.',
                  ),
                ],
              ),
              const SizedBox(height: 28),
              Row(
                children: [
                  FilledButton.icon(
                    onPressed: _refresh,
                    icon: const Icon(Icons.refresh_rounded),
                    label: const Text('Refresh'),
                  ),
                  const SizedBox(width: 12),
                  OutlinedButton.icon(
                    onPressed: () => browser.openUrl('/api/pairing'),
                    icon: const Icon(Icons.data_object_rounded),
                    label: const Text('Open pairing JSON'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status, required this.healthy});

  final String status;
  final bool healthy;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
      decoration: BoxDecoration(
        color: healthy ? const Color(0xFF123D24) : const Color(0xFF3A1F22),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: healthy ? const Color(0xFF3FE07A) : const Color(0xFFFF7676),
        ),
      ),
      child: Text(status, style: const TextStyle(fontWeight: FontWeight.w800)),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({
    required this.title,
    required this.icon,
    required this.children,
  });

  final String title;
  final IconData icon;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1118),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: const Color(0xFF263241)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon),
              const SizedBox(width: 10),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ...children,
        ],
      ),
    );
  }
}
