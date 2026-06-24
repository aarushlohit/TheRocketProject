import 'dart:async';

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
  final Set<int> _activePointers = <int>{};
  bool _sending = false;
  bool _fourFingerHandled = false;
  bool _twoFingerEraseHandled = false;
  int? _selectedCell;
  String? _lastSpokenTask;
  RocketExecutionResult? _lastExecutionResult;
  String? _lastTryAgainMessage;

  @override
  void initState() {
    super.initState();
    _lastExecutionResult = widget.socketService.lastExecutionResult;
    _lastTryAgainMessage = widget.socketService.lastTryAgainMessage;
    widget.socketService.addListener(_handleSocketUpdate);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.socketService.tts.speakOnce('Braille mode.');
    });
  }

  @override
  void dispose() {
    widget.socketService.removeListener(_handleSocketUpdate);
    super.dispose();
  }

  void _handleSocketUpdate() {
    final task = widget.socketService.lastTask;
    if (task != null &&
        task.source == 'braille' &&
        task.task != _lastSpokenTask) {
      _lastSpokenTask = task.task;
      widget.socketService.tts.speakResult('Intent recognized. ${task.task}');
      widget.socketService.tts.speakFeedback('Task sent');
    }

    final result = widget.socketService.lastExecutionResult;
    if (result != null && result != _lastExecutionResult) {
      _lastExecutionResult = result;
      if (mounted) setState(() => _sending = false);
    }

    final tryAgain = widget.socketService.lastTryAgainMessage;
    if (tryAgain != null && tryAgain != _lastTryAgainMessage) {
      _lastTryAgainMessage = tryAgain;
      if (mounted) setState(() => _sending = false);
    }
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

  void _focusDot(int dot) {
    final selected = _activeDots.contains(dot);
    widget.socketService.tts.speakOnce(
      '${_dotName(dot)} ${selected ? "selected" : "unselected"}.',
    );
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
      '${_dotName(dot)} ${selected ? "selected" : "unselected"}.',
    );
  }

  void _commitCell() {
    if (_activeDots.isEmpty) {
      widget.socketService.tts.speakOnce('No dots selected');
      return;
    }

    final dots = _activeDots.toList()..sort();
    final cell = '[${dots.join("-")}]';
    setState(() {
      if (_selectedCell != null && _selectedCell! < _cells.length) {
        _cells[_selectedCell!] = cell;
      } else {
        _cells.add(cell);
        _selectedCell = _cells.length - 1;
      }
      _activeDots.clear();
    });
    _vibrateCharacter(dots);
    widget.socketService.tts.speakOnce('Character completed');
  }

  void _insertSpace() {
    setState(() {
      final insertAt =
          _selectedCell == null ? _cells.length : _selectedCell! + 1;
      _cells.insert(insertAt, '[space]');
      _selectedCell = insertAt;
      _activeDots.clear();
    });
    widget.socketService.tts.speakOnce('Space inserted');
    widget.socketService.haptic.vibrate(duration: 90, amplitude: 96);
  }

  void _readCell(int index) {
    if (index < 0 || index >= _cells.length) return;
    setState(() => _selectedCell = index);
    final cell = _cells[index];
    if (cell == '[space]') {
      widget.socketService.tts.speakOnce('Space');
      return;
    }
    final dots = _parseCellDots(cell);
    widget.socketService.tts.speakOnce(
      dots.isEmpty ? 'Empty character' : dots.map(_dotName).join(', '),
    );
  }

  void _loadCellForUpdate(int index) {
    if (index < 0 || index >= _cells.length) return;
    final dots = _parseCellDots(_cells[index]);
    setState(() {
      _selectedCell = index;
      _activeDots
        ..clear()
        ..addAll(dots);
    });
    widget.socketService.tts.speakOnce('Character selected');
  }

  void _deleteCell(int index) {
    if (index < 0 || index >= _cells.length) return;
    setState(() {
      _cells.removeAt(index);
      if (_cells.isEmpty) {
        _selectedCell = null;
      } else if (index >= _cells.length) {
        _selectedCell = _cells.length - 1;
      } else {
        _selectedCell = index;
      }
      _activeDots.clear();
    });
    widget.socketService.tts.speakOnce('Character deleted');
    widget.socketService.haptic.vibrate(duration: 180, amplitude: 140);
  }

  void _moveSelection(int direction) {
    if (_cells.isEmpty) return;
    final current = _selectedCell ?? 0;
    final next = (current + direction).clamp(0, _cells.length - 1);
    setState(() => _selectedCell = next);
    _readCell(next);
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
      return;
    }

    setState(() => _sending = true);
    try {
      await widget.socketService.tts.speakOnce('Sending command');
      await widget.socketService.sendBraille(payload);
      if (!mounted) return;
      setState(() {
        _cells.clear();
        _activeDots.clear();
        _selectedCell = null;
      });
    } catch (error) {
      await widget.socketService.tts.speakError('Braille send failed: $error');
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  List<int> _parseCellDots(String cell) {
    if (!cell.startsWith('[') || !cell.endsWith(']') || cell == '[space]') {
      return <int>[];
    }
    return cell
        .substring(1, cell.length - 1)
        .split('-')
        .map(int.tryParse)
        .whereType<int>()
        .where((dot) => dot >= 1 && dot <= 8)
        .toList()
      ..sort();
  }

  void _vibrateCharacter(List<int> dots) {
    if (dots.isEmpty) return;
    final pattern = <int>[0];
    for (final dot in dots) {
      pattern
        ..add(35 + (dot * 10))
        ..add(35);
    }
    widget.socketService.haptic.customPattern({'pattern': pattern});
  }

  void _handlePointerDown(PointerDownEvent event) {
    _activePointers.add(event.pointer);
    if (_activePointers.length >= 4 && !_fourFingerHandled) {
      _fourFingerHandled = true;
      unawaited(_send());
    }
  }

  void _handlePointerMove(PointerMoveEvent event) {
    if (_activePointers.length == 2 && !_twoFingerEraseHandled) {
      _twoFingerEraseHandled = true;
      if (_selectedCell != null) {
        _deleteCell(_selectedCell!);
      } else if (_activeDots.isNotEmpty) {
        setState(_activeDots.clear);
        widget.socketService.tts.speakOnce('Character deleted');
      }
    }
  }

  void _handlePointerUp(PointerEvent event) {
    _activePointers.remove(event.pointer);
    if (_activePointers.isEmpty) {
      _fourFingerHandled = false;
      _twoFingerEraseHandled = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: const Text('Braille')),
      body: SafeArea(
        child: Listener(
          onPointerDown: _handlePointerDown,
          onPointerMove: _handlePointerMove,
          onPointerUp: _handlePointerUp,
          onPointerCancel: _handlePointerUp,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
            child: Column(
              children: [
                _CurrentCell(activeDots: _activeDots),
                const SizedBox(height: AppTheme.spacingS),
                Expanded(
                  flex: 3,
                  child: _DotSurface(
                    activeDots: _activeDots,
                    dotName: _dotName,
                    onFocus: _focusDot,
                    onToggle: _toggleDot,
                  ),
                ),
                const SizedBox(height: AppTheme.spacingS),
                Expanded(
                  flex: 2,
                  child: _CellStrip(
                    cells: _cells,
                    selectedIndex: _selectedCell,
                    parseCellDots: _parseCellDots,
                    onRead: _readCell,
                    onUpdate: _loadCellForUpdate,
                    onDelete: _deleteCell,
                    onMove: _moveSelection,
                    onEmptyDoubleTap: _commitCell,
                    onSpace: _insertSpace,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DotSurface extends StatelessWidget {
  const _DotSurface({
    required this.activeDots,
    required this.dotName,
    required this.onFocus,
    required this.onToggle,
  });

  final Set<int> activeDots;
  final String Function(int dot) dotName;
  final void Function(int dot) onFocus;
  final void Function(int dot) onToggle;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(4, (row) {
        final leftDot = row + 1;
        final rightDot = row + 5;
        return Expanded(
          child: Padding(
            padding: const EdgeInsets.only(bottom: AppTheme.spacingS),
            child: Row(
              children: [
                Expanded(
                  child: _DotZone(
                    dot: leftDot,
                    label: dotName(leftDot),
                    selected: activeDots.contains(leftDot),
                    onTap: () => onFocus(leftDot),
                    onDoubleTap: () => onToggle(leftDot),
                  ),
                ),
                const SizedBox(width: AppTheme.spacingS),
                Expanded(
                  child: _DotZone(
                    dot: rightDot,
                    label: dotName(rightDot),
                    selected: activeDots.contains(rightDot),
                    onTap: () => onFocus(rightDot),
                    onDoubleTap: () => onToggle(rightDot),
                  ),
                ),
              ],
            ),
          ),
        );
      }),
    );
  }
}

class _CellStrip extends StatelessWidget {
  const _CellStrip({
    required this.cells,
    required this.selectedIndex,
    required this.parseCellDots,
    required this.onRead,
    required this.onUpdate,
    required this.onDelete,
    required this.onMove,
    required this.onEmptyDoubleTap,
    required this.onSpace,
  });

  final List<String> cells;
  final int? selectedIndex;
  final List<int> Function(String cell) parseCellDots;
  final void Function(int index) onRead;
  final void Function(int index) onUpdate;
  final void Function(int index) onDelete;
  final void Function(int direction) onMove;
  final VoidCallback onEmptyDoubleTap;
  final VoidCallback onSpace;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Braille cells',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onDoubleTap: onEmptyDoubleTap,
        onHorizontalDragEnd: (details) {
          final velocity = details.primaryVelocity ?? 0;
          if (velocity > 0 && cells.isEmpty) {
            onSpace();
          } else if (velocity > 0) {
            onMove(1);
          } else if (velocity < 0) {
            onMove(-1);
          }
        },
        child: Container(
          width: double.infinity,
          decoration: BoxDecoration(
            color: const Color(0xFF101010),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF2C2C2C)),
          ),
          child: cells.isEmpty
              ? const SizedBox.expand()
              : SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: List.generate(cells.length, (index) {
                      return _BrailleCell(
                        cell: cells[index],
                        dots: parseCellDots(cells[index]),
                        selected: selectedIndex == index,
                        onTap: () => onRead(index),
                        onDoubleTap: () => onUpdate(index),
                        onTripleTap: () => onDelete(index),
                      );
                    }),
                  ),
                ),
        ),
      ),
    );
  }
}

