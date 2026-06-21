import 'package:flutter/material.dart';
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

    widget.socketService.tts.speakOnce(
      'Rocket. Top left voice. Top right draw. Bottom left braille. Bottom right settings.',
    );
  }

  void _selectQuadrant(HomeQuadrant quadrant) {
    final label = switch (quadrant) {
      HomeQuadrant.voice => 'Voice mode. Double tap to enter.',
      HomeQuadrant.drawing => 'Drawing mode. Double tap to enter.',
      HomeQuadrant.braille => 'Braille mode. Double tap to enter.',
      HomeQuadrant.settings => 'Settings. Double tap to enter.',
    };
    widget.socketService.tts.speakOnce(label);
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
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Row(
                children: [
                  Expanded(
                    child: QuadrantTile(
                      title: 'Voice',
                      icon: Icons.mic_rounded,
                      backgroundColor: Colors.black,
                      onTap: () => _selectQuadrant(HomeQuadrant.voice),
                      onDoubleTap: () => _activateQuadrant(HomeQuadrant.voice),
                    ),
                  ),
                  Expanded(
                    child: QuadrantTile(
                      title: 'Draw',
                      icon: Icons.edit_rounded,
                      backgroundColor: const Color(0xFF111111),
                      onTap: () => _selectQuadrant(HomeQuadrant.drawing),
                      onDoubleTap: () =>
                          _activateQuadrant(HomeQuadrant.drawing),
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
                      symbol: '⠿',
                      backgroundColor: const Color(0xFF111111),
                      onTap: () => _selectQuadrant(HomeQuadrant.braille),
                      onDoubleTap: () =>
                          _activateQuadrant(HomeQuadrant.braille),
                    ),
                  ),
                  Expanded(
                    child: QuadrantTile(
                      title: 'Settings',
                      icon: Icons.settings_rounded,
                      backgroundColor: Colors.black,
                      onTap: () => _selectQuadrant(HomeQuadrant.settings),
                      onDoubleTap: () =>
                          _activateQuadrant(HomeQuadrant.settings),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
