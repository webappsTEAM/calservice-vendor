import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/documents/presentation/documents_screen.dart';
import 'package:mobile/features/profile/domain/employee_profile.dart';
import 'package:mobile/features/profile/presentation/profile_providers.dart';

void main() {
  group('DocumentsScreen Widget Tests', () {
    final populatedProfile = EmployeeProfile(
      employeeId: 'ORG--0024',
      firstName: 'Mani',
      lastName: 'S',
      email: 'mani@gmail.com',
      isOnline: true,
      registrationStatus: 'approved',
      approvedServices: const [],
      allRequestedServices: const [],
      documents: [
        const EmployeeDocument(
          category: 'identity_proof',
          title: 'Government Identity Proof',
          documentNumber: 'ID-12345',
          fileUrl: 'https://example.com/id.jpg',
          status: 'approved',
        ),
        const EmployeeDocument(
          category: 'driving_license',
          title: 'Driving License / Vehicle RC',
          documentNumber: 'DL-67890',
          fileUrl: 'https://example.com/dl.jpg',
          status: 'rejected',
          rejectionReason: 'Image is expired or unreadable.',
        ),
        const EmployeeDocument(
          category: 'technical_qualification',
          title: 'Trade & Technical Qualification',
          fileUrl: 'https://example.com/cert.pdf',
          status: 'pending',
        ),
      ],
      controlledFields: const ControlledFieldsConfig(isLocked: true, lockedFields: []),
    );

    final emptyProfile = EmployeeProfile(
      employeeId: 'ORG--0024',
      firstName: 'Mani',
      lastName: 'S',
      isOnline: false,
      registrationStatus: 'under_review',
      approvedServices: const [],
      allRequestedServices: const [],
      documents: const [],
      controlledFields: const ControlledFieldsConfig(isLocked: false, lockedFields: []),
    );

    testWidgets('renders Documents & Identity title, subtitle, Credential Status card, and 5 categories', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(populatedProfile)),
          ],
          child: const MaterialApp(
            home: DocumentsScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify Header and Subtitle
      expect(find.text('Documents & Identity'), findsWidgets);
      expect(
        find.text('Manage your identity credentials, trade certifications, and compliance verification files'),
        findsOneWidget,
      );

      // Verify Credential Status Card & Account Status
      expect(find.text('Credential Status'), findsOneWidget);
      expect(
        find.text('All documents are securely archived and audited against platform compliance requirements.'),
        findsOneWidget,
      );
      // Verify Categories
      expect(find.text('Government Identity Proof (Aadhaar / ID)'), findsOneWidget);
      expect(find.text('Driving License / Vehicle RC'), findsOneWidget);
      expect(find.text('Trade & Technical Qualification'), findsOneWidget);
      expect(find.text('Police Verification / Background Check'), findsOneWidget);

      // Scroll to reveal remaining items
      await tester.drag(find.byType(ListView).first, const Offset(0, -500));
      await tester.pumpAndSettle();

      expect(find.text('Bank Passbook / Cancelled Cheque'), findsOneWidget);

      // Verify Mandatory / Optional badges
      expect(find.text('Mandatory'), findsWidgets);
      expect(find.text('Optional'), findsWidgets);

      // Verify Actions
      expect(find.text('View Uploaded Document'), findsWidgets);
      expect(find.text('Replace Document'), findsWidgets);
      expect(find.text('Upload File'), findsWidgets);

      // Verify Rejection reason
      expect(find.text('Rejection Reason: Image is expired or unreadable.'), findsOneWidget);
    });

    testWidgets('renders pending account status when profile registrationStatus is under_review', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(emptyProfile)),
          ],
          child: const MaterialApp(
            home: DocumentsScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Account Status: Under Review'), findsOneWidget);
      expect(find.text('Upload File'), findsNWidgets(5));
    });

    testWidgets('renders responsive layout cleanly on 320px width without overflow', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(320 * 2.0, 640 * 2.0);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(populatedProfile)),
          ],
          child: const MaterialApp(
            home: DocumentsScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Documents & Identity'), findsWidgets);
      expect(tester.takeException(), isNull);

      await tester.drag(find.byType(ListView).first, const Offset(0, -600));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  });
}
