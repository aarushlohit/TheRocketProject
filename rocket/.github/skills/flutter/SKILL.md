---
name: flutter
description: 'Build production Flutter apps with Clean Architecture, Riverpod, GoRouter navigation, Impeller rendering engine, Dart 3.7+ patterns, platform channels via Pigeon. Use when: create a Flutter app, set up state management, design widgets, implement navigation, build flutter, mobile app flutter, pubspec.yaml, flutter test, flutter build, riverpod, go_router.'
---

# Flutter Architect

**Widgets are functions of state. Keep them pure. Compose, don't inherit.**

Production Flutter apps with Clean Architecture, Riverpod, GoRouter, Impeller, and platform channels.

## Architecture

```
lib/
├── core/          # Shared: theme, constants, extensions, routing
├── features/
│   └── <feature>/
│       ├── domain/    # Entities, repository contracts, use cases (pure Dart)
│       ├── data/      # Repository implementations, DTOs, data sources
│       └── presentation/  # Providers, screens, widgets
└── main.dart
```

**Domain layer has zero Flutter imports** — pure Dart only. This is the key rule of Clean Architecture.

## Workflow

1. **Domain first**: Define entities, repository contracts, and use cases. Zero Flutter imports. Pure Dart with `freezed` for sealed unions.
2. **Data layer**: Implement repositories with Dio/retrofit, DTOs with `json_serializable`, and data sources. Wire up in Riverpod with `Provider<AuthRepository>`.
3. **Presentation**: Build screens and widgets with `ConsumerWidget`/`ConsumerStatefulWidget`. Wire `NotifierProvider` for each feature. Keep `ref.watch` at leaf level.
4. **Routing**: Configure GoRouter with auth redirect (`redirect` guard), nested routes per feature, and deep link patterns.

## State Management (Riverpod)

```dart
// Provider for a simple dependency
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

// Notifier for mutable state
final authNotifierProvider = NotifierProvider<AuthNotifier, AuthState>(
  AuthNotifier.new,
);

class AuthNotifier extends Notifier<AuthState> {
  @override
  AuthState build() => AuthState.unauthenticated();

  Future<void> login(String email, String password) async {
    state = AuthState.loading();
    try {
      final user = await ref.read(authRepoProvider).login(email, password);
      state = AuthState.authenticated(user);
    } catch (e) {
      state = AuthState.error(e.toString());
    }
  }
}
```

## Testing

- Unit test providers and notifiers with `ProviderContainer`.
- Widget test screens with `ProviderScope` overrides.
- Integration test user flows with `integration_test` package.
