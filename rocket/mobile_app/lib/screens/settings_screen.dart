import 'package:flutter/material.dart';

import '../models/app_theme.dart';
import '../models/pairing_config.dart';
import '../services/nova_socket_service.dart';
import 'qr_pairing_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({
    required this.socketService,
    required this.currentPairing,
    required this.onPairingChanged,
    super.key,
  });

  final NovaSocketService socketService;
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
    widget.socketService.tts.clearSpokenCache();
    
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_announced) {
        _announced = true;
        final isPaired = widget.currentPairing != null;
        widget.socketService.tts.speakOnce(
          isPaired
              ? 'Settings. Connected to ${widget.currentPairing!.ip}. '
                'Double tap Scan QR to change connection.'
              : 'Settings. Not connected. Double tap Scan QR to connect.',
        );
      }
    });
  }

  Future<void> _scanQr(BuildContext context) async {
    widget.socketService.tts.clearSpokenCache();
    
    final PairingConfig? config = await Navigator.of(context).push<PairingConfig>(
      MaterialPageRoute<PairingConfig>(
        builder: (_) => QrPairingScreen(socketService: widget.socketService),
      ),
    );

    if (config == null) return;

    // Immediately update pairing (this triggers backend sync in main.dart)
    await widget.onPairingChanged(config);
    
    if (!context.mounted) return;
    
    widget.socketService.tts.speakOnce('Connected to ${config.ip}');
    widget.socketService.haptic.success();
  }

  void _reconnect() {
    widget.socketService.connect();
    widget.socketService.tts.speakOnce('Reconnecting');
    widget.socketService.haptic.tap();
  }

  void _clearPairing() {
    widget.onPairingChanged(null);
    widget.socketService.tts.speakOnce('Connection cleared');
    widget.socketService.haptic.tap();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.background,
        elevation: 0,
        leading: Semantics(
          button: true,
          label: 'Go back',
          child: IconButton(
            icon: const Icon(Icons.arrow_back_rounded),
            color: AppTheme.textPrimary,
            onPressed: () {
              widget.socketService.haptic.tap();
              Navigator.of(context).pop();
            },
          ),
        ),
        title: Text(
          'Settings',
          style: AppTheme.headingSmall.copyWith(
            color: AppTheme.textPrimary,
          ),
        ),
      ),
      body: ListenableBuilder(
        listenable: widget.socketService,
        builder: (context, _) {
          return ListView(
            padding: const EdgeInsets.all(AppTheme.spacingL),
            children: [
              // Connection status card
              _buildCard(
                title: 'Connection Status',
                icon: widget.socketService.status == NovaConnectionStatus.connected
                    ? Icons.wifi_rounded
                    : Icons.wifi_off_rounded,
                iconColor: widget.socketService.status == NovaConnectionStatus.connected
                    ? AppTheme.success
                    : AppTheme.error,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.socketService.statusLabel,
                      style: AppTheme.bodyLarge.copyWith(
                        color: widget.socketService.status == NovaConnectionStatus.connected
                            ? AppTheme.success
                            : AppTheme.error,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (widget.currentPairing != null) ...[
                      const SizedBox(height: AppTheme.spacingS),
                      Text(
                        '${widget.currentPairing!.ip}:${widget.currentPairing!.port}',
                        style: AppTheme.bodySmall,
                      ),
                    ],
                  ],
                ),
              ),
              
              const SizedBox(height: AppTheme.spacingM),

              // Pairing card
              _buildCard(
                title: 'Device Pairing',
                icon: Icons.qr_code_scanner_rounded,
                iconColor: AppTheme.primary,
                child: Text(
                  widget.currentPairing == null
                      ? 'No device paired. Scan a QR code to connect.'
                      : 'Paired with desktop computer.',
                  style: AppTheme.bodyMedium,
                ),
              ),

              const SizedBox(height: AppTheme.spacingXL),

              // Scan QR button (primary action)
              Semantics(
                button: true,
                label: 'Scan QR code to connect',
                child: GestureDetector(
                  onTap: () {
                    widget.socketService.tts.speakOnce('Double tap to scan');
                    widget.socketService.haptic.selection();
                  },
                  onDoubleTap: () => _scanQr(context),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 18),
                    decoration: AppTheme.primaryButtonDecoration,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.qr_code_scanner_rounded,
                          color: Colors.white,
                          size: 24,
                        ),
                        const SizedBox(width: AppTheme.spacingM),
                        Text(
                          'Scan Desktop QR',
                          style: AppTheme.buttonText,
                        ),
                      ],
                    ),
                  ),
                ),
              ),

              const SizedBox(height: AppTheme.spacingM),

              // Reconnect button
              Semantics(
                button: true,
                label: 'Reconnect to server',
                child: GestureDetector(
                  onTap: () {
                    widget.socketService.tts.speakOnce('Double tap to reconnect');
                    widget.socketService.haptic.selection();
                  },
                  onDoubleTap: _reconnect,
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    decoration: AppTheme.secondaryButtonDecoration,
                    child: Center(
                      child: Text(
                        'Reconnect',
                        style: AppTheme.buttonText.copyWith(
                          color: AppTheme.primary,
                        ),
                      ),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: AppTheme.spacingM),

              // Clear pairing button
              if (widget.currentPairing != null)
                Semantics(
                  button: true,
                  label: 'Clear connection',
                  child: GestureDetector(
                    onTap: () {
                      widget.socketService.tts.speakOnce('Double tap to clear');
                      widget.socketService.haptic.selection();
                    },
                    onDoubleTap: _clearPairing,
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      decoration: BoxDecoration(
                        color: AppTheme.error.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: AppTheme.error.withOpacity(0.3),
                          width: 2,
                        ),
                      ),
                      child: Center(
                        child: Text(
                          'Clear Connection',
                          style: AppTheme.buttonText.copyWith(
                            color: AppTheme.error,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildCard({
    required String title,
    required IconData icon,
    required Color iconColor,
    required Widget child,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppTheme.spacingL),
      decoration: AppTheme.cardDecoration(
        backgroundColor: Colors.white,
        hasShadow: true,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: iconColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              icon,
              color: iconColor,
              size: 24,
            ),
          ),
          const SizedBox(width: AppTheme.spacingM),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTheme.bodySmall.copyWith(
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textMuted,
                  ),
                ),
                const SizedBox(height: AppTheme.spacingS),
                child,
              ],
            ),
          ),
        ],
      ),
    );
  }
}
