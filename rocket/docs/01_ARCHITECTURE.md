# Rocket V3 Architecture

```text
Flutter App
  -> Input Capture
      -> Voice
      -> Drawing
      -> Braille
  -> Websocket
  -> RocketTerminal
  -> Nemotron Omni
  -> RocketParser Prompt
  -> Executable Task
  -> Display in RocketTerminal
  -> OpenWork in Phase 2
```

Frozen Phase 1 boundary:

- No automation.
- No execution.
- No deterministic planner.
- No verifier.
- No task DAG.
- No OS control.
- No browser control.
- No memory.

Vendored Phase 2 dependency:

- `external/openwork`
- Stored only.
- Not patched, built, started, or integrated in Phase 1.
