import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/core/network/auth_events.dart';
import 'package:mobile/core/storage/token_storage.dart';
import 'package:mobile/features/admin/domain/admin_monitoring.dart';
import 'package:mobile/features/admin/presentation/monitoring/admin_database_egress_screen.dart';
import 'package:mobile/features/admin/presentation/monitoring/admin_monitoring_providers.dart';
import 'package:mobile/features/admin/presentation/widgets/admin_drawer.dart';
import 'package:mobile/features/auth/data/auth_api.dart';
import 'package:mobile/features/auth/data/auth_repository.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';

AdminMonitoringData _createMockTelemetry() {
  return AdminMonitoringData(
    plainEnglishSummary: const PlainEnglishSummary(
      systemHealthStatus: 'Healthy & Optimal',
      speedHeadline: '99.88% of data requests are served instantly from RAM.',
      storageHeadline: 'Total database size is 170 MB.',
      optimizationsHeadline: '4 network guardrails are active, eliminating duplicate queries.',
      indexUtilizationHeadline: '584 of 923 search shortcuts are actively accelerating queries.',
    ),
    databaseHealth: const DatabaseHealth(
      engine: 'postgresql',
      databaseSize: '170 MB',
      statsResetTimestamp: '2026-08-01T00:00:00Z',
      databaseCacheEfficiency: CacheEfficiency(
        blocksHit: 1200000,
        blocksRead: 800,
        hitRatioPercent: 99.93,
        status: 'OPTIMAL',
        measurementType: 'ACTUAL',
      ),
      indexCacheEfficiency: CacheEfficiency(
        blocksHit: 900000,
        blocksRead: 200,
        hitRatioPercent: 99.98,
        status: 'OPTIMAL',
        measurementType: 'ACTUAL',
      ),
      billingCost: 'Not available from PostgreSQL telemetry.',
      measurementType: 'ACTUAL',
    ),
    analytics: const DatabaseAnalytics(
      totalIndexes: 923,
      usedIndexes: 584,
      unusedIndexes: 339,
      utilizationRatePercent: 63.3,
      categoryStorageBytes: {
        'Logs & Audit History': 72771584,
        'Notifications & Messaging': 20971520,
        'Core Workforce & Personnel': 15728640,
        'Jobs & Service Requests': 18874368,
        'Financial & Billing': 12582912,
        'Other System Tables': 37748736,
      },
      topUsedIndexes: [
        DatabaseIndex(
          tableName: 'workforce_servicerequest',
          indexName: 'idx_sr_status_company',
          cumulativeScans: 4520,
          indexSize: '24 kB',
        ),
      ],
    ),
    indexHealth: const IndexHealth(
      totalMonitoredIndexes: 923,
      filteredCount: 923,
      page: 1,
      pageSize: 15,
      totalPages: 62,
      allTables: ['workforce_servicerequest', 'workforce_employee'],
      indexes: [
        DatabaseIndex(
          tableName: 'workforce_servicerequest',
          indexName: 'idx_sr_status_company',
          indexSize: '24 kB',
          cumulativeScans: 4520,
          tuplesRead: 4520,
          tuplesFetched: 4520,
          indexDefinition: 'CREATE INDEX idx_sr_status_company ON workforce_servicerequest (company_id, status);',
          status: 'USED',
          note: 'Actively serving queries',
        ),
      ],
      tableStorage: [
        TableStorage(
          tableName: 'workforce_servicerequest',
          dataSize: '45 MB',
          indexSize: '12 MB',
          totalSize: '57 MB',
          totalBytes: 59768832,
        ),
      ],
    ),
    apiTrafficOptimizations: const [
      TrafficOptimization(
        endpoint: 'GET /api/workforce/jobs/ (Admin)',
        title: 'Admin Job List Optimization',
        simpleExplanation: 'Sends only essential job summary data (18 fields).',
        serializer: 'WorkforceJobListSerializer',
        status: 'IMPLEMENTED',
        measurementType: 'CODE-DERIVED',
      ),
      TrafficOptimization(
        endpoint: 'GET /api/workforce/applications/',
        title: 'Technician Applications N+1 Fix',
        simpleExplanation: 'Reads related technician info efficiently in memory.',
        status: 'IMPLEMENTED',
        measurementType: 'CODE-DERIVED',
      ),
    ],
    supabaseEgress: const SupabaseEgress(
      historicalPeriodEgress: '36.13 GB',
      postRemediationEgress: 'NOT MEASURED',
      dailyRate: 'NOT MEASURED',
      reason: 'Requires 48-hour observation window on Supabase platform dashboard.',
      measurementType: 'NOT MEASURED',
    ),
  );
}

