import 'package:flutter_test/flutter_test.dart';
import 'package:rocket_backend_web/main.dart';

void main() {
  testWidgets('Rocket backend web dashboard renders', (tester) async {
    await tester.pumpWidget(const RocketBackendWebApp());

    expect(find.text('Rocket Backend'), findsWidgets);
    expect(find.text('Mobile Pairing'), findsOneWidget);
    expect(find.text('Runtime'), findsOneWidget);
  });
}
