import 'package:flutter/material.dart';

import '../models/app_theme.dart';
import '../models/pairing_config.dart';
import '../services/rocket_socket_service.dart';
import 'qr_pairing_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({
    required this.socketService,
    required this.currentPairing,
    required this.onPairingChanged,
    super.key,
  });

  final RocketSocketService socketService;
  final PairingConfig? currentPairing;
  final Future<void> Function(PairingConfig? config) onPairingChanged;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _announced = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_announced) return;
      _announced = true;
      final paired = widget.currentPairing != null;
      widget.socketService.tts.speakOnce(
        paired
            ? 'Settings. Current connection ${widget.currentPairing!.ip}. Backend Nemotron with Pollinations fallback.'
            : 'Settings. No desktop connected. Double tap scan desktop QR.',
      );
    });
  }

  Future<void> _scanQr() async {
    await widget.socketService.tts.speakFeedback('Scanning QR code');
    if (!mounted) return;
    final config = await Navigator.of(context).push<PairingConfig>(
      MaterialPageRoute(
        builder: (_) => QrPairingScreen(socketService: widget.socketService),
      ),
    );
    if (!mounted) return;
    if (config == null) return;
    await widget.onPairingChanged(config);
    if (!mounted) return;
    await widget.socketService.tts.speakFeedback('Pairing successful');
    await widget.socketService.haptic.success();
  }

  Future<void> _clearPairing() async {
    await widget.onPairingChanged(null);
    await widget.socketService.tts.speakFeedback('Pairing cleared');
    await widget.socketService.haptic.tap();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(title: const Text('Settings')),
      body: ListenableBuilder(
        listenable: widget.socketService,
        builder: (context, _) {
          return Padding(
            padding: const EdgeInsets.all(AppTheme.spacingM),
            child: Column(
              children: [
                _InfoRow(
                  label: 'Desktop Pairing',
                  value:
                      widget.currentPairing == null ? 'Not paired' : 'Paired',
                ),
                _InfoRow(
                  label: 'Connection State',
                  value: widget.socketService.statusLabel,
                ),
                const _InfoRow(label: 'Backend', value: 'Nemotron'),
                const SizedBox(height: AppTheme.spacingS),
                const Text('Speech Speed', style: AppTheme.headingSmall),
                Slider(
                  semanticFormatterCallback: (value) =>
                      'Speech speed ${value.toStringAsFixed(1)}',
                  value: widget.socketService.tts.speechRate,
                  min: 0.2,
                  max: 0.9,
                  divisions: 7,
                  label: widget.socketService.tts.speechRate.toStringAsFixed(1),
                  onChanged: (value) {
                    widget.socketService.tts.setSpeechRate(value);
                  },
                  onChangeEnd: (_) {
                    widget.socketService.tts
                        .speakFeedback('Speech speed updated');
                  },
                ),
                const SizedBox(height: AppTheme.spacingS),
                _ActionButton(
                  label: 'QR Scan',
                  icon: Icons.qr_code_scanner_rounded,
                  onTap: () {
                    widget.socketService.tts.speakOnce('Double tap QR scan');
                  },
                  onDoubleTap: _scanQr,
                ),
                const SizedBox(height: AppTheme.spacingS),
                _ActionButton(
                  label: 'Reconnect',
                  icon: Icons.sync_rounded,
                  onTap: () {
                    widget.socketService.tts.speakOnce('Double tap reconnect');
                  },
                  onDoubleTap: () {
                    widget.socketService.connect();
                    widget.socketService.tts.speakFeedback('Reconnecting');
                  },
                ),
                const SizedBox(height: AppTheme.spacingS),
                _ActionButton(
                  label: 'Clear Pairing',
                  icon: Icons.link_off_rounded,
                  onTap: () {
                    widget.socketService.tts
                        .speakOnce('Double tap clear pairing');
                  },
                  onDoubleTap: _clearPairing,
                  destructive: true,
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 52),
      padding: const EdgeInsets.symmetric(vertical: AppTheme.spacingXS),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: Colors.black12)),
      ),
      child: Row(
        children: [
          Expanded(child: Text(label, style: AppTheme.bodyMedium)),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: AppTheme.bodyLarge,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.label,
    required this.icon,
    required this.onTap,
    required this.onDoubleTap,
    this.destructive = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final VoidCallback onDoubleTap;
  final bool destructive;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '$label. Double tap to continue.',
      child: GestureDetector(
        onTap: onTap,
        onDoubleTap: onDoubleTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 72),
          decoration: BoxDecoration(
            color: destructive ? AppTheme.error : AppTheme.textPrimary,
            borderRadius: BorderRadius.circular(18),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: Colors.white, size: 28),
              const SizedBox(width: AppTheme.spacingS),
              Text(label, style: AppTheme.buttonText),
            ],
          ),
        ),
      ),
    );
  }
}
