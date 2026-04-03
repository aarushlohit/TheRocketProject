import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../models/pairing_config.dart';

class QrPairingScreen extends StatefulWidget {
  const QrPairingScreen({super.key});

  @override
  State<QrPairingScreen> createState() => _QrPairingScreenState();
}

class _QrPairingScreenState extends State<QrPairingScreen> {
  bool _handled = false;

  void _handleCapture(BarcodeCapture capture) {
    if (_handled) {
      return;
    }

    final Barcode? barcode =
        capture.barcodes.isEmpty ? null : capture.barcodes.first;
    final String? rawValue = barcode?.rawValue;
    if (rawValue == null || rawValue.isEmpty) {
      return;
    }

    try {
      final PairingConfig config = PairingConfig.fromQrPayload(rawValue);
      _handled = true;
      Navigator.of(context).pop(config);
    } on FormatException catch (error) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          MobileScanner(
            onDetect: _handleCapture,
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close, color: Colors.white),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.7),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Text(
                      'Point the camera at the Nova desktop QR code to pair this phone.',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        height: 1.35,
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
