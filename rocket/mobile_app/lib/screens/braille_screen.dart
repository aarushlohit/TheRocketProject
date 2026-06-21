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
  final Set<int> _activeDots = <int>{};
  final List<String> _cells = <String>[];
  bool _sending = false;
  String? _lastSpokenTask;

  @override
  void initState() {
    super.initState();
    widget.socketService.addListener(_handleSocketUpdate);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.socketService.tts.speakOnce(
        'Braille mode. Eight dot keyboard. Single tap hears a dot. Double tap toggles it.',
      );
    });
  }

  @override
  void dispose() {
    widget.socketService.removeListener(_handleSocketUpdate);
    super.dispose();
  }

  void _handleSocketUpdate() {
    final task = widget.socketService.lastTask;
    if (task == null ||
        task.source != 'braille' ||
        task.task == _lastSpokenTask) {
      return;
    }
    _lastSpokenTask = task.task;
    widget.socketService.tts.speakResult('Intent recognized. ${task.task}');
    widget.socketService.tts.speakFeedback('Task sent');
    widget.socketService.haptic.success();
  }

  String _dotName(int dot) {
    const names = <int, String>{
      1: 'Dot one',
      2: 'Dot two',
      3: 'Dot three',
      4: 'Dot four',
      5: 'Dot five',
      6: 'Dot six',
      7: 'Dot seven',
      8: 'Dot eight',
    };
    return names[dot]!;
  }

  Future<void> _vibrateDot(int dot) {
    return widget.socketService.haptic.vibrate(
      duration: 35 + (dot * 18),
      amplitude: 48 + (dot * 18),
    );
  }

  void _focusDot(int dot) {
    final selected = _activeDots.contains(dot);
    widget.socketService.tts.speakOnce(
      '${_dotName(dot)}. ${selected ? "Selected" : "Not selected"}. Double tap to toggle.',
    );
    _vibrateDot(dot);
  }

  void _toggleDot(int dot) {
    setState(() {
      if (_activeDots.contains(dot)) {
        _activeDots.remove(dot);
      } else {
        _activeDots.add(dot);
      }
    });
    final selected = _activeDots.contains(dot);
    widget.socketService.tts.speakOnce(
      '${_dotName(dot)} ${selected ? "selected" : "removed"}.',
    );
    _vibrateDot(dot);
  }

  void _commitCell() {
    if (_activeDots.isEmpty) {
      _cells.add('[space]');
      widget.socketService.tts.speakOnce('Space added');
      widget.socketService.haptic.tap();
      setState(() {});
      return;
    }
    final dots = _activeDots.toList()..sort();
    final cell = '[${dots.join("-")}]';
    setState(() {
      _cells.add(cell);
      _activeDots.clear();
    });
    widget.socketService.tts.speakOnce('Cell added. $cell');
    widget.socketService.haptic.tap();
  }

  void _backspace() {
    setState(() {
      if (_activeDots.isNotEmpty) {
        _activeDots.clear();
      } else if (_cells.isNotEmpty) {
        _cells.removeLast();
      }
    });
    widget.socketService.tts.speakOnce('Backspace');
    widget.socketService.haptic.tap();
  }

  Future<void> _send() async {
    if (_sending) return;
    final pending = _activeDots.toList()..sort();
    final payload = [
      ..._cells,
      if (pending.isNotEmpty) '[${pending.join("-")}]',
    ].join(' ');

    if (payload.trim().isEmpty) {
      await widget.socketService.tts.speakOnce('Braille input is empty');
      await widget.socketService.haptic.error();
      return;
    }

    setState(() => _sending = true);
    try {
      await widget.socketService.sendBraille(payload);
      if (!mounted) return;
      setState(() {
        _cells.clear();
        _activeDots.clear();
      });
    } catch (error) {
      await widget.socketService.tts.speakError('Braille send failed: $error');
      await widget.socketService.haptic.error();
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: const Text('Braille')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppTheme.spacingL),
          child: Column(
            children: [
              Expanded(
                child: Column(
                  children: List.generate(4, (row) {
                    final leftDot = row + 1;
                    final rightDot = row + 5;
                    return Expanded(
                      child: Padding(
                        padding:
                            const EdgeInsets.only(bottom: AppTheme.spacingM),
                        child: Row(
                          children: [
                            Expanded(
                              child: _DotButton(
                                dot: leftDot,
                                label: _dotName(leftDot),
                                selected: _activeDots.contains(leftDot),
                                onTap: () => _focusDot(leftDot),
                                onDoubleTap: () => _toggleDot(leftDot),
                              ),
                            ),
                            const SizedBox(width: AppTheme.spacingM),
                            Expanded(
                              child: _DotButton(
                                dot: rightDot,
                                label: _dotName(rightDot),
                                selected: _activeDots.contains(rightDot),
                                onTap: () => _focusDot(rightDot),
                                onDoubleTap: () => _toggleDot(rightDot),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                ),
              ),
              Row(
                children: [
                  Expanded(
                    child: _ControlButton(
                      label: 'Backspace',
                      icon: Icons.backspace_rounded,
                      onTap: () {
                        widget.socketService.tts
                            .speakOnce('Double tap backspace');
                        widget.socketService.haptic.selection();
                      },
                      onDoubleTap: _backspace,
                    ),
                  ),
                  const SizedBox(width: AppTheme.spacingM),
                  Expanded(
                    child: _ControlButton(
                      label: 'Space',
                      icon: Icons.space_bar_rounded,
                      onTap: () {
                        widget.socketService.tts.speakOnce('Double tap space');
                        widget.socketService.haptic.selection();
                      },
                      onDoubleTap: _commitCell,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppTheme.spacingS),
              _ControlButton(
                label: _sending ? 'Sending' : 'Send',
                icon: Icons.send_rounded,
                onTap: () {
                  widget.socketService.tts.speakOnce('Double tap send');
                  widget.socketService.haptic.selection();
                },
                onDoubleTap: _send,
                primary: true,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DotButton extends StatelessWidget {
  const _DotButton({
    required this.dot,
    required this.label,
    required this.selected,
    required this.onTap,
    required this.onDoubleTap,
  });

  final int dot;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final VoidCallback onDoubleTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: '$label. ${selected ? "Selected" : "Not selected"}.',
      hint: 'Double tap to toggle.',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        onDoubleTap: onDoubleTap,
        child: AnimatedContainer(
          duration: Duration.zero,
          constraints: const BoxConstraints(minHeight: 120),
          decoration: BoxDecoration(
            color: selected ? Colors.white : Colors.black,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: Colors.white,
              width: selected ? 5 : 2,
            ),
          ),
          child: Center(
            child: Text(
              '$dot',
              style: AppTheme.headingLarge.copyWith(
                color: selected ? Colors.black : Colors.white,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ControlButton extends StatelessWidget {
  const _ControlButton({
    required this.label,
    required this.icon,
    required this.onTap,
    required this.onDoubleTap,
    this.primary = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final VoidCallback onDoubleTap;
  final bool primary;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '$label. Double tap to activate.',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        onDoubleTap: onDoubleTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 96),
          decoration: BoxDecoration(
            color: primary ? Colors.white : Colors.black,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.white, width: 2),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                color: primary ? Colors.black : Colors.white,
                size: 28,
              ),
              const SizedBox(width: AppTheme.spacingS),
              Flexible(
                child: Text(
                  label,
                  style: AppTheme.buttonText.copyWith(
                    color: primary ? Colors.black : Colors.white,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
