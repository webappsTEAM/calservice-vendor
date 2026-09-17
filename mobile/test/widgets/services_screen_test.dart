import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/profile/domain/employee_profile.dart';
import 'package:mobile/features/profile/presentation/profile_providers.dart';
import 'package:mobile/features/services/data/services_repository.dart';
import 'package:mobile/features/services/domain/service_catalog.dart';
import 'package:mobile/features/services/presentation/services_providers.dart';
import 'package:mobile/features/services/presentation/services_screen.dart';

class FakeServicesRepository implements ServicesRepository {
  List<dynamic>? lastRequestedIds;
  bool shouldThrowError = false;

  @override
  Future<List<CatalogCategory>> fetchCatalog() async {
    if (shouldThrowError) {
      throw Exception('Network Error');
    }
    return const [];
  }

  @override
  Future<List<EmployeeSkill>> fetchMySkills() async => const [];

  @override
  Future<Map<String, dynamic>> requestService({required dynamic serviceId, String name = ''}) async {
    lastRequestedIds = [serviceId];
    return {'status': 'success'};
  }

  @override
  Future<Map<String, dynamic>> bulkRequestServices(List<dynamic> serviceIds) async {
    lastRequestedIds = serviceIds;
    return {'status': 'success', 'count': serviceIds.length};
  }

  @override
  Future<Map<String, dynamic>> removeService(dynamic serviceId) async {
    return {'status': 'success'};
  }
}

