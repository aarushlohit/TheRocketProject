# Rocket Project — Copilot Instructions

## Code Style & Quality Standards

- **Write production-grade code**: readable, correct, maintainable, secure, and failure-aware. Prioritize clarity over cleverness.
- **Naming**: use descriptive names that eliminate the need for comments. Good names make refactoring safe and prevent misunderstandings.
- **Keep functions small**: each function should do one thing well. If it does more than one thing, split it.
- **Fail gracefully**: validate inputs, handle edge cases, and never trust external data. Every function should have a defined error state.
- **No commented-out code**: delete it. Git history exists for a reason.
- **No debug artifacts**: remove `print()`, `console.log()`, `debugger`, and temporary files before committing.
- **Avoid magic numbers/strings**: extract to named constants.

## Architecture Principles

- **Separation of concerns**: keep UI, business logic, and data access in distinct layers.
- **Clean Architecture** (see `ARCHITECTURE.md`): domain layer has zero framework imports. Pure Dart/Python with no Flutter/framework dependencies in domain entities.
- **Compose, don't inherit**: prefer composition over inheritance. Favor interfaces/abstract classes.
- **Dependency injection**: wire dependencies explicitly. Avoid global state and singletons.
- **Project-specific**: see `docs/01_ARCHITECTURE.md` for the detailed architecture documentation.

## Build & Test

- **Python backend**: virtual env at `.venv/`. Run `python -m agent.main` to start.
- **Flutter apps**: located in `backend_app/`, `backend_web_app/`, `mobile_app/`. Use `flutter build` / `flutter test`.
- **Testing Trophy approach**: 80% integration tests, 10% unit tests, 10% E2E. Test behavior, not implementation.
- **Always run tests** after making changes: `pytest` for Python, `flutter test` for Flutter.
- **Git**: use conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).

## Project Conventions

- **Python**: Type hints on all functions. Use `pathlib` over `os.path`. Favor dataclasses over dicts.
- **Flutter/Dart**: Riverpod for state management, GoRouter for navigation, Freezed for data classes.
- **MCP Servers**: defined in `opencode.json` under `mcp` section. Key ones: filesystem, playwright, memory, google-workspace.
- **Documentation**: key docs in `docs/` folder. See `docs/00_VISION.md` for project vision, `RUNBOOK.md` for operations.

## What NOT to Do

- Don't add dependencies without evaluating alternatives first.
- Don't use `Any` or `dynamic` types unless absolutely unavoidable.
- Don't leave TODO comments without an owner or issue reference.
- Don't break existing tests — if a test fails, understand why before changing it.
- Don't commit secrets, API keys, or credentials.
