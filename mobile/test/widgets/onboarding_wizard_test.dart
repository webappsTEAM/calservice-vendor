import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/notifications/presentation/notifications_providers.dart';
import 'package:mobile/features/onboarding_wizard/data/onboarding_repository.dart';
import 'package:mobile/features/onboarding_wizard/presentation/onboarding_wizard_screen.dart';
import 'package:mobile/features/profile/domain/employee_profile.dart';
import 'package:mobile/features/profile/presentation/profile_providers.dart';
import 'package:mobile/features/services/domain/service_catalog.dart';
import 'package:mobile/features/services/presentation/services_providers.dart';

class FakeAuthController extends StateNotifier<AuthState> implements AuthController {
  FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeOnboardingRepository implements OnboardingRepository {
  final List<Map<String, dynamic>> savedDrafts = [];
  bool submitCalled = false;

  @override
  Future<void> saveDraft({required int step, required Map<String, dynamic> draftData}) async {
    savedDrafts.add({'step': step, 'draft_data': draftData});
  }

  @override
  Future<void> submit() async {
    submitCalled = true;
  }
}

void main() {
  const mockUser = AuthUser(
    id: 1,
    username: 'zayn',
    email: 'zayn@example.com',
    firstName: 'Zayn',
    lastName: '',
    role: 'employee',
    companyId: 1,
    companyName: 'CalServices',
    isSuperuser: false,
    employeeId: null,
    registrationStatus: 'not_started',
  );

  EmployeeProfile buildProfile({int step = 1, Map<String, dynamic>? personalDraft}) {
    return EmployeeProfile(
      firstName: 'Zayn',
      lastName: '',
      isOnline: false,
      registrationStatus: 'not_started',
      approvedServices: const [],
      allRequestedServices: const [],
      documents: const [],
      controlledFields: const ControlledFieldsConfig(isLocked: false, lockedFields: []),
      onboardingData: OnboardingData(
        status: 'not_started',
        step: step,
        draft: {'personal': personalDraft ?? <String, dynamic>{}},
        services: const [],
        correctionNotes: '',
        rejectionReason: '',
      ),
    );
  }

  Widget createSubject({
    required EmployeeProfile profile,
    required _FakeOnboardingRepository fakeRepo,
    int? initialStep,
  }) {
    return ProviderScope(
      overrides: [
        authControllerProvider.overrideWith((ref) => FakeAuthController(mockUser)),
        employeeProfileProvider.overrideWith((ref) => Future.value(profile)),
        serviceCatalogProvider.overrideWith((ref) => Future.value(<CatalogCategory>[])),
        onboardingRepositoryProvider.overrideWithValue(fakeRepo),
        unreadNotificationsCountProvider.overrideWithValue(0),
      ],
      child: MaterialApp(
        theme: ThemeData.light(useMaterial3: true),
        home: OnboardingWizardScreen(initialStep: initialStep),
      ),
    );
  }

  testWidgets('Step 1 renders personal information fields', (tester) async {
    final fakeRepo = _FakeOnboardingRepository();
    await tester.pumpWidget(createSubject(profile: buildProfile(), fakeRepo: fakeRepo));
    await tester.pump();
    await tester.pump();

    expect(tester.takeException(), isNull);
    expect(find.text('Step 1 of 7: Personal'), findsOneWidget);
    expect(find.text('1. Personal Information'), findsOneWidget);
    expect(find.textContaining('Date of Birth', findRichText: true), findsOneWidget);
    expect(find.text('Save & Continue'), findsOneWidget);
  });

  testWidgets('blocks continue without date of birth and shows validation message', (tester) async {
    final fakeRepo = _FakeOnboardingRepository();
    await tester.pumpWidget(createSubject(profile: buildProfile(), fakeRepo: fakeRepo));
    await tester.pump();
    await tester.pump();

    await tester.tap(find.text('Save & Continue'));
    await tester.pump();

    expect(find.text('Please enter your date of birth.'), findsOneWidget);
    expect(fakeRepo.savedDrafts, isEmpty);
  });

  testWidgets('saving step 1 preserves pre-seeded personal keys and advances to step 2', (tester) async {
    final fakeRepo = _FakeOnboardingRepository();
    await tester.pumpWidget(
      createSubject(
        profile: buildProfile(personalDraft: {'first_name': 'Zayn', 'email': 'zayn@example.com'}),
        fakeRepo: fakeRepo,
      ),
    );
    await tester.pump();
    await tester.pump();

    // The DOB field is read-only and opens a date picker (matching web's
    // native <input type="date">) — drive the picker rather than
    // enterText, which doesn't attach to a read-only field.
    await tester.tap(find.byType(TextField).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Save & Continue'));
    await tester.pumpAndSettle();

    expect(fakeRepo.savedDrafts, hasLength(1));
    final sentPersonal = fakeRepo.savedDrafts.first['draft_data']['personal'] as Map<String, dynamic>;
    expect(sentPersonal['dob'], isNotEmpty);
    expect(sentPersonal['first_name'], 'Zayn');
    expect(sentPersonal['email'], 'zayn@example.com');
    expect(find.text('Step 2 of 7: Address & Territory'), findsOneWidget);
  });

  testWidgets('resumes at the backend-reported step', (tester) async {
    final fakeRepo = _FakeOnboardingRepository();
    await tester.pumpWidget(createSubject(profile: buildProfile(step: 4), fakeRepo: fakeRepo));
    await tester.pump();
    await tester.pump();

    expect(find.text('Step 4 of 7: Skills & Tools'), findsOneWidget);
  });

  testWidgets('correction re-entry honours an explicit initialStep over the stored step', (tester) async {
    final fakeRepo = _FakeOnboardingRepository();
    await tester.pumpWidget(
      createSubject(profile: buildProfile(step: 2), fakeRepo: fakeRepo, initialStep: 5),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('Step 5 of 7: Documents'), findsOneWidget);
  });
}
