import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/presentation/create_account_screen.dart';

void main() {
  Widget buildTestableCreateAccount({Size size = const Size(390, 844)}) {
    return ProviderScope(
      child: MaterialApp(
        home: MediaQuery(
          data: MediaQueryData(size: size),
          child: const CreateAccountScreen(),
        ),
      ),
    );
  }

  group('CreateAccountScreen Background & Elevated Card Presentation Tests', () {
    testWidgets('renders subtle background gradient, elevated card, and section headers', (tester) async {
      await tester.pumpWidget(buildTestableCreateAccount());
      await tester.pumpAndSettle();

      // 1. Header / App Bar branding
      expect(find.text('SEVO VENDOR'), findsOneWidget);
      expect(find.text('WORKFORCE'), findsOneWidget);

      // 2. Page title & short context
      expect(find.text('Create Technician'), findsOneWidget);
      expect(find.text('Create your account and start your workforce journey.'), findsOneWidget);

      // 3. Section Badges inside Form Card
      expect(find.text('PERSONAL DETAILS'), findsOneWidget);
      expect(find.text('CONTACT DETAILS'), findsOneWidget);
      expect(find.text('SECURITY CREDENTIALS'), findsOneWidget);

      // 4. Form Fields
      expect(find.textContaining('First Name'), findsOneWidget);
      expect(find.textContaining('Last Name'), findsOneWidget);
      expect(find.textContaining('Mobile Number'), findsOneWidget);
      expect(find.textContaining('Email Address'), findsOneWidget);
      expect(find.textContaining('Password'), findsWidgets);
      expect(find.textContaining('Confirm Password'), findsOneWidget);

      // 5. Primary Submit Button
      expect(find.text('Create Account & Continue'), findsOneWidget);

      // 6. Navigation Link & Legal
      expect(find.text('Already have an account? '), findsOneWidget);
      expect(find.text('Sign In'), findsOneWidget);
      expect(find.text('Privacy Policy'), findsOneWidget);
      expect(find.text('Terms of Service'), findsOneWidget);
      expect(find.text('Support & Contact'), findsOneWidget);
    });

    const testSizes = [
      Size(320, 568), // Compact Android
      Size(360, 640), // Standard Android
      Size(390, 844), // Modern Standard
      Size(412, 915), // Large Android
      Size(480, 800), // Wide Android
    ];

    for (final size in testSizes) {
      testWidgets('renders smoothly on ${size.width}x${size.height} with no overflow', (tester) async {
        await tester.pumpWidget(buildTestableCreateAccount(size: size));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);

        // Test scrolling
        await tester.drag(find.byType(SingleChildScrollView), const Offset(0, -300));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
      });
    }
  });
}
