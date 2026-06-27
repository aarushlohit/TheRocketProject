---
description: 'Use when writing Flutter/Dart code, editing .dart files, or building Flutter widgets. Covers Clean Architecture, Riverpod, GoRouter, Freezed patterns.'
applyTo: "**/*.dart"
---

# Flutter/Dart Conventions

## Architecture
- **Clean Architecture**: `domain/` layer has ZERO Flutter imports — pure Dart only.
- Structure: `lib/core/`, `lib/features/<name>/domain/`, `lib/features/<name>/data/`, `lib/features/<name>/presentation/`.

## State Management (Riverpod)
- Use `NotifierProvider` / `AsyncNotifierProvider` for state.
- Use `Provider` / `FutureProvider` for dependencies and computed values.
- Keep `ref.watch` at the leaf widget level — avoid rebuilding entire screen trees.
- Test providers with `ProviderContainer`.

## Navigation (GoRouter)
- Define routes in a centralized `router.dart` or `app_router.dart`.
- Use `redirect` guards for auth protection.
- Support deep linking with path parameters.

## Data Classes (Freezed)
- Use `freezed` for data classes, sealed unions, and DTOs.
- Use `json_serializable` with `json_annotation` for JSON serialization.

## Style
- Use `const` constructors wherever possible.
- Prefer `ConsumerWidget` / `ConsumerStatefulWidget` over manually managing `ref`.
- Extract reusable widgets into separate files.
