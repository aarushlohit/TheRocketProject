import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../models/app_theme.dart';
import '../models/pairing_config.dart';
import '../services/nova_socket_service.dart';

class QrPairingScreen extends StatefulWidget {
  const QrPairingScreen({
    required this.socketService,
    super.key,
  });

  final NovaSocketService socketService;

  @override
  State<QrPairingScreen> createState() => _QrPairingScreenState();
}

class _QrPairingScreenState extends State<QrPairingScreen> {
  bool _handled = false;
  bool _announced = false;

  @override
  void initState() {
    super.initState();
    
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_announced) {
        _announced = true;
        widget.socketService.tts.speakOnce(
          'QR scanner active. Point camera at desktop QR code. '
          'Double tap close button to cancel.',
        );
        widget.socketService.haptic.executionStart();
      }
    });
  }

  void _handleCapture(BarcodeCapture capture) {
    if (_handled) return;

    final Barcode? barcode =
        capture.barcodes.isEmpty ? null : capture.barcodes.first;
    final String? rawValue = barcode?.rawValue;
    if (rawValue == null || rawValue.isEmpty) return;

    try {
      final PairingConfig config = PairingConfig.fromQrPayload(rawValue);
      _handled = true;
      
      // Success feedback
      widget.socketService.tts.speakOnce('QR code detected. Connecting.');
      widget.socketService.haptic.success();
      
      Navigator.of(context).pop(config);
    } on FormatException catch (error) {
      widget.socketService.tts.speakOnce('Invalid QR code. ${error.message}');
      widget.socketService.haptic.error();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // Camera view
          MobileScanner(
            onDetect: _handleCapture,
          ),

          // Overlay UI
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(AppTheme.spacingL),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Close button
                  Semantics(
                    button: true,
                    label: 'Close scanner',
                    child: GestureDetector(
                      onTap: () {
                        widget.socketService.tts.speakOnce('Double tap to close');
                        widget.socketService.haptic.selection();
                      },
                      onDoubleTap: () {
                        widget.socketService.haptic.tap();
                        Navigator.of(context).pop();
                      },
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.black.withOpacity(0.6),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.close_rounded,
                          color: Colors.white,
                          size: 28,
                        ),
                      ),
                    ),
                  ),

                  const Spacer(),

                  // Scanning frame
                  Center(
                    child: Container(
                      width: 280,
                      height: 280,
                      decoration: BoxDecoration(
                        border: Border.all(
                          color: AppTheme.primary,
                          width: 3,
                        ),
                        borderRadius: BorderRadius.circular(24),
                      ),
                      child: Stack(
                        children: [
                          // Corner decorations
                          Positioned(
                            top: -2,
                            left: -2,
                            child: Container(
                              width: 24,
                              height: 24,
                              decoration: const BoxDecoration(
                                color: AppTheme.primary,
                                borderRadius: BorderRadius.only(
                                  topLeft: Radius.circular(22),
                                ),
                              ),
                            ),
                          ),
                          Positioned(
                            top: -2,
                            right: -2,
                            child: Container(
                              width: 24,
                              height: 24,
                              decoration: const BoxDecoration(
                                color: AppTheme.primary,
                                borderRadius: BorderRadius.only(
                                  topRight: Radius.circular(22),
                                ),
                              ),
                            ),
                          ),
                          Positioned(
                            bottom: -2,
                            left: -2,
                            child: Container(
                              width: 24,
                              height: 24,
                              decoration: const BoxDecoration(
                                color: AppTheme.primary,
                                borderRadius: BorderRadius.only(
                                  bottomLeft: Radius.circular(22),
                                ),
                              ),
                            ),
                          ),
                          Positioned(
                            bottom: -2,
                            right: -2,
                            child: Container(
                              width: 24,
                              height: 24,
                              decoration: const BoxDecoration(
                                color: AppTheme.primary,
                                borderRadius: BorderRadius.only(
                                  bottomRight: Radius.circular(22),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const Spacer(),

                  // Instructions
                  Semantics(
                    liveRegion: true,
                    child: Container(
                      padding: const EdgeInsets.all(AppTheme.spacingL),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.7),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(
                                Icons.qr_code_scanner_rounded,
                                color: AppTheme.primary,
                                size: 28,
                              ),
                              const SizedBox(width: AppTheme.spacingM),
                              Text(
                                'Scan QR Code',
                                style: AppTheme.headingSmall.copyWith(
                                  color: Colors.white,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: AppTheme.spacingS),
                          Text(
                            'Point your camera at the Rocket desktop QR code to connect.',
                            style: AppTheme.bodyMedium.copyWith(
                              color: Colors.white.withOpacity(0.9),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
