import 'package:flutter/material.dart';

import '../models/app_theme.dart';
import '../services/nova_socket_service.dart';

class BrailleScreen extends StatefulWidget {
  const BrailleScreen({
    required this.socketService,
    super.key,
  });

  final NovaSocketService socketService;

  @override
  State<BrailleScreen> createState() => _BrailleScreenState();
}

class _BrailleScreenState extends State<BrailleScreen> {
  final TextEditingController _controller = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.socketService.tts.speakOnce(
        'Braille mode. Enter braille text or translated cells, then double tap send.',
      );
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty) {
      await widget.socketService.tts.speakOnce('Braille input is empty');
      await widget.socketService.haptic.error();
      return;
    }
    setState(() {
      _sending = true;
    });
    try {
      await widget.socketService.sendBraille(text);
      _controller.clear();
    } catch (error) {
      await widget.socketService.tts.speakError('Braille send failed: $error');
      await widget.socketService.haptic.error();
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(title: const Text('Braille')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppTheme.spacingL),
          child: Column(
            children: [
              TextField(
                controller: _controller,
                minLines: 6,
                maxLines: 8,
                style: AppTheme.bodyLarge,
                decoration: const InputDecoration(
                  labelText: 'Braille input',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: AppTheme.spacingL),
              Semantics(
                button: true,
                label: 'Send braille. Double tap to send.',
                child: GestureDetector(
                  onTap: () {
                    widget.socketService.tts.speakOnce('Double tap to send braille');
                    widget.socketService.haptic.selection();
                  },
                  onDoubleTap: _sending ? null : _send,
                  child: Container(
                    width: double.infinity,
                    constraints: const BoxConstraints(minHeight: 120),
                    alignment: Alignment.center,
                    decoration: AppTheme.primaryButtonDecoration,
                    child: Text(
                      _sending ? 'Sending...' : 'Send Braille',
                      style: AppTheme.buttonText,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