void main() {
  group('ServicesScreen Widget Tests', () {
    final testProfile = EmployeeProfile(
      employeeId: 'ORG--0024',
      firstName: 'Mani',
      lastName: 'S',
      email: 'mani@gmail.com',
      isOnline: true,
      liveAvailability: 'busy',
      registrationStatus: 'approved',
      approvedServices: const [
        ApprovedService(id: 1, name: 'AC Regular Servicing & Jet Clean'),
        ApprovedService(id: 2, name: 'Switchboard Repair & Installation'),
      ],
      allRequestedServices: const [
        RequestedService(
          id: 1,
          name: 'AC Regular Servicing & Jet Clean',
          status: 'approved',
          categoryName: 'HVAC & Air Conditioning',
          requestType: 'add',
        ),
        RequestedService(
          id: 2,
          name: 'Switchboard Repair & Installation',
          status: 'approved',
          categoryName: 'Electrical & Wiring',
          requestType: 'add',
        ),
        RequestedService(
          id: 3,
          name: 'AC Gas Charging',
          status: 'pending',
          categoryName: 'HVAC & Air Conditioning',
          requestType: 'add',
        ),
        RequestedService(
          id: 4,
          name: 'Heavy Duct Installation',
          status: 'rejected',
          categoryName: 'HVAC & Air Conditioning',
          requestType: 'add',
          rejectionReason: 'Requires commercial HVAC license level 2.',
        ),
      ],
      documents: const [],
      controlledFields: const ControlledFieldsConfig(isLocked: true, lockedFields: []),
    );

    final testCatalog = [
      const CatalogCategory(
        id: 1,
        name: 'Consistency Category',
        slug: 'consistency-category',
        group: 'Consistency Category',
        services: [
          CatalogService(
            id: 10,
            name: 'Consistency Maintenance',
            slug: 'consistency-maintenance',
            durationMinutes: 60,
          ),
        ],
      ),
      const CatalogCategory(
        id: 2,
        name: 'Goods & Transport',
        slug: 'goods-transport',
        group: 'Goods & Transport',
        services: [
          CatalogService(
            id: 20,
            name: 'Cargo & Goods Van Delivery',
            slug: 'cargo-goods-delivery',
            durationMinutes: 120,
          ),
        ],
      ),
      const CatalogCategory(
        id: 3,
        name: 'AC & Appliance',
        slug: 'ac-appliance',
        group: 'AC & Appliance',
        services: [
          CatalogService(
            id: 1,
            name: 'AC Regular Servicing & Jet Clean',
            slug: 'ac-regular-servicing',
            durationMinutes: 60,
          ),
        ],
      ),
    ];

    final testSkills = [
      const EmployeeSkill(
        id: 1,
        skillId: 10,
        skillName: 'Compressor Diagnosis',
        category: 'Cooling Systems',
        proficiencyLevel: 'EXPERT',
        isVerified: true,
      ),
    ];

    testWidgets('1. Renders title, subtitle, Request New Service button, Active Trade Qualifications summary card with dynamic count', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            serviceCatalogProvider.overrideWith((ref) => Future.value(testCatalog)),
            employeeSkillsProvider.overrideWith((ref) => Future.value(testSkills)),
          ],
          child: const MaterialApp(
            home: ServicesScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify Header & Subtitle
      expect(find.text('Services & Skills'), findsWidgets);
      expect(
        find.text('Manage your authorized trade services, skills portfolio, and request new service categories'),
        findsOneWidget,
      );

      // Verify Request New Service button
      expect(find.text('Request New Service'), findsOneWidget);

      // Verify Active Trade Qualifications summary card
      expect(find.text('Active Trade Qualifications'), findsOneWidget);
      expect(
        find.text('You are currently authorized to accept customer service requests for 2 trades.'),
        findsOneWidget,
      );
      expect(find.text('Total Services'), findsOneWidget);
      expect(find.text('2'), findsWidgets);

      // Verify Authorized Service categories
      expect(find.text('HVAC & Air Conditioning'), findsWidgets);
      expect(find.text('Electrical & Wiring'), findsWidgets);

      // Verify Service card details
      expect(find.text('AC Regular Servicing & Jet Clean'), findsWidgets);
      expect(find.text('Switchboard Repair & Installation'), findsWidgets);
      expect(find.text('Approved'), findsWidgets);
      expect(find.text('✓ Eligible for Dispatch'), findsWidgets);

      // Verify Delete buttons exist for services
      expect(find.byIcon(Icons.delete_outline_rounded), findsWidgets);
    });

    testWidgets('2. Tapping Delete icon shows Remove Service? confirmation dialog', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            serviceCatalogProvider.overrideWith((ref) => Future.value(testCatalog)),
            employeeSkillsProvider.overrideWith((ref) => Future.value(testSkills)),
          ],
          child: const MaterialApp(
            home: ServicesScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Tap first delete icon
      await tester.tap(find.byIcon(Icons.delete_outline_rounded).first);
      await tester.pumpAndSettle();

      // Verify confirmation dialog
      expect(find.text('Remove Service?'), findsOneWidget);
      expect(
        find.text('Are you sure you want to remove this service from your authorized skills?'),
        findsOneWidget,
      );
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Remove'), findsOneWidget);
    });

    testWidgets('3. Tapping Request New Service opens direct category list with right checkboxes and selection logic', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final fakeRepo = FakeServicesRepository();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            servicesRepositoryProvider.overrideWithValue(fakeRepo),
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            serviceCatalogProvider.overrideWith((ref) => Future.value(testCatalog)),
            employeeSkillsProvider.overrideWith((ref) => Future.value(testSkills)),
          ],
          child: const MaterialApp(
            home: ServicesScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await tester.tap(find.text('Request New Service'));
      await tester.pumpAndSettle();

      // Verify Modal Title
      expect(find.text('Request New Services from Catalog'), findsOneWidget);
      expect(find.text('Select trade services to request operational authorization'), findsOneWidget);

      // Verify All Categories and Dynamic Category tags
      expect(find.text('All Categories'), findsOneWidget);
      expect(find.text('CONSISTENCY CATEGORY'), findsWidgets);
      expect(find.text('GOODS & TRANSPORT'), findsWidgets);

      // Verify Direct Category names
      expect(find.text('Consistency Category'), findsWidgets);
      expect(find.text('Goods & Transport'), findsWidgets);
      expect(find.text('AC & Appliance'), findsWidgets);

      // Verify Approved category status badge
      expect(find.text('✓ Already Approved'), findsWidgets);

      // Verify initial live selection counter
      expect(find.text('0 service(s) selected'), findsOneWidget);

      // Verify Submit Request button is disabled initially
      final submitButtonFinder = find.widgetWithText(ElevatedButton, 'Submit Request');
      expect(submitButtonFinder, findsOneWidget);
      final ElevatedButton submitBtn = tester.widget(submitButtonFinder);
      expect(submitBtn.onPressed, isNull);

      // Verify checkboxes are rendered directly
      expect(find.byType(Checkbox), findsWidgets);

      // Select Consistency Category
      await tester.tap(find.text('Consistency Category').last);
      await tester.pumpAndSettle();

      // Verify counter updated to 1
      expect(find.text('1 service selected'), findsOneWidget);

      // Select Goods & Transport
      await tester.tap(find.text('Goods & Transport').last);
      await tester.pumpAndSettle();

      // Verify counter updated to 2
      expect(find.text('2 services selected'), findsOneWidget);

      // Verify Submit Request button is enabled with count
      expect(find.text('Submit Request (2)'), findsOneWidget);

      // Tap Submit Request
      await tester.tap(find.text('Submit Request (2)'));
      await tester.pumpAndSettle();

      // Verify API was called with selected service IDs [10, 20]
      expect(fakeRepo.lastRequestedIds, containsAll([10, 20]));
    });

    testWidgets('4. RequestNewServicesModal displays empty catalog view when no services available', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            serviceCatalogProvider.overrideWith((ref) => Future.value(const [])),
            employeeSkillsProvider.overrideWith((ref) => Future.value(testSkills)),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: RequestNewServicesModal(),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Request New Services from Catalog'), findsOneWidget);
      expect(find.text('No services available'), findsOneWidget);
      expect(find.text('New service categories will appear here when available.'), findsOneWidget);
    });

    testWidgets('5. RequestNewServicesModal displays error view with retry on catalog load failure', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            employeeSkillsProvider.overrideWith((ref) => Future.value(testSkills)),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: RequestNewServicesModal(
                hasError: true,
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Request New Services from Catalog'), findsOneWidget);
      expect(find.text('Unable to load service catalog'), findsOneWidget);
      expect(find.text('Please check your connection and try again.'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('6. Responsive layout on 320px, 360px, 390px, 412px screen widths without overflow', (
      WidgetTester tester,
    ) async {
      final widths = [320.0, 360.0, 390.0, 412.0];

      for (final width in widths) {
        tester.view.physicalSize = Size(width * 2.0, 800 * 2.0);
        tester.view.devicePixelRatio = 2.0;

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
              serviceCatalogProvider.overrideWith((ref) => Future.value(testCatalog)),
              employeeSkillsProvider.overrideWith((ref) => Future.value(testSkills)),
            ],
            child: const MaterialApp(
              home: ServicesScreen(),
            ),
          ),
        );

        await tester.pumpAndSettle();

        expect(find.text('Services & Skills'), findsWidgets);
        expect(tester.takeException(), isNull);

        // Open modal on this width
        await tester.tap(find.text('Request New Service'));
        await tester.pumpAndSettle();

        expect(find.text('Request New Services from Catalog'), findsOneWidget);
        final err = tester.takeException();
        if (err != null) {
          if (err is FlutterError) {
            // ignore: avoid_print
            print('OVERFLOW ON WIDTH $width details:\n${err.message}\n${err.diagnostics.map((d) => d.toString()).join("\n")}');
          } else {
            // ignore: avoid_print
            print('ERROR ON WIDTH $width: $err');
          }
        }
        expect(err, isNull);

        // Close modal
        await tester.tap(find.text('Cancel'));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      }

      tester.view.resetPhysicalSize();
    });
  });
}
