# Nova Mobile

This folder contains the Stage 0 Flutter source for Nova:

- 2x2 home grid with haptic quadrant selection
- fullscreen drawing canvas
- QR pairing flow
- local pairing persistence
- auto-reconnecting WebSocket client that sends PNG bytes

## Local setup

The Flutter SDK is not installed in this workspace, so only the app source is checked in here.
On a machine with Flutter installed:

```bash
cd mobile_app
flutter create . --platforms=android,ios
flutter pub get
flutter run
```

## Required platform settings

Add these after generating host scaffolding if Flutter overwrites anything:

### Android `android/app/src/main/AndroidManifest.xml`

- Add `<uses-permission android:name="android.permission.INTERNET" />`
- Ensure camera permission is available for QR scanning:
  `<uses-permission android:name="android.permission.CAMERA" />`

### iOS `ios/Runner/Info.plist`

- Add `NSCameraUsageDescription` with a QR scanning reason
- Add `NSAppTransportSecurity` / `NSAllowsArbitraryLoads` because Stage 0 uses `ws://<ip>:8765`
