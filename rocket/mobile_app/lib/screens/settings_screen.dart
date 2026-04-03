import 'package:flutter/material.dart';

import '../models/pairing_config.dart';
import '../services/nova_socket_service.dart';
import 'qr_pairing_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({
    required this.socketService,
    required this.currentPairing,
    required this.onPairingChanged,
    super.key,
  });

  final NovaSocketService socketService;
  final PairingConfig? currentPairing;
  final Future<void> Function(PairingConfig? config) onPairingChanged;

  Future<void> _scanQr(BuildContext context) async {
    final PairingConfig? config = await Navigator.of(context).push<PairingConfig>(
      MaterialPageRoute<PairingConfig>(
        builder: (_) => const QrPairingScreen(),
      ),
    );

    if (config == null) {
      return;
    }

    await onPairingChanged(config);
    if (!context.mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Paired with ${config.ip}:${config.port}')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: socketService,
      builder: (BuildContext context, Widget? child) {
        final Map<String, dynamic>? response = socketService.lastResponse;
        return Scaffold(
          backgroundColor: const Color(0xFFF8F5EF),
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            elevation: 0,
            title: const Text('Settings'),
          ),
          body: ListView(
            padding: const EdgeInsets.all(24),
            children: <Widget>[
              _SettingsCard(
                title: 'Pairing',
                child: Text(
                  currentPairing == null
                      ? 'No desktop paired yet.'
                      : 'Connected target: ${currentPairing!.ip}:${currentPairing!.port}',
                  style: const TextStyle(fontSize: 16, height: 1.4),
                ),
              ),
              const SizedBox(height: 16),
              _SettingsCard(
                title: 'Connection',
                child: Text(
                  socketService.statusLabel,
                  style: const TextStyle(fontSize: 16, height: 1.4),
                ),
              ),
              if (response != null) ...<Widget>[
                const SizedBox(height: 16),
                _SettingsCard(
                  title: 'Last response',
                  child: Text(
                    response['message']?.toString() ?? 'No response yet',
                    style: const TextStyle(fontSize: 16, height: 1.4),
                  ),
                ),
              ],
              const SizedBox(height: 28),
              FilledButton(
                onPressed: () => _scanQr(context),
                child: const Text('Scan desktop QR'),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: socketService.connect,
                child: const Text('Reconnect now'),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () => onPairingChanged(null),
                child: const Text('Clear pairing'),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({
    required this.title,
    required this.child,
  });

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 20,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            title,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: Colors.black54,
            ),
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }
}
