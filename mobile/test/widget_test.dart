import 'package:flutter_test/flutter_test.dart';
import 'package:koru_app/main.dart';

void main() {
  testWidgets('App renders KORU title', (WidgetTester tester) async {
    await tester.pumpWidget(const KoruApp());
    await tester.pump();
    expect(find.text('KORU'), findsOneWidget);
  });
}
