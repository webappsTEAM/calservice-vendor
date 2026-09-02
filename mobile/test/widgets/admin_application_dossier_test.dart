import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/admin_application.dart';
import 'package:mobile/features/admin/presentation/admin_dashboard_providers.dart';
import 'package:mobile/features/admin/presentation/applications/admin_application_detail_screen.dart';

final mockDossierApplication = AdminApplication.fromJson({
  'id': 7688,
  'employee_id': 'ORG--7688',
  'name': 'Zayn Kishan',
  'first_name': 'Zayn',
  'last_name': 'Kishan',
  'email': 'zaynkishan@gmail.com',
  'phone': '987654355',
  'mobile_number': '987654355',
  'registration_status': 'submitted',
  'is_online': false,
  'date_of_birth': '1996-08-15',
  'all_requested_services': [
    {
      'id': 201,
      'name': 'AC Installation & Uninstallation',
      'category_name': 'HVAC',
      'status': 'pending',
    },
    {
      'id': 202,
      'name': 'AC Filter Cleaning & Deep Clean',
      'category_name': 'HVAC',
      'status': 'pending',
    },
    {
      'id': 203,
      'name': 'Refrigerator Gas Refill',
      'category_name': 'Appliance',
      'status': 'approved',
    },
  ],
  'documents_status': {
    'aadhaar': {
      'category': 'aadhaar',
      'title': 'Aadhaar Card',
      'status': 'pending',
      'file_url': 'https://example.com/docs/aadhaar.pdf',
      'document_number': 'XXXX-XXXX-1234',
    },
    'trade_certificate': {
      'category': 'trade_certificate',
      'title': 'HVAC Trade Certificate',
      'status': 'approved',
      'file_url': 'https://example.com/docs/cert.pdf',
      'document_number': 'CERT-9988',
    },
  },
  'onboarding_data': {
    'status': 'submitted',
    'draft': {
      'personal': {
        'dob': '1996-08-15',
        'gender': 'male',
        'emergencyName': 'Aarav Kishan',
        'emergencyPhone': '987654300',
      },
      'address': {
        'street': '123 Tech Park Road',
        'city': 'Hosur',
        'state': 'Tamil Nadu',
        'pincode': '635109',
        'serviceRadius': 10,
      },
      'skills': {
        'experienceYears': 4,
        'vehicleType': 'two_wheeler',
        'licenseNumber': 'DL-TN-2018-0099',
      },
      'bank': {
        'accountHolder': 'Zayn Kishan',
        'accountNumber': '987654321012',
        'ifsc': 'SBIN0001234',
        'upiId': 'zayn@upi',
      },
    },
  },
});

