import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/invitations/data/invitations_repository.dart';
import 'package:mobile/features/invitations/domain/technician_invitation.dart';
import 'package:mobile/features/invitations/presentation/invitations_providers.dart';
import 'package:mobile/features/invitations/presentation/technician_invitations_screen.dart';

class FakeInvitationsRepository implements InvitationsRepository {
  FakeInvitationsRepository({
    required this.response,
  });

  InvitationsResponse response;
  int? respondedInvitationId;
  String? respondedDecision;

  @override
  Future<InvitationsResponse> getInvitations({String? status}) async {
    return response;
  }

  @override
  Future<Map<String, dynamic>> respondToInvitation({
    required int invitationId,
    required String decision,
  }) async {
    respondedInvitationId = invitationId;
    respondedDecision = decision;
    return {
      'message': 'Success',
      'status': decision == 'ACCEPT' ? 'ACCEPTED' : 'REJECTED',
    };
  }
}

void main() {
  final sampleInvitationsResponse = InvitationsResponse(
    activeVendor: const ActiveVendorInfo(
      vendorId: 5,
      vendorName: 'Apex Air Conditioning Services',
      relationshipId: 10,
    ),
    pendingCount: 1,
    invitations: [
      TechnicianInvitation(
        id: 1,
        vendorId: 8,
        vendorName: 'CoolCare Express Ltd',
        vendorAddress: 'Indiranagar, Bangalore',
        status: 'PENDING',
        channel: 'DIRECT',
        message: 'Looking for experienced HVAC technicians for commercial installations.',
        matchedCriteria: const [
          MatchedCriterion(attribute: 'skill', value: 'HVAC Ducting', operator: '='),
          MatchedCriterion(attribute: 'rating', value: '4.5+', operator: '>='),
        ],
        createdAt: DateTime.parse('2026-08-28T09:00:00Z'),
        expiresAt: DateTime.parse('2026-09-10T23:59:59Z'),
      ),
      TechnicianInvitation(
        id: 2,
        vendorId: 5,
        vendorName: 'Apex Air Conditioning Services',
        vendorAddress: 'Koramangala, Bangalore',
        status: 'ACCEPTED',
        channel: 'PORTAL',
        message: 'Welcome to Apex Team!',
        matchedCriteria: const [],
        createdAt: DateTime.parse('2026-08-01T10:00:00Z'),
      ),
      TechnicianInvitation(
        id: 3,
        vendorId: 9,
        vendorName: 'CityVolt Electricals',
        vendorAddress: 'HSR Layout, Bangalore',
        status: 'DECLINED',
        channel: 'PORTAL',
        message: 'Offer for residential wiring project.',
        matchedCriteria: const [],
        createdAt: DateTime.parse('2026-07-15T10:00:00Z'),
      ),
    ],
  );

  final independentWorkerResponse = InvitationsResponse(
    activeVendor: null,
    pendingCount: 1,
    invitations: [
      TechnicianInvitation(
        id: 1,
        vendorId: 8,
        vendorName: 'CoolCare Express Ltd',
        vendorAddress: 'Indiranagar, Bangalore',
        status: 'PENDING',
        channel: 'DIRECT',
        message: 'Looking for experienced HVAC technicians.',
        matchedCriteria: const [
          MatchedCriterion(attribute: 'skill', value: 'HVAC Ducting', operator: '='),
        ],
        createdAt: DateTime.parse('2026-08-28T09:00:00Z'),
        expiresAt: DateTime.parse('2026-09-10T23:59:59Z'),
      ),
    ],
  );

  group('TechnicianInvitationsScreen Widget Tests', () {
    testWidgets('renders classic app bar, independent worker status card, and description', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            technicianInvitationsProvider.overrideWith(
              (ref) => Future.value(independentWorkerResponse),
            ),
          ],
          child: const MaterialApp(
            home: TechnicianInvitationsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // App Bar title
      expect(find.text('Vendor Invitations'), findsOneWidget);
      expect(
        find.text('Private invitations received directly from verified service businesses.'),
        findsOneWidget,
      );

      // Independent Worker Status Card
      expect(find.text('Independent Worker Status'), findsOneWidget);
      expect(
        find.textContaining('You are currently free to accept an invitation'),
        findsOneWidget,
      );
    });

    testWidgets('renders active partnered vendor card when technician has active partnership', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            technicianInvitationsProvider.overrideWith(
              (ref) => Future.value(sampleInvitationsResponse),
            ),
          ],
          child: const MaterialApp(
            home: TechnicianInvitationsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Partnered: Apex Air Conditioning Services'), findsOneWidget);
      expect(find.textContaining('You are actively partnered with this vendor.'), findsOneWidget);
    });

    testWidgets('renders status tabs with dynamic counts from real provider data', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            technicianInvitationsProvider.overrideWith(
              (ref) => Future.value(sampleInvitationsResponse),
            ),
          ],
          child: const MaterialApp(
            home: TechnicianInvitationsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Pending (1)'), findsOneWidget);
      expect(find.text('Accepted (1)'), findsOneWidget);
      expect(find.text('Declined (1)'), findsOneWidget);
      expect(find.text('All History (3)'), findsOneWidget);
    });

    testWidgets('filters invitations when switching status tabs', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            technicianInvitationsProvider.overrideWith(
              (ref) => Future.value(sampleInvitationsResponse),
            ),
          ],
          child: const MaterialApp(
            home: TechnicianInvitationsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Pending card is visible initially
      expect(find.text('CoolCare Express Ltd'), findsOneWidget);

      // Switch to Accepted tab
      await tester.tap(find.text('Accepted (1)'));
      await tester.pumpAndSettle();

      expect(find.text('CoolCare Express Ltd'), findsNothing);
      expect(find.text('🟢 ACCEPTED'), findsOneWidget);

      // Switch to Declined tab
      await tester.tap(find.text('Declined (1)'));
      await tester.pumpAndSettle();

      expect(find.text('CityVolt Electricals'), findsOneWidget);
      expect(find.text('DECLINED'), findsOneWidget);

      // Switch to All History tab
      await tester.ensureVisible(find.text('All History (3)'));
      await tester.tap(find.text('All History (3)'));
      await tester.pumpAndSettle();

      expect(find.text('CoolCare Express Ltd'), findsOneWidget);
      expect(find.text('CityVolt Electricals'), findsOneWidget);
    });

    testWidgets('renders polished empty state when no pending invitations', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            technicianInvitationsProvider.overrideWith(
              (ref) => Future.value(const InvitationsResponse(invitations: [])),
            ),
          ],
          child: const MaterialApp(
            home: TechnicianInvitationsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No pending invitations'), findsOneWidget);
      expect(
        find.text('Keep your skills and availability updated. When vendors match with your profile, your invitations will appear here.'),
        findsOneWidget,
      );
    });

    testWidgets('renders pending invitation card details: vendor name, note, matched criteria, buttons', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            technicianInvitationsProvider.overrideWith(
              (ref) => Future.value(sampleInvitationsResponse),
            ),
          ],
          child: const MaterialApp(
            home: TechnicianInvitationsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('CoolCare Express Ltd'), findsOneWidget);
      expect(find.text('Indiranagar, Bangalore'), findsOneWidget);
      expect(find.text('SKILL: HVAC Ducting'), findsOneWidget);
      expect(find.text('RATING: 4.5+'), findsOneWidget);
      expect(find.text('Looking for experienced HVAC technicians for commercial installations.'), findsOneWidget);
      expect(find.text('Accept Invitation'), findsOneWidget);
      expect(find.text('Decline'), findsOneWidget);
    });

    testWidgets('accept action opens confirmation dialog with workforce platform rules', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            technicianInvitationsProvider.overrideWith(
              (ref) => Future.value(sampleInvitationsResponse),
            ),
          ],
          child: const MaterialApp(
            home: TechnicianInvitationsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Accept Invitation
      await tester.tap(find.text('Accept Invitation'));
      await tester.pumpAndSettle();

      // Dialog is displayed
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.textContaining('Once accepted, you will join "CoolCare Express Ltd"'), findsOneWidget);
      expect(find.text('Accept & Join'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);

      // Cancel closes dialog
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsNothing);
    });

    testWidgets('decline action opens confirmation dialog', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            technicianInvitationsProvider.overrideWith(
              (ref) => Future.value(sampleInvitationsResponse),
            ),
          ],
          child: const MaterialApp(
            home: TechnicianInvitationsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Decline
      await tester.tap(find.text('Decline'));
      await tester.pumpAndSettle();

      // Dialog is displayed
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('Decline Invitation'), findsWidgets);
      expect(find.text('Are you sure you want to decline the invitation from "CoolCare Express Ltd"?'), findsOneWidget);
      expect(find.text('Keep Invitation'), findsOneWidget);

      // Cancel closes dialog
      await tester.tap(find.text('Keep Invitation'));
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsNothing);
    });

    testWidgets('confirming accept calls repository and triggers provider refresh', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final fakeRepo = FakeInvitationsRepository(response: sampleInvitationsResponse);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            invitationsRepositoryProvider.overrideWithValue(fakeRepo),
            technicianInvitationsProvider.overrideWith(
              (ref) => Future.value(sampleInvitationsResponse),
            ),
          ],
          child: const MaterialApp(
            home: TechnicianInvitationsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Accept Invitation'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Accept & Join'));
      await tester.pump();
      await tester.pumpAndSettle();

      expect(fakeRepo.respondedInvitationId, 1);
      expect(fakeRepo.respondedDecision, 'ACCEPT');
      expect(find.text('Invitation accepted! You are now partnered with CoolCare Express Ltd.'), findsOneWidget);
    });

    testWidgets('responsive layout renders smoothly across 320px, 360px, 390px, 412px widths with zero overflow', (tester) async {
      const screenWidths = [320.0, 360.0, 390.0, 412.0];

      for (final width in screenWidths) {
        tester.view.physicalSize = Size(width * 2.0, 800 * 2.0);
        tester.view.devicePixelRatio = 2.0;

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              technicianInvitationsProvider.overrideWith(
                (ref) => Future.value(sampleInvitationsResponse),
              ),
            ],
            child: const MaterialApp(
              home: TechnicianInvitationsScreen(),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('Vendor Invitations'), findsOneWidget);
        expect(find.text('Pending (1)'), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
      tester.view.resetPhysicalSize();
    });
  });
}
