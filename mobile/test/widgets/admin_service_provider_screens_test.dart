import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/provider_profile.dart';
import 'package:mobile/features/admin/domain/tied_technician.dart';
import 'package:mobile/features/admin/domain/vendor_invitation.dart';
import 'package:mobile/features/admin/presentation/admin_dashboard_providers.dart';
import 'package:mobile/features/admin/presentation/invitations/admin_vendor_invitations_screen.dart';
import 'package:mobile/features/admin/presentation/network/admin_tied_technicians_screen.dart';
import 'package:mobile/features/admin/presentation/profile/admin_provider_profile_screen.dart';
import 'package:mobile/features/admin/presentation/settings/admin_settings_screen.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';

class FakeAuthController extends StateNotifier<AuthState>
    implements AuthController {
  FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  const mockVendorAdmin = AuthUser(
    id: 10,
    username: 'vendor_admin',
    email: 'admin@coolcare.com',
    firstName: 'Vendor',
    lastName: 'Manager',
    role: 'admin',
    companyId: 5,
    companyName: 'CoolCare Services Ltd',
    isSuperuser: false,
    isPlatformAdmin: false,
    isVendorAdmin: true,
    employeeId: null,
    registrationStatus: 'approved',
  );

  const mockTechnicians = [
    TiedTechnician(
      relationshipId: 1,
      technicianId: 101,
      userId: 201,
      name: 'Ravi Kumar',
      email: 'ravi@coolcare.com',
      phone: '+91 9876543210',
      title: 'Senior HVAC Tech',
      state: 'ACTIVE',
      status: 'ACTIVE',
      scopeSkills: ['HVAC Repair', 'Jet Pump Cleaning'],
      engagementType: 'DIRECT',
      paymentModel: 'REVENUE_SHARE',
      averageRating: 4.85,
      ratingCount: 42,
      tier: 'GOLD',
      isOnline: true,
      currentAvailability: 'AVAILABLE',
    ),
    TiedTechnician(
      relationshipId: 2,
      technicianId: 102,
      userId: 202,
      name: 'Anand Singh',
      email: 'anand@coolcare.com',
      phone: '+91 9876543211',
      title: 'Appliance Repair Lead',
      state: 'SUSPENDED',
      status: 'SUSPENDED',
      scopeSkills: ['Appliance Repair'],
      engagementType: 'CONTRACT',
      paymentModel: 'FIXED_PER_JOB',
      averageRating: 4.20,
      ratingCount: 15,
      tier: 'SILVER',
      isOnline: false,
      currentAvailability: 'OFFLINE',
    ),
  ];

  const mockNetworkResponse = VendorNetworkResponse(
    technicians: mockTechnicians,
    counts: {'TOTAL': 2, 'ACTIVE': 1, 'SUSPENDED': 1},
  );

  const mockInvitations = [
    VendorSentInvitation(
      id: 101,
      inviteCode: 'INV-A1B2',
      invitedEmail: 'tech.candidate1@example.com',
      technicianName: 'Candidate One',
      technicianEmail: 'tech.candidate1@example.com',
      technicianPhone: '+91 9876500001',
      status: 'PENDING',
      channel: 'DIRECT_EMAIL',
      createdAt: '2026-09-01T09:00:00Z',
      expiresAt: '2026-09-15T09:00:00Z',
    ),
    VendorSentInvitation(
      id: 102,
      inviteCode: 'INV-C3D4',
      invitedEmail: 'tech.candidate2@example.com',
      technicianName: 'Candidate Two',
      technicianEmail: 'tech.candidate2@example.com',
      technicianPhone: '+91 9876500002',
      status: 'ACCEPTED',
      channel: 'DIRECT_EMAIL',
      createdAt: '2026-08-25T11:00:00Z',
      expiresAt: '2026-09-08T11:00:00Z',
    ),
  ];

  const mockInvitationsResponse = VendorInvitationsResponse(
    invitations: mockInvitations,
    counts: {'TOTAL': 2, 'PENDING': 1, 'ACCEPTED': 1},
  );

  const mockProfile = ProviderProfile(
    id: 5,
    companyName: 'CoolCare Services Ltd',
    companyCode: 'CC-BLR-01',
    registrationNumber: 'REG-2024-9988',
    email: 'contact@coolcare.com',
    phone: '+91 80 2345 6789',
    address: '100 Feet Road, Indiranagar',
    city: 'Bengaluru',
    state: 'Karnataka',
    postalCode: '560038',
    isActive: true,
    isVerified: true,
    tiedTechniciansCount: 18,
    primaryAdmin: {
      'first_name': 'Rajesh',
      'last_name': 'Sharma',
      'email': 'rajesh@coolcare.com',
      'phone': '+91 9988776655',
    },
  );

  setUp(() {
    AppColors.configure(brightness: Brightness.light, highContrast: false);
  });

  group('Admin Tied Technicians Screen Tests', () {
    testWidgets('displays technician network list and summary metrics',
        (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockVendorAdmin)),
            adminVendorNetworkProvider
                .overrideWith((ref, params) async => mockNetworkResponse),
          ],
          child: const MaterialApp(
            home: AdminTiedTechniciansScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Tied Technicians'), findsWidgets);
      expect(find.text('Ravi Kumar'), findsOneWidget);
      expect(find.text('Senior HVAC Tech'), findsOneWidget);
      expect(find.text('Anand Singh'), findsOneWidget);
      expect(find.text('Appliance Repair Lead'), findsOneWidget);
      expect(find.text('ACTIVE'), findsWidgets);
      expect(find.text('SUSPENDED'), findsWidgets);
    });
  });

  group('Admin Vendor Invitations Screen Tests', () {
    testWidgets('displays invitations list, codes, and open invite dialog button',
        (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockVendorAdmin)),
            adminVendorInvitationsProvider
                .overrideWith((ref, status) async => mockInvitationsResponse),
          ],
          child: const MaterialApp(
            home: AdminVendorInvitationsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Send Invitations'), findsWidgets);
      expect(find.text('tech.candidate1@example.com'), findsOneWidget);
      expect(find.text('CODE: INV-A1B2'), findsOneWidget);
      expect(find.text('Send New Invitation'), findsOneWidget);
    });
  });

  group('Admin Provider Profile Screen Tests', () {
    testWidgets('displays organization profile and credentials', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockVendorAdmin)),
            adminProviderProfileProvider
                .overrideWith((ref) async => mockProfile),
          ],
          child: const MaterialApp(
            home: AdminProviderProfileScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Company Profile'), findsWidgets);
      expect(find.text('CoolCare Services Ltd'), findsWidgets);
      expect(find.text('REG-2024-9988'), findsOneWidget);
      expect(find.text('contact@coolcare.com'), findsOneWidget);
      expect(find.text('Rajesh Sharma'), findsOneWidget);
    });
  });

  group('Admin Settings Screen Tests', () {
    testWidgets('displays service provider settings options', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockVendorAdmin)),
          ],
          child: const MaterialApp(
            home: AdminSettingsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('System Settings'), findsWidgets);
      expect(find.text('Account & Security'), findsOneWidget);
      expect(find.text('Appearance & UI'), findsOneWidget);
      expect(find.text('Notifications & Alerts'), findsOneWidget);
      expect(find.text('Privacy & Data Governance'), findsOneWidget);
      expect(find.text('SEVO Workforce Operations Platform v2.4.0'), findsOneWidget);
    });
  });
}