class _BrailleCell extends StatefulWidget {
  const _BrailleCell({
    required this.cell,
    required this.dots,
    required this.selected,
    required this.onTap,
    required this.onDoubleTap,
    required this.onTripleTap,
  });

  final String cell;
  final List<int> dots;
  final bool selected;
  final VoidCallback onTap;
  final VoidCallback onDoubleTap;
  final VoidCallback onTripleTap;

  @override
  State<_BrailleCell> createState() => _BrailleCellState();
}

class _BrailleCellState extends State<_BrailleCell> {
  int _tapCount = 0;
  Timer? _tapTimer;

  @override
  void dispose() {
    _tapTimer?.cancel();
    super.dispose();
  }

  void _handleTap() {
    _tapCount += 1;
    _tapTimer?.cancel();
    _tapTimer = Timer(const Duration(milliseconds: 280), () {
      final count = _tapCount;
      _tapCount = 0;
      if (count >= 3) {
        widget.onTripleTap();
      } else if (count == 2) {
        widget.onDoubleTap();
      } else {
        widget.onTap();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final label = widget.cell == '[space]'
        ? 'Space ${widget.selected ? "selected" : "unselected"}.'
        : '${widget.dots.map((dot) => "dot $dot").join(", ")} ${widget.selected ? "selected" : "unselected"}.';

    return Semantics(
      label: label,
      selected: widget.selected,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: _handleTap,
        child: Container(
          width: 76,
          height: 120,
          margin: const EdgeInsets.all(8),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: widget.selected ? AppTheme.primary : const Color(0xFF171717),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: widget.selected
                  ? AppTheme.primaryLight
                  : const Color(0xFF3A3A3A),
              width: widget.selected ? 3 : 1,
            ),
          ),
          child: widget.cell == '[space]'
              ? Center(
                  child: Container(
                    width: 36,
                    height: 6,
                    color: Colors.white,
                  ),
                )
              : _MiniCell(dots: widget.dots),
        ),
      ),
    );
  }
}

