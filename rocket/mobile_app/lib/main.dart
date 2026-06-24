import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'models/app_theme.dart';
import 'models/pairing_config.dart';
import 'models/user_profile.dart';
import 'screens/home_screen.dart';
import 'screens/onboarding_screen.dart';
import 'services/haptic_service.dart';
import 'services/nova_socket_service.dart';
import 'services/pairing_store.dart';
import 'services/tts_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  runApp(const RocketApp());
}

class RocketApp extends StatefulWidget {
  const RocketApp({super.key});

  @override
  State<RocketApp> createState() => _RocketAppState();
}

class _RocketAppState extends State<RocketApp> with WidgetsBindingObserver {
  final PairingStore _store = PairingStore();
  late final TtsService _ttsService;
  late final HapticService _hapticService;
  late final NovaSocketService _socketService;

  PairingConfig? _pairingConfig;
  UserProfile? _userProfile;
  bool _bootstrapped = false;
  bool _onboardingComplete = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    _ttsService = TtsService();
    _hapticService = HapticService();
    _socketService = NovaSocketService(
      ttsService: _ttsService,
      hapticService: _hapticService,
    );

    _socketService.addListener(_onSocketStateChanged);
    _bootstrap();
  }

  void _onSocketStateChanged() {
    setState(() {});
  }

  /// Load saved data and determine initial screen
  Future<void> _bootstrap() async {
    final savedPairing = await _store.load();
    final savedProfile = await _store.loadProfile();
    final onboardingDone = await _store.isOnboardingComplete();
    _socketService.setLocalOnboardingState(
      profile: savedProfile,
      isOnboardingDone: onboardingDone,
    );

    if (!mounted) return;

    setState(() {
      _pairingConfig = savedPairing;
      _userProfile = savedProfile;
      _onboardingComplete = onboardingDone && (savedProfile?.onboardingCompleted ?? false);
      _bootstrapped = true;
      if (savedPairing != null) {
        _socketService.setPairing(savedPairing);
      }
    });
  }

  /// Update pairing config (from QR scan)
  Future<void> _updatePairing(PairingConfig? config) async {
    if (config == null) {
      await _store.clear();
    } else {
      await _store.save(config);
    }

    await _socketService.setPairing(config);

    if (!mounted) return;
    setState(() {
      _pairingConfig = config;
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _pairingConfig != null) {
      _socketService.connect();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _socketService.removeListener(_onSocketStateChanged);
    _socketService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Rocket',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.themeData,
      home: !_bootstrapped
          ? const Scaffold(
              backgroundColor: AppTheme.background,
              body: Center(child: CircularProgressIndicator()),
            )
          : !_onboardingComplete
              ? OnboardingScreen(
                  ttsService: _ttsService,
                  hapticService: _hapticService,
                  onComplete: _completeOnboarding,
                )
              : HomeScreen(
                  socketService: _socketService,
                  pairingConfig: _pairingConfig,
                  userProfile: _userProfile,
                  onPairingChanged: _updatePairing,
                ),
    );
  }

  Future<void> _completeOnboarding(UserProfile profile) async {
    await _store.saveProfile(profile);
    _socketService.setLocalOnboardingState(
      profile: profile,
      isOnboardingDone: true,
    );
    if (!mounted) return;
    setState(() {
      _userProfile = profile;
      _onboardingComplete = true;
    });
  }
}