void main() {
  setUp(() {
    AppColors.configure(brightness: Brightness.light, highContrast: false);
  });

  Widget buildTestableWidget(Widget child, {List<Override> overrides = const []}) {
    return ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        home: child,
      ),
    );
  }

  group('Admin Review Full Dossier Screen Tests', () {
    testWidgets('Renders all 7 dossier tabs and candidate header', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        buildTestableWidget(
          const AdminApplicationDetailScreen(applicationId: 7688),
          overrides: [
            adminApplicationDetailProvider(7688).overrideWith((ref) => Future.value(mockDossierApplication)),
          ],
        ),
      );
      await tester.pumpAndSettle();

      // Verify Header details
      expect(find.text('Dossier #7688'), findsOneWidget);
      expect(find.text('Zayn Kishan'), findsOneWidget);
      expect(find.textContaining('ID: ORG--7688'), findsOneWidget);
      expect(find.textContaining('zaynkishan@gmail.com'), findsNWidgets(2)); // Header + Overview card
      expect(find.text('SUBMITTED'), findsOneWidget);

      // Verify Tabs exist
      expect(find.text('Overview'), findsOneWidget);
      expect(find.text('Registration'), findsOneWidget);
      expect(find.text('Services'), findsOneWidget);
      expect(find.text('Documents'), findsOneWidget);
      expect(find.text('Experience & Skills'), findsOneWidget);
      expect(find.text('Bank Details'), findsOneWidget);
      expect(find.text('Audit History'), findsOneWidget);

      // Verify Overview Tab contents
      expect(find.text('CANDIDATE DETAILS'), findsOneWidget);
      expect(find.text('SERVICES SUMMARY'), findsOneWidget);
      expect(find.text('DOCUMENTS LODGED'), findsOneWidget);
      expect(find.text('Hosur'), findsOneWidget);
      expect(find.text('10 km'), findsOneWidget);
      expect(find.text('3 services'), findsOneWidget);
      expect(find.text('2 files'), findsOneWidget);

      // Verify Bottom Actions
      expect(find.text('Correction'), findsOneWidget);
      expect(find.text('Reject'), findsOneWidget);
      expect(find.text('Approve Technician'), findsOneWidget);
    });

    testWidgets('Switches to Registration tab and renders personal & address details', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        buildTestableWidget(
          const AdminApplicationDetailScreen(applicationId: 7688),
          overrides: [
            adminApplicationDetailProvider(7688).overrideWith((ref) => Future.value(mockDossierApplication)),
          ],
        ),
      );
      await tester.pumpAndSettle();

      // Tap Registration Tab
      await tester.tap(find.text('Registration'));
      await tester.pumpAndSettle();

      expect(find.text('PERSONAL INFORMATION'), findsOneWidget);
      expect(find.text('1996-08-15'), findsOneWidget);
      expect(find.text('Aarav Kishan'), findsOneWidget);
      expect(find.text('987654300'), findsOneWidget);

      expect(find.text('ADDRESS & DISPATCH TERRITORY'), findsOneWidget);
      expect(find.text('123 Tech Park Road'), findsOneWidget);
      expect(find.text('Hosur, Tamil Nadu'), findsOneWidget);
      expect(find.text('635109'), findsOneWidget);
    });

    testWidgets('Switches to Services tab and renders authorization matrix', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        buildTestableWidget(
          const AdminApplicationDetailScreen(applicationId: 7688),
          overrides: [
            adminApplicationDetailProvider(7688).overrideWith((ref) => Future.value(mockDossierApplication)),
          ],
        ),
      );
      await tester.pumpAndSettle();

      // Tap Services Tab
      await tester.tap(find.text('Services'));
      await tester.pumpAndSettle();

      expect(find.text('PER-SERVICE AUTHORIZATION MATRIX'), findsOneWidget);
      expect(find.text('AC Installation & Uninstallation'), findsOneWidget);
      expect(find.text('AC Filter Cleaning & Deep Clean'), findsOneWidget);
      expect(find.text('Refrigerator Gas Refill'), findsOneWidget);
      expect(find.text('Approve All Pending (2)'), findsOneWidget);
      expect(find.text('Approved ✓'), findsOneWidget);
    });

    testWidgets('Switches to Documents tab and renders files & verification controls', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        buildTestableWidget(
          const AdminApplicationDetailScreen(applicationId: 7688),
          overrides: [
            adminApplicationDetailProvider(7688).overrideWith((ref) => Future.value(mockDossierApplication)),
          ],
        ),
      );
      await tester.pumpAndSettle();

      // Tap Documents Tab
      await tester.tap(find.text('Documents'));
      await tester.pumpAndSettle();

      expect(find.text('UPLOADED IDENTIFICATION & COMPLIANCE FILES'), findsOneWidget);
      expect(find.text('Aadhaar Card'), findsOneWidget);
      expect(find.text('HVAC Trade Certificate'), findsOneWidget);
      expect(find.text('View File'), findsNWidgets(2));
      expect(find.text('Verify'), findsOneWidget);
      expect(find.text('Verified ✓'), findsOneWidget);
    });

    testWidgets('Switches to Bank Details tab and renders masked account credentials', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        buildTestableWidget(
          const AdminApplicationDetailScreen(applicationId: 7688),
          overrides: [
            adminApplicationDetailProvider(7688).overrideWith((ref) => Future.value(mockDossierApplication)),
          ],
        ),
      );
      await tester.pumpAndSettle();

      // Scroll to and tap Bank Details Tab
      await tester.ensureVisible(find.text('Bank Details'));
      await tester.tap(find.text('Bank Details'));
      await tester.pumpAndSettle();

      expect(find.text('DIRECT DEPOSIT & PAYOUT CREDENTIALS'), findsOneWidget);
      expect(find.text('Zayn Kishan'), findsNWidgets(2)); // Header + Bank Account Holder
      expect(find.text('••••1012'), findsOneWidget);
      expect(find.text('SBIN0001234'), findsOneWidget);
      expect(find.text('zayn@upi'), findsOneWidget);
    });

    testWidgets('Approve button opens confirmation dialog with compliance warnings', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        buildTestableWidget(
          const AdminApplicationDetailScreen(applicationId: 7688),
          overrides: [
            adminApplicationDetailProvider(7688).overrideWith((ref) => Future.value(mockDossierApplication)),
          ],
        ),
      );
      await tester.pumpAndSettle();

      // Tap Approve Technician
      await tester.tap(find.text('Approve Technician'));
      await tester.pumpAndSettle();

      // Dialog opens showing notice that Aadhaar Card is unapproved
      expect(find.text('Approval Notice'), findsOneWidget);
      expect(find.textContaining('Unapproved Documents'), findsOneWidget);
      expect(find.textContaining('Aadhaar Card'), findsOneWidget);
      expect(find.text('Review Items First'), findsOneWidget);
      expect(find.text('Proceed'), findsOneWidget);
    });
  });
}
