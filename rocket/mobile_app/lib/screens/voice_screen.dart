import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

import '../models/app_theme.dart';
import '../services/nova_socket_service.dart';

class VoiceScreen extends StatefulWidget {
  const VoiceScreen({
    required this.socketService,
    super.key,
  });

  final NovaSocketService socketService;

  @override
  State<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends State<VoiceScreen> {
  final AudioRecorder _recorder = AudioRecorder();
  bool _recording = false;
  bool _sending = false;
  String? _path;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.socketService.tts.speakOnce(
        'Voice mode. Double tap the microphone to start recording. Double tap again to stop and send.',
      );
    });
  }

  @override
  void dispose() {
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _toggleRecording() async {
    if (_sending) return;

    if (_recording) {
      final path = await _recorder.stop();
      setState(() {
        _recording = false;
        _path = path;
      });
      await widget.socketService.tts.speakFeedback('Recording stopped');
      await _sendRecording();
      return;
    }

    final status = await Permission.microphone.request();
    if (!status.isGranted) {
      await widget.socketService.tts.speakError('Microphone permission is required');
      return;
    }

    final path = '${Directory.systemTemp.path}/rocket_voice_${DateTime.now().millisecondsSinceEpoch}.wav';
    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.wav),
      path: path,
    );
    setState(() {
      _recording = true;
      _path = path;
    });
    await widget.socketService.tts.speakFeedback('Recording started');
    await widget.socketService.haptic.executionStart();
  }

  Future<void> _sendRecording() async {
    final path = _path;
    if (path == null) return;
    setState(() {
      _sending = true;
    });
    try {
      final bytes = await File(path).readAsBytes();
      await widget.socketService.sendAudio(Uint8List.fromList(bytes));
    } catch (error) {
      await widget.socketService.tts.speakError('Voice send failed: $error');
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
      appBar: AppBar(
        title: const Text('Voice'),
      ),
      body: SafeArea(
        child: Center(
          child: Semantics(
            button: true,
            label: _recording ? 'Recording. Double tap to stop.' : 'Microphone. Double tap to record.',
            child: GestureDetector(
              onTap: () {
                widget.socketService.tts.speakOnce(
                  _recording ? 'Double tap to stop recording.' : 'Double tap to start recording.',
                );
                widget.socketService.haptic.selection();
              },
              onDoubleTap: _toggleRecording,
              child: Container(
                width: 220,
                height: 220,
                decoration: BoxDecoration(
                  color: _recording ? AppTheme.error : AppTheme.textPrimary,
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _recording ? Icons.stop_rounded : Icons.mic_rounded,
                  color: Colors.white,
                  size: 88,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
