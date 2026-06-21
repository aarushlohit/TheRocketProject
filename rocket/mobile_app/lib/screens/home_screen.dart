import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/app_theme.dart';
import '../models/pairing_config.dart';
import '../models/user_profile.dart';
import '../services/nova_socket_service.dart';
import '../widgets/quadrant_tile.dart';
import 'braille_screen.dart';
import 'drawing_screen.dart';
import 'settings_screen.dart';
import 'voice_screen.dart';

enum HomeQuadrant {
  voice,
  drawing,
  braille,
  settings,
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    required this.socketService,
    required this.pairingConfig,
    required this.userProfile,
    required this.onPairingChanged,
    super.key,
  });

  final NovaSocketService socketService;
  final PairingConfig? pairingConfig;
  final UserProfile? userProfile;
  final Future<void> Function(PairingConfig? config) onPairingChanged;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  HomeQuadrant? _selectedQuadrant;
  bool _guidanceAnnounced = false;

  @override
  void initState() {
    super.initState();
    widget.socketService.tts.clearSpokenCache();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _announceAdaptiveGuidance();
    });
  }

  void _announceAdaptiveGuidance() {
    if (_guidanceAnnounced) return;
    _guidanceAnnounced = true;

    final profile = widget.userProfile;
    final isPaired = widget.pairingConfig != null;

    String guidance = 'Home screen. ';

    if (!isPaired) {
      guidance += 'You need to connect to a computer. ';
      guidance += 'Double tap bottom right corner for settings, then scan QR code. ';
    } else {
      guidance += '${widget.socketService.statusLabel}. ';
    }

    if (profile != null) {
      if (profile.isVisuallyImpaired) {
        guidance += 'Double tap top right for drawing mode. ';
        guidance += 'All actions will be spoken aloud. ';
      } else if (profile.hasMotorDisability) {
        guidance += 'Large buttons are arranged in four corners. ';
        guidance += 'Drawing is at top right. Settings at bottom right. ';
      } else if (profile.hasCognitiveSupport) {
        guidance += 'Four big buttons. Drawing button at top right is ready to use. ';
      }
    } else {
      guidance += 'Four quadrants available. Drawing at top right, Settings at bottom right. ';
    }

    widget.socketService.tts.speakOnce(guidance);
    widget.socketService.haptic.success();
  }

  void _selectQuadrant(HomeQuadrant quadrant) {
    HapticFeedback.mediumImpact();
    setState(() {
      _selectedQuadrant = quadrant;
    });

    final label = switch (quadrant) {
      HomeQuadrant.voice => 'Voice Mode. Double tap to continue.',
      HomeQuadrant.drawing => 'Drawing Mode. Double tap to continue.',
      HomeQuadrant.braille => 'Braille Mode. Double tap to continue.',
      HomeQuadrant.settings => 'Settings. Double tap to open.',
    };
    widget.socketService.tts.speakOnce(label);
    widget.socketService.haptic.selection();
  }

  Future<void> _activateQuadrant(HomeQuadrant quadrant) async {
    _selectQuadrant(quadrant);

    switch (quadrant) {
      case HomeQuadrant.voice:
        widget.socketService.tts.clearSpokenCache();
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (_) => VoiceScreen(socketService: widget.socketService),
          ),
        );
        _guidanceAnnounced = false;
        widget.socketService.tts.clearSpokenCache();
        break;

      case HomeQuadrant.drawing:
        widget.socketService.tts.clearSpokenCache();
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (_) => DrawingScreen(socketService: widget.socketService),
          ),
        );
        _guidanceAnnounced = false;
        widget.socketService.tts.clearSpokenCache();
        break;

      case HomeQuadrant.settings:
        widget.socketService.tts.clearSpokenCache();
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (_) => SettingsScreen(
              socketService: widget.socketService,
              currentPairing: widget.pairingConfig,
              onPairingChanged: widget.onPairingChanged,
            ),
          ),
        );
        _guidanceAnnounced = false;
        widget.socketService.tts.clearSpokenCache();
        break;

      case HomeQuadrant.braille:
        widget.socketService.tts.clearSpokenCache();
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (_) => BrailleScreen(socketService: widget.socketService),
          ),
        );
        _guidanceAnnounced = false;
        widget.socketService.tts.clearSpokenCache();
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Column(
          children: [
            _buildStatusBar(),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(AppTheme.spacingS),
                child: Column(
                  children: [
                    Expanded(
                      child: Row(
                        children: [
                          Expanded(
                            child: QuadrantTile(
                              title: 'Voice',
                              subtitle: 'Record command',
                              icon: Icons.mic_none_rounded,
                              backgroundColor: AppTheme.cardVoice,
                              active: _selectedQuadrant == HomeQuadrant.voice,
                              onTap: () => _selectQuadrant(HomeQuadrant.voice),
                              onDoubleTap: () => _activateQuadrant(HomeQuadrant.voice),
                            ),
                          ),
                          Expanded(
                            child: QuadrantTile(
                              title: 'Drawing',
                              subtitle: 'Draw commands',
                              icon: Icons.draw_rounded,
                              backgroundColor: AppTheme.cardDrawing,
                              active: _selectedQuadrant == HomeQuadrant.drawing,
                              onTap: () => _selectQuadrant(HomeQuadrant.drawing),
                              onDoubleTap: () => _activateQuadrant(HomeQuadrant.drawing),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: Row(
                        children: [
                          Expanded(
                            child: QuadrantTile(
                              title: 'Braille',
                              subtitle: 'Braille to task',
                              icon: Icons.blur_on_rounded,
                              backgroundColor: AppTheme.cardBraille,
                              active: _selectedQuadrant == HomeQuadrant.braille,
                              onTap: () => _selectQuadrant(HomeQuadrant.braille),
                              onDoubleTap: () => _activateQuadrant(HomeQuadrant.braille),
                            ),
                          ),
                          Expanded(
                            child: QuadrantTile(
                              title: 'Settings',
                              subtitle: widget.pairingConfig == null
                                  ? 'Scan QR to connect'
                                  : 'Connection settings',
                              icon: Icons.settings_suggest_rounded,
                              backgroundColor: AppTheme.cardSettings,
                              active: _selectedQuadrant == HomeQuadrant.settings,
                              onTap: () => _selectQuadrant(HomeQuadrant.settings),
                              onDoubleTap: () => _activateQuadrant(HomeQuadrant.settings),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBar() {
    return ListenableBuilder(
      listenable: widget.socketService,
      builder: (context, _) {
        final connected = widget.socketService.status == NovaConnectionStatus.connected;
        final isPaired = widget.pairingConfig != null;

        return Semantics(
          label: isPaired
              ? 'Connection status: ${widget.socketService.statusLabel}'
              : 'Not connected. Go to settings to scan QR code.',
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppTheme.spacingM,
              vertical: AppTheme.spacingS,
            ),
            decoration: BoxDecoration(
              color: connected
                  ? AppTheme.success.withValues(alpha: 0.1)
                  : isPaired
                      ? AppTheme.warning.withValues(alpha: 0.1)
                      : AppTheme.error.withValues(alpha: 0.1),
              border: Border(
                bottom: BorderSide(
                  color: connected
                      ? AppTheme.success.withValues(alpha: 0.2)
                      : AppTheme.error.withValues(alpha: 0.2),
                  width: 1,
                ),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  connected
                      ? Icons.wifi_rounded
                      : isPaired
                          ? Icons.wifi_off_rounded
                          : Icons.link_off_rounded,
                  color: connected
                      ? AppTheme.success
                      : isPaired
                          ? AppTheme.warning
                          : AppTheme.textMuted,
                  size: 18,
                ),
                const SizedBox(width: AppTheme.spacingS),
                Text(
                  isPaired ? widget.socketService.statusLabel : 'Not connected',
                  style: AppTheme.bodySmall.copyWith(
                    color: connected
                        ? AppTheme.success
                        : isPaired
                            ? AppTheme.warning
                            : AppTheme.textMuted,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
