import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';

void main() {
  runApp(const RocketBackendApp());
}

class RocketBackendApp extends StatelessWidget {
  const RocketBackendApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Rocket Backend',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0F63D8),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFF070A0F),
      ),
      home: const BackendHome(),
    );
  }
}

class BackendHome extends StatefulWidget {
  const BackendHome({super.key});

  @override
  State<BackendHome> createState() => _BackendHomeState();
}

class _BackendHomeState extends State<BackendHome> {
  static const int _port = 8765;

  Process? _process;
  String _status = 'Stopped';
  final String _connection = 'ws://0.0.0.0:8765';
  final List<String> _logs = <String>[];
  bool _starting = false;

  bool get _running => _process != null;

  @override
  void initState() {
    super.initState();
    unawaited(_startBackend());
  }

  @override
  void dispose() {
    _stopBackend();
    super.dispose();
  }

  Future<void> _startBackend() async {
    if (_running || _starting) return;
    setState(() {
      _starting = true;
      _status = 'Starting';
      _logs.clear();
    });

    final exe = _backendExecutable();
    if (!await exe.exists()) {
      _appendLog('Bundled backend executable missing: ${exe.path}');
      setState(() {
        _status = 'Install incomplete';
        _starting = false;
      });
      return;
    }

    final appDir = exe.parent;
    final opencodeCommand = _opencodeCommand(appDir);
    final env = Map<String, String>.from(Platform.environment)
      ..['ROCKET_APP_BUNDLE_DIR'] = appDir.path
      ..['ROCKET_DATA_DIR'] = _dataDir().path
      ..['ROCKET_POWERS_SOURCE_DIR'] = _powersDir(appDir).path
      ..['PYTHONUTF8'] = '1';
    if (opencodeCommand.existsSync()) {
      env['ROCKET_OPENCODE_COMMAND'] = opencodeCommand.path;
    }

    try {
      final process = await Process.start(
        exe.path,
        <String>['--host', '0.0.0.0', '--port', '$_port'],
        workingDirectory: appDir.path,
        environment: env,
        runInShell: false,
      );
      _process = process;
      _listen(process.stdout, isError: false);
      _listen(process.stderr, isError: true);
      unawaited(
        process.exitCode.then((code) {
          if (!mounted) return;
          setState(() {
            _process = null;
            _status = 'Stopped with code $code';
          });
        }),
      );
      setState(() {
        _status = 'Running';
        _starting = false;
      });
      _appendLog('Rocket Backend running on $_connection');
    } catch (error) {
      _appendLog('Failed to start backend: $error');
      setState(() {
        _status = 'Failed';
        _starting = false;
      });
    }
  }

  void _stopBackend() {
    final process = _process;
    if (process == null) return;
    process.kill(ProcessSignal.sigterm);
    _process = null;
    if (mounted) {
      setState(() => _status = 'Stopped');
    }
  }

  void _listen(Stream<List<int>> stream, {required bool isError}) {
    stream
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) => _appendLog(isError ? 'ERR $line' : line));
  }

  void _appendLog(String line) {
    if (!mounted) return;
    setState(() {
      _logs.add(line);
      if (_logs.length > 300) {
        _logs.removeRange(0, _logs.length - 300);
      }
    });
  }

  File _backendExecutable() {
    final exeDir = File(Platform.resolvedExecutable).parent;
    final candidates = <File>[
      File('${exeDir.path}\\data\\backend\\RocketBackend.exe'),
      File('${Directory.current.path}\\data\\backend\\RocketBackend.exe'),
      File('${Directory.current.path}\\RocketBackend.exe'),
    ];
    return candidates.firstWhere(
      (file) => file.existsSync(),
      orElse: () => candidates.first,
    );
  }

  Directory _powersDir(Directory appDir) {
    return Directory('${appDir.path}\\data\\opencode-powers');
  }

  Directory _dataDir() {
    final localAppData = Platform.environment['LOCALAPPDATA'];
    if (localAppData == null || localAppData.trim().isEmpty) {
      return Directory('${Directory.current.path}\\RocketBackendData');
    }
    return Directory('$localAppData\\RocketBackend\\data');
  }

  File _opencodeCommand(Directory appDir) {
    return File('${appDir.path}\\data\\tools\\opencode\\opencode.cmd');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.rocket_launch_rounded, size: 44),
                  const SizedBox(width: 16),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Rocket Backend',
                          style: TextStyle(
                            fontSize: 30,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        Text(
                          'Bundled desktop runtime for Rocket mobile pairing',
                        ),
                      ],
                    ),
                  ),
                  _StatusPill(status: _status, running: _running),
                ],
              ),
              const SizedBox(height: 24),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  FilledButton.icon(
                    onPressed: _running || _starting ? null : _startBackend,
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: const Text('Start backend'),
                  ),
                  OutlinedButton.icon(
                    onPressed: _running ? _stopBackend : null,
                    icon: const Icon(Icons.stop_rounded),
                    label: const Text('Stop backend'),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              _ConnectionCard(connection: _connection),
              const SizedBox(height: 20),
              const Text(
                'Runtime Logs',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0D1118),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF263241)),
                  ),
                  child: SingleChildScrollView(
                    reverse: true,
                    child: SelectableText(
                      _logs.isEmpty
                          ? 'Waiting for backend logs...'
                          : _logs.join('\n'),
                      style: const TextStyle(
                        fontFamily: 'Consolas',
                        fontSize: 13,
                      ),
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

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status, required this.running});

  final String status;
  final bool running;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: running ? const Color(0xFF123D24) : const Color(0xFF3A1F22),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: running ? const Color(0xFF3FE07A) : const Color(0xFFFF7676),
        ),
      ),
      child: Text(status, style: const TextStyle(fontWeight: FontWeight.w700)),
    );
  }
}

class _ConnectionCard extends StatelessWidget {
  const _ConnectionCard({required this.connection});

  final String connection;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF10284B), Color(0xFF0D1A24)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF315A8E)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Pairing',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text('Backend listens on $connection'),
          const SizedBox(height: 8),
          const Text(
            'Open Rocket mobile, scan the QR shown in logs/terminal output, or use settings pairing.',
          ),
        ],
      ),
    );
  }
}
