import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'models/app_theme.dart';
import 'models/pairing_config.dart';
import 'models/user_profile.dart';
import 'screens/home_screen.dart';
import 'screens/onboarding_screen.dart';
import 'screens/splash_screen.dart';
import 'screens/success_screen.dart';
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

/// App navigation state
enum AppState {
  splash,
  onboarding,
  success,
  home,
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

  AppState _appState = AppState.splash;
  PairingConfig? _pairingConfig;
  UserProfile? _userProfile;

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
  }

  void _onSocketStateChanged() {
    setState(() {});
  }

  /// Called when splash screen finishes
  void _onSplashComplete() {
    _bootstrap();
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
      // Determine next screen
      if (!onboardingDone || savedProfile == null) {
        _appState = AppState.onboarding;
      } else {
        _appState = AppState.home;
        // Connect if paired
        if (savedPairing != null) {
          _socketService.setPairing(savedPairing);
        }
      }
    });
  }

  /// Called when user completes onboarding
  void _onOnboardingComplete(UserProfile profile) {
    setState(() {
      _userProfile = profile;
      _appState = AppState.success;
    });

    _store.saveProfile(profile);
    _socketService.setLocalOnboardingState(
      profile: profile,
      isOnboardingDone: true,
    );
  }

  /// Called when success countdown finishes
  void _onSuccessComplete() {
    setState(() {
      _appState = AppState.home;
    });

    // Clear TTS cache for fresh home experience
    _ttsService.clearSpokenCache();
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
      home: _buildCurrentScreen(),
    );
  }

  Widget _buildCurrentScreen() {
    return switch (_appState) {
      AppState.splash => SplashScreen(onComplete: _onSplashComplete),
      AppState.onboarding => OnboardingScreen(
          ttsService: _ttsService,
          hapticService: _hapticService,
          onComplete: _onOnboardingComplete,
        ),
      AppState.success => SuccessScreen(
          ttsService: _ttsService,
          hapticService: _hapticService,
          onComplete: _onSuccessComplete,
        ),
      AppState.home => HomeScreen(
          socketService: _socketService,
          pairingConfig: _pairingConfig,
          userProfile: _userProfile,
          onPairingChanged: _updatePairing,
        ),
    };
  }
}
