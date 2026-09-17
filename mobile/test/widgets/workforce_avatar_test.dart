import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/shared/widgets/workforce_avatar.dart';

void main() {
  group('WorkforceAvatar Widget Tests', () {
    testWidgets('renders fallback initial when imageUrl is null', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WorkforceAvatar(
              imageUrl: null,
              name: 'John Doe',
            ),
          ),
        ),
      );

      expect(find.text('J'), findsOneWidget);
    });

    testWidgets('renders custom initial if provided explicitly', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WorkforceAvatar(
              imageUrl: null,
              name: 'John Doe',
              initial: 'Z',
            ),
          ),
        ),
      );

      expect(find.text('Z'), findsOneWidget);
    });

    testWidgets('renders default initial "T" when name and initial are empty', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WorkforceAvatar(
              imageUrl: null,
            ),
          ),
        ),
      );

      expect(find.text('T'), findsOneWidget);
    });

    testWidgets('renders presence indicator when showPresence is true', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WorkforceAvatar(
              imageUrl: null,
              name: 'Alice Smith',
              showPresence: true,
              isOnline: true,
            ),
          ),
        ),
      );

      expect(find.descendant(of: find.byType(WorkforceAvatar), matching: find.byType(Stack)), findsOneWidget);
      expect(find.text('A'), findsOneWidget);
    });

    testWidgets('triggers onTap callback when tapped', (WidgetTester tester) async {
      bool tapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: WorkforceAvatar(
              imageUrl: null,
              name: 'Bob Builder',
              onTap: () {
                tapped = true;
              },
            ),
          ),
        ),
      );

      await tester.tap(find.byType(WorkforceAvatar));
      await tester.pumpAndSettle();

      expect(tapped, isTrue);
    });
  });
}