class _MiniCell extends StatelessWidget {
  const _MiniCell({required this.dots});

  final List<int> dots;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: List.generate(4, (row) {
        final leftDot = row + 1;
        final rightDot = row + 5;
        return Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            _CellPreviewDot(selected: dots.contains(leftDot), compact: true),
            _CellPreviewDot(selected: dots.contains(rightDot), compact: true),
          ],
        );
      }),
    );
  }
}

class _DotZone extends StatelessWidget {
  const _DotZone({
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
      selected: selected,
      label: '$label ${selected ? "selected" : "unselected"}.',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        onDoubleTap: onDoubleTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 86),
          decoration: BoxDecoration(
            color: selected ? const Color(0xFF0F63D8) : const Color(0xFF171717),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: selected ? AppTheme.primaryLight : const Color(0xFF3A3A3A),
              width: selected ? 3 : 1,
            ),
          ),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: selected ? Colors.white : Colors.transparent,
                    border: Border.all(
                      color: selected ? Colors.white : Colors.white70,
                      width: 3,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '$dot',
                  style: AppTheme.bodySmall.copyWith(
                    color: selected ? Colors.white : Colors.white38,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CurrentCell extends StatelessWidget {
  const _CurrentCell({required this.activeDots});

  final Set<int> activeDots;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Current cell. $_semanticDots.',
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(
          horizontal: AppTheme.spacingM,
          vertical: AppTheme.spacingS,
        ),
        decoration: BoxDecoration(
          color: const Color(0xFF101010),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFF2C2C2C)),
        ),
        child: Center(
          child: SizedBox(
            width: 112,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(4, (row) {
                final leftDot = row + 1;
                final rightDot = row + 5;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _CellPreviewDot(selected: activeDots.contains(leftDot)),
                      _CellPreviewDot(selected: activeDots.contains(rightDot)),
                    ],
                  ),
                );
              }),
            ),
          ),
        ),
      ),
    );
  }

  String get _semanticDots {
    if (activeDots.isEmpty) return 'No dots selected';
    final dots = activeDots.toList()..sort();
    return dots.map((dot) => 'dot $dot selected').join(', ');
  }
}

class _CellPreviewDot extends StatelessWidget {
  const _CellPreviewDot({
    required this.selected,
    this.compact = false,
  });

  final bool selected;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final size = compact ? 12.0 : 22.0;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: selected ? AppTheme.primaryLight : Colors.transparent,
        border: Border.all(
          color: selected ? AppTheme.primaryLight : Colors.white54,
          width: compact ? 1.5 : 2,
        ),
      ),
    );
  }
}
