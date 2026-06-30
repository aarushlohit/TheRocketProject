import 'package:flutter_test/flutter_test.dart';
import 'package:rocket_backend_app/main.dart';

void main() {
  testWidgets('Rocket backend control panel renders', (tester) async {
    await tester.pumpWidget(const RocketBackendApp());

    expect(find.text('Rocket Backend'), findsWidgets);
    expect(find.text('Start backend'), findsOneWidget);
    expect(find.text('Stop backend'), findsOneWidget);
  });
}
