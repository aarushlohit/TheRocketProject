import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

import '../models/app_theme.dart';
import '../services/rocket_socket_service.dart';

enum _VoiceState {
  idle,
  listening,
  processing,
  sent,
}

class VoiceScreen extends StatefulWidget {
  const VoiceScreen({
    required this.socketService,
    super.key,
  });

  final RocketSocketService socketService;

  @override
  State<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends State<VoiceScreen> {
  final AudioRecorder _recorder = AudioRecorder();
  _VoiceState _state = _VoiceState.idle;
  bool _recording = false;
  bool _sending = false;
  String? _path;
  String? _lastSpokenTask;

  @override
  void initState() {
    super.initState();
    widget.socketService.addListener(_handleSocketUpdate);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.socketService.tts.speakOnce('Voice mode. Double tap to start.');
    });
  }

  @override
  void dispose() {
    widget.socketService.removeListener(_handleSocketUpdate);
    _recorder.dispose();
    super.dispose();
  }

  void _handleSocketUpdate() {
    final task = widget.socketService.lastTask;
    if (task == null ||
        task.source != 'voice' ||
        task.task == _lastSpokenTask) {
      return;
    }
    _lastSpokenTask = task.task;
    if (!mounted) return;
    setState(() => _state = _VoiceState.sent);
    widget.socketService.tts.speakResult('Task sent');
    widget.socketService.haptic.success();
  }

  Future<void> _startRecording() async {
    if (_recording || _sending) return;

    final status = await Permission.microphone.request();
    if (!status.isGranted) {
      await widget.socketService.tts
          .speakError('Microphone permission is required');
      await widget.socketService.haptic.error();
      return;
    }

    final path =
        '${Directory.systemTemp.path}/rocket_voice_${DateTime.now().millisecondsSinceEpoch}.wav';
    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.wav),
      path: path,
    );
    if (!mounted) return;
    setState(() {
      _recording = true;
      _path = path;
      _state = _VoiceState.listening;
    });
    await widget.socketService.tts.speakFeedback('Listening');
    await widget.socketService.haptic.executionStart();
  }

  Future<void> _stopAndSend() async {
    if (!_recording || _sending) return;
    final path = await _recorder.stop();
    if (!mounted) return;
    setState(() {
      _recording = false;
      _path = path ?? _path;
      _state = _VoiceState.processing;
    });
    await widget.socketService.tts.speakFeedback('Processing');
    await _sendRecording();
  }

  Future<void> _toggleRecording() async {
    if (_recording) {
      await _stopAndSend();
    } else {
      await _startRecording();
    }
  }

  Future<void> _sendRecording() async {
    final path = _path;
    if (path == null) return;
    setState(() => _sending = true);
    try {
      final bytes = await File(path).readAsBytes();
      await widget.socketService.sendAudio(Uint8List.fromList(bytes));
    } catch (error) {
      await widget.socketService.tts.speakError('Voice send failed: $error');
      await widget.socketService.haptic.error();
      if (mounted) setState(() => _state = _VoiceState.idle);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  String get _statusLabel => switch (_state) {
        _VoiceState.idle => 'Idle',
        _VoiceState.listening => 'Listening...',
        _VoiceState.processing => _sending ? 'Sending...' : 'Processing...',
        _VoiceState.sent => 'Sending...',
      };

  Color get _buttonColor => switch (_state) {
        _VoiceState.listening => AppTheme.error,
        _VoiceState.processing => AppTheme.warning,
        _VoiceState.sent => AppTheme.success,
        _ => AppTheme.textPrimary,
      };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () {
            widget.socketService.tts.speakOnce(
              _recording ? 'Double tap to send.' : 'Double tap to start.',
            );
          },
          onDoubleTap: _toggleRecording,
          child: Stack(
            children: [
              Positioned(
                top: AppTheme.spacingM,
                left: AppTheme.spacingM,
                child: _BackButton(onTap: () => Navigator.of(context).pop()),
              ),
              Center(
                child: Semantics(
                  liveRegion: true,
                  button: true,
                  label: _recording
                      ? 'Microphone. Listening. Double tap to send.'
                      : 'Microphone. $_statusLabel. Double tap to start.',
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 240,
                        height: 240,
                        decoration: BoxDecoration(
                          color: _buttonColor,
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 3),
                        ),
                        child: const Icon(
                          Icons.mic_rounded,
                          color: Colors.white,
                          size: 112,
                        ),
                      ),
                      const SizedBox(height: AppTheme.spacingXL),
                      Text(
                        _statusLabel,
                        style: AppTheme.headingLarge.copyWith(
                          color: Colors.white,
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
    );
  }
}

class _BackButton extends StatelessWidget {
  const _BackButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Back',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: const SizedBox(
          width: 72,
          height: 72,
          child: Icon(
            Icons.arrow_back_rounded,
            color: Colors.white,
            size: 40,
          ),
        ),
      ),
    );
  }
}