class _FakeTokenStorage extends TokenStorage {
  @override
  Future<String?> readAccessToken() async => null;
  @override
  Future<String?> readRefreshToken() async => null;
  @override
  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {}
  @override
  Future<void> clear() async {}
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository()
      : super(
          authApi: AuthApi(Dio()),
          tokenStorage: _FakeTokenStorage(),
        );

  @override
  Future<AuthUser?> restoreSession() async => null;
}

class _MockAuthController extends AuthController {
  _MockAuthController(AuthUser user)
      : super(_FakeAuthRepository(), AuthEvents()) {
    state = AuthState.authenticated(user);
  }
}

Widget _buildTestApp({
  required AdminMonitoringData data,
  Size size = const Size(390, 844),
  List<Override> additionalOverrides = const [],
}) {
  return ProviderScope(
    overrides: [
      adminMonitoringDataProvider.overrideWith((ref) async => data),
      ...additionalOverrides,
    ],
    child: MaterialApp(
      home: MediaQuery(
        data: MediaQueryData(size: size),
        child: const SizedBox(
          width: 390,
          height: 844,
          child: AdminDatabaseEgressScreen(),
        ),
      ),
    ),
  );
}

void main() {
  group('AdminDatabaseEgressScreen Widget Tests', () {
    testWidgets('renders screen header, live status badge, and Executive Summary', (tester) async {
      final mockData = _createMockTelemetry();

      await tester.pumpWidget(_buildTestApp(data: mockData));
      await tester.pumpAndSettle();

      // Screen Header & Badge
      expect(find.text('Database & Egress Monitoring'), findsWidgets);
      expect(find.text('Live Telemetry'), findsOneWidget);
      expect(find.textContaining('Plain-English performance analytics'), findsOneWidget);

      // Mode Switcher
      expect(find.text('Plain English'), findsOneWidget);
      expect(find.text('Technical SQL'), findsOneWidget);

      // Executive Summary
      expect(find.text('Executive System Summary'), findsOneWidget);
      expect(find.text('Healthy & Optimal'), findsOneWidget);
      expect(find.text('Total System Size'), findsOneWidget);
      expect(find.text('170 MB'), findsWidgets);
      expect(find.text('Speed & Memory'), findsOneWidget);
      expect(find.text('99.93% Memory Hits'), findsOneWidget);
      expect(find.text('Search Shortcuts'), findsOneWidget);
      expect(find.text('584 / 923 Active'), findsOneWidget);
      expect(find.text('Network Guardrails'), findsOneWidget);
      expect(find.text('2 Active Guards'), findsOneWidget);
    });

    testWidgets('renders Storage Analytics category breakdown', (tester) async {
      final mockData = _createMockTelemetry();

      await tester.pumpWidget(_buildTestApp(data: mockData));
      await tester.pumpAndSettle();

      expect(find.text('Where is my Database Space Being Used?'), findsOneWidget);
      expect(find.text('Storage Analytics'), findsOneWidget);
      expect(find.text('Total Database Footprint'), findsOneWidget);

      // Categories
      expect(find.text('Audit Logs'), findsOneWidget);
      expect(find.text('Notifications'), findsOneWidget);
      expect(find.text('Workforce'), findsOneWidget);
      expect(find.text('Job Requests'), findsOneWidget);
      expect(find.text('Financials'), findsOneWidget);
      expect(find.text('System Tables'), findsOneWidget);
    });

    testWidgets('renders Search Shortcuts, allows card expansion to show SQL', (tester) async {
      final mockData = _createMockTelemetry();

      await tester.pumpWidget(_buildTestApp(data: mockData));
      await tester.pumpAndSettle();

      expect(find.text('Database Search Shortcuts'), findsOneWidget);
      expect(find.text('Index Performance & Scans'), findsOneWidget);
      expect(find.text('ACTUAL MEASUREMENT'), findsOneWidget);

      // Scroll to Index Card & tap to expand
      final mainScrollable = find.byType(Scrollable).first;
      final indexFinder = find.text('idx_sr_status_company');
      await tester.scrollUntilVisible(indexFinder, 200, scrollable: mainScrollable);
      await tester.pumpAndSettle();

      expect(indexFinder, findsOneWidget);
      expect(find.text('4520 scans'), findsOneWidget);

      await tester.tap(indexFinder);
      await tester.pumpAndSettle();

      // Expanded content
      expect(find.text('Size on Disk'), findsOneWidget);
      expect(find.text('Examined'), findsOneWidget);
      expect(find.text('Delivered'), findsOneWidget);
      
      final viewSqlFinder = find.text('View SQL Definition');
      await tester.scrollUntilVisible(viewSqlFinder, 200, scrollable: mainScrollable);
      await tester.pumpAndSettle();
      expect(viewSqlFinder, findsOneWidget);

      // Tap View SQL
      await tester.tap(viewSqlFinder);
      await tester.pumpAndSettle();

      expect(find.textContaining('CREATE INDEX idx_sr_status_company'), findsOneWidget);
    });

    testWidgets('renders Network Guardrails and Supabase Platform Egress', (tester) async {
      final mockData = _createMockTelemetry();

      await tester.pumpWidget(_buildTestApp(data: mockData));
      await tester.pumpAndSettle();

      final mainScrollable = find.byType(Scrollable).first;

      // Scroll to Guardrails
      final guardrailsFinder = find.text('Network Guardrails & Optimizations');
      await tester.scrollUntilVisible(guardrailsFinder, 200, scrollable: mainScrollable);
      await tester.pumpAndSettle();

      expect(guardrailsFinder, findsOneWidget);
      expect(find.text('What was fixed?'), findsOneWidget);
      expect(find.text('Admin Job List Optimization'), findsOneWidget);
      expect(find.text('Technician Applications N+1 Fix'), findsOneWidget);

      // Scroll to Supabase Platform Egress
      final egressFinder = find.text('Supabase Platform Egress');
      await tester.scrollUntilVisible(egressFinder, 200, scrollable: mainScrollable);
      await tester.pumpAndSettle();

      expect(egressFinder, findsOneWidget);
      expect(find.text('Network Bandwidth Usage'), findsOneWidget);
      expect(find.text('Historical Pre-Remediation Total'), findsOneWidget);
      expect(find.text('36.13 GB'), findsOneWidget);
      expect(find.text('Post-Remediation Rate'), findsOneWidget);
      expect(find.text('NOT MEASURED'), findsWidgets);
      expect(find.text('How Egress Works'), findsOneWidget);
    });

    testWidgets('toggles to Technical SQL Mode and displays technical engine telemetry', (tester) async {
      final mockData = _createMockTelemetry();

      await tester.pumpWidget(_buildTestApp(data: mockData));
      await tester.pumpAndSettle();

      // Tap Technical SQL
      await tester.tap(find.text('Technical SQL'));
      await tester.pumpAndSettle();

      expect(find.text('Technical Engine & Buffer Telemetry'), findsOneWidget);
      expect(find.textContaining('pg_stat_database'), findsWidgets);
      expect(find.text('Database Cache Efficiency (pg_stat_database)'), findsOneWidget);
      expect(find.text('Index Buffer Cache Hit Ratio (pg_statio_user_indexes)'), findsOneWidget);
      expect(find.text('POSTGRESQL'), findsOneWidget);
    });

    testWidgets('renders error state when telemetry is unavailable', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            adminMonitoringDataProvider.overrideWith((ref) async {
              throw Exception('Network connection refused');
            }),
          ],
          child: const MaterialApp(
            home: AdminDatabaseEgressScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Monitoring data unavailable'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('renders cleanly on narrow 320px screen width without overflow', (tester) async {
      tester.view.physicalSize = const Size(320, 700);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final mockData = _createMockTelemetry();

      await tester.pumpWidget(_buildTestApp(data: mockData, size: const Size(320, 700)));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.text('Database & Egress Monitoring'), findsWidgets);
    });

    testWidgets('AdminDrawer contains MONITORING group with Database & Egress navigation item', (tester) async {
      const adminUser = AuthUser(
        id: 1,
        username: 'admin',
        email: 'admin@cal.com',
        firstName: 'Ops',
        lastName: 'Admin',
        role: 'admin',
        companyId: 1,
        companyName: 'Cal Service',
        isSuperuser: true,
        employeeId: null,
        registrationStatus: 'approved',
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(
              (ref) => _MockAuthController(adminUser),
            ),
          ],
          child: const MaterialApp(
            home: Scaffold(drawer: AdminDrawer()),
          ),
        ),
      );

      // Open drawer
      final scaffoldState = tester.state<ScaffoldState>(find.byType(Scaffold));
      scaffoldState.openDrawer();
      await tester.pumpAndSettle();

      final monitoringFinder = find.text('MONITORING');
      await tester.scrollUntilVisible(monitoringFinder, 200, scrollable: find.byType(Scrollable).last);
      await tester.pumpAndSettle();

      expect(monitoringFinder, findsOneWidget);
      expect(find.text('Database & Egress'), findsOneWidget);
    });
  });
}
