import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/pairing_config.dart';
import '../services/nova_socket_service.dart';
import '../widgets/quadrant_tile.dart';
import 'drawing_screen.dart';
import 'settings_screen.dart';

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
    required this.onPairingChanged,
    super.key,
  });

  final NovaSocketService socketService;
  final PairingConfig? pairingConfig;
  final Future<void> Function(PairingConfig? config) onPairingChanged;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  HomeQuadrant? _selectedQuadrant;

  void _selectQuadrant(HomeQuadrant quadrant) {
    HapticFeedback.mediumImpact();
    setState(() {
      _selectedQuadrant = quadrant;
    });
  }

  Future<void> _activateQuadrant(HomeQuadrant quadrant) async {
    _selectQuadrant(quadrant);

    switch (quadrant) {
      case HomeQuadrant.drawing:
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (_) => DrawingScreen(socketService: widget.socketService),
          ),
        );
      case HomeQuadrant.settings:
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (_) => SettingsScreen(
              socketService: widget.socketService,
              currentPairing: widget.pairingConfig,
              onPairingChanged: widget.onPairingChanged,
            ),
          ),
        );
      case HomeQuadrant.voice:
      case HomeQuadrant.braille:
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Stage 0 focuses on drawing mode only.')),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3EEE7),
      body: SafeArea(
        child: Column(
          children: <Widget>[
            Expanded(
              child: Row(
                children: <Widget>[
                  Expanded(
                    child: QuadrantTile(
                      title: 'Voice',
                      subtitle: 'Inactive for Stage 0',
                      icon: Icons.mic_none_rounded,
                      backgroundColor: const Color(0xFFE9F2FF),
                      active: _selectedQuadrant == HomeQuadrant.voice,
                      onTap: () => _selectQuadrant(HomeQuadrant.voice),
                      onDoubleTap: () => _activateQuadrant(HomeQuadrant.voice),
                    ),
                  ),
                  Expanded(
                    child: QuadrantTile(
                      title: 'Drawing',
                      subtitle: 'Double tap to enter draw-to-action mode',
                      icon: Icons.draw_rounded,
                      backgroundColor: const Color(0xFFFFF0DE),
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
                children: <Widget>[
                  Expanded(
                    child: QuadrantTile(
                      title: 'Braille',
                      subtitle: 'Inactive for Stage 0',
                      icon: Icons.blur_on_rounded,
                      backgroundColor: const Color(0xFFE3F5ED),
                      active: _selectedQuadrant == HomeQuadrant.braille,
                      onTap: () => _selectQuadrant(HomeQuadrant.braille),
                      onDoubleTap: () => _activateQuadrant(HomeQuadrant.braille),
                    ),
                  ),
                  Expanded(
                    child: QuadrantTile(
                      title: 'Settings',
                      subtitle: widget.pairingConfig == null
                          ? 'Pair to a desktop with QR'
                          : 'Connection and pairing',
                      icon: Icons.settings_suggest_rounded,
                      backgroundColor: const Color(0xFFF2E7FF),
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
    );
  }
}
