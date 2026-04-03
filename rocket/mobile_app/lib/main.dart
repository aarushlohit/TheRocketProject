import 'package:flutter/material.dart';

import 'models/pairing_config.dart';
import 'screens/home_screen.dart';
import 'services/nova_socket_service.dart';
import 'services/pairing_store.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const NovaApp());
}

class NovaApp extends StatefulWidget {
  const NovaApp({super.key});

  @override
  State<NovaApp> createState() => _NovaAppState();
}

class _NovaAppState extends State<NovaApp> {
  final PairingStore _pairingStore = PairingStore();
  late final NovaSocketService _socketService;
  PairingConfig? _pairingConfig;
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    _socketService = NovaSocketService();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final PairingConfig? savedPairing = await _pairingStore.load();
    await _socketService.setPairing(savedPairing);
    if (!mounted) {
      return;
    }
    setState(() {
      _pairingConfig = savedPairing;
      _ready = true;
    });
  }

  Future<void> _updatePairing(PairingConfig? config) async {
    if (config == null) {
      await _pairingStore.clear();
    } else {
      await _pairingStore.save(config);
    }
    await _socketService.setPairing(config);
    if (!mounted) {
      return;
    }
    setState(() {
      _pairingConfig = config;
    });
  }

  @override
  void dispose() {
    _socketService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Nova',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFBF6C2C)),
        scaffoldBackgroundColor: const Color(0xFFF3EEE7),
      ),
      home: _ready
          ? HomeScreen(
              socketService: _socketService,
              pairingConfig: _pairingConfig,
              onPairingChanged: _updatePairing,
            )
          : const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            ),
    );
  }
}
