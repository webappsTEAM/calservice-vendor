import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/storage/token_storage.dart';
import 'package:mobile/features/auth/data/auth_api.dart';
import 'package:mobile/features/auth/data/auth_repository.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/dashboard/presentation/home_screen.dart';
import 'package:mobile/features/onboarding_status/presentation/correction_required_screen.dart';
import 'package:mobile/features/onboarding_status/presentation/pending_review_screen.dart';
import 'package:mobile/features/onboarding_status/presentation/registration_incomplete_screen.dart';
import 'package:mobile/features/onboarding_status/presentation/rejected_screen.dart';
import 'package:mobile/routing/app_router.dart';
import 'package:mobile/routing/app_routes.dart';

class MockTokenStorage extends TokenStorage {
  String? accessToken;
  String? refreshToken;

  @override
  Future<String?> readAccessToken() async => accessToken;

  @override
  Future<String?> readRefreshToken() async => refreshToken;

  @override
  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
  }

  @override
  Future<void> clear() async {
    accessToken = null;
    refreshToken = null;
  }
}

class FakeAuthRepository extends AuthRepository {
  FakeAuthRepository({required super.authApi, required super.tokenStorage});

  AuthUser? mockUser;
  bool shouldThrow = false;
  Map<String, dynamic>? lastSignupPayload;

  @override
  Future<AuthUser?> restoreSession() async => mockUser;

  @override
  Future<AuthUser> login({required String identifier, required String password}) async {
    if (shouldThrow) throw Exception('Invalid credentials');
    return mockUser ??
        const AuthUser(
          id: 1,
          username: 'tech_mani',
          email: 'mani@calservices.com',
          firstName: 'Manikandan',
          lastName: 'Sundaram',
          role: 'employee',
          companyId: 1,
          companyName: 'CalServices Operations',
          isSuperuser: false,
          employeeId: 'EMP-1001',
          registrationStatus: 'approved',
        );
  }

  @override
  Future<AuthUser> signup({
    required String firstName,
    String? lastName,
    required String mobileNumber,
    required String email,
    required String password,
  }) async {
    if (shouldThrow) throw Exception('Email already exists');
    lastSignupPayload = {
      'first_name': firstName,
      if (lastName != null && lastName.isNotEmpty) 'last_name': lastName,
      'mobile_number': mobileNumber,
      'email': email,
      'password': password,
    };
    return AuthUser(
      id: 2,
      username: email.split('@').first,
      email: email,
      firstName: firstName,
      lastName: lastName ?? '',
      role: 'employee',
      companyId: 1,
      companyName: 'CalServices Operations',
      isSuperuser: false,
      employeeId: 'EMP-1002',
      registrationStatus: 'not_started',
    );
  }
}

void main() {
  late MockTokenStorage mockTokenStorage;
  late FakeAuthRepository fakeAuthRepository;

  setUp(() {
    mockTokenStorage = MockTokenStorage();
    fakeAuthRepository = FakeAuthRepository(
      authApi: AuthApi(Dio()),
      tokenStorage: mockTokenStorage,
    );
  });

  Widget createTestWidget({String initialLocation = AppRoutes.login}) {
    return ProviderScope(
      overrides: [
        tokenStorageProvider.overrideWithValue(mockTokenStorage),
        authRepositoryProvider.overrideWithValue(fakeAuthRepository),
      ],
      child: Consumer(
        builder: (context, ref, _) {
          final router = ref.watch(appRouterProvider);
          return MaterialApp.router(
            routerConfig: router,
          );
        },
      ),
    );
  }

  group('LoginScreen Tests', () {
    testWidgets('renders Employee Sign In header, branding, fields, and Create Account entry',
        (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('SEVO VENDOR'), findsOneWidget);
      expect(find.text('WORKFORCE'), findsOneWidget);
      expect(find.text('Employee Sign In'), findsOneWidget);
      expect(find.text('Sign in to access your Workforce account.'), findsOneWidget);
      expect(find.text('Email, Username or Employee ID'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.text('Sign In'), findsOneWidget);
      expect(find.text('New technician? '), findsOneWidget);
      expect(find.text('Create Account'), findsOneWidget);
      expect(find.textContaining('CALDIM ENGINEERING'), findsOneWidget);
    });

    testWidgets('tapping Create Account navigates to CreateAccountScreen', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      final createAccountLink = find.text('Create Account');
      expect(createAccountLink, findsOneWidget);

      await tester.tap(createAccountLink);
      await tester.pumpAndSettle();

      expect(find.text('Join the Workforce Platform'), findsOneWidget);
      expect(find.text('Create your technician account to start onboarding'), findsOneWidget);
    });
  });

  group('CreateAccountScreen Form & Validation Tests', () {
    testWidgets('renders all required form fields and labels', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create Account'));
      await tester.pumpAndSettle();

      expect(find.textContaining('First Name'), findsOneWidget);
      expect(find.textContaining('Last Name'), findsOneWidget);
      expect(find.textContaining('Mobile Number'), findsOneWidget);
      expect(find.textContaining('Email Address'), findsOneWidget);
      expect(find.textContaining('Password'), findsWidgets);
      expect(find.textContaining('Confirm Password'), findsOneWidget);
      expect(find.text('Create Account & Start Onboarding'), findsOneWidget);
      expect(find.text('Already have an account? '), findsOneWidget);
      expect(find.text('Sign In'), findsOneWidget);
      expect(find.textContaining('CALDIM ENGINEERING'), findsOneWidget);
    });

    testWidgets('tapping Sign In navigates back from Create Account to Login', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create Account'));
      await tester.pumpAndSettle();

      expect(find.text('Join the Workforce Platform'), findsOneWidget);

      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      expect(find.text('Employee Sign In'), findsOneWidget);
    });

    testWidgets('validates required fields on empty submit', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create Account'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create Account & Start Onboarding'));
      await tester.pumpAndSettle();

      expect(find.text('First name required'), findsOneWidget);
      expect(find.text('Mobile number required'), findsOneWidget);
      expect(find.text('Email address required'), findsOneWidget);
      expect(find.text('Password required'), findsOneWidget);
    });

    testWidgets('validates invalid email format', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create Account'));
      await tester.pumpAndSettle();

      final textFields = find.byType(TextFormField);
      await tester.enterText(textFields.at(0), 'Ramesh');
      await tester.enterText(textFields.at(2), '9876543210');
      await tester.enterText(textFields.at(3), 'not-an-email');
      await tester.enterText(textFields.at(4), 'Password123');
      await tester.enterText(textFields.at(5), 'Password123');

      await tester.tap(find.text('Create Account & Start Onboarding'));
      await tester.pumpAndSettle();

      expect(find.text('Enter a valid email address'), findsOneWidget);
    });

    testWidgets('validates minimum 6-character password requirement', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create Account'));
      await tester.pumpAndSettle();

      final textFields = find.byType(TextFormField);
      await tester.enterText(textFields.at(0), 'Ramesh');
      await tester.enterText(textFields.at(2), '9876543210');
      await tester.enterText(textFields.at(3), 'ramesh@example.com');
      await tester.enterText(textFields.at(4), '123');
      await tester.enterText(textFields.at(5), '123');

      await tester.tap(find.text('Create Account & Start Onboarding'));
      await tester.pumpAndSettle();

      expect(find.text('Password must be at least 6 characters'), findsOneWidget);
    });

    testWidgets('validates password mismatch', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create Account'));
      await tester.pumpAndSettle();

      final textFields = find.byType(TextFormField);
      await tester.enterText(textFields.at(0), 'Ramesh');
      await tester.enterText(textFields.at(2), '9876543210');
      await tester.enterText(textFields.at(3), 'ramesh@example.com');
      await tester.enterText(textFields.at(4), 'Password123');
      await tester.enterText(textFields.at(5), 'DifferentPassword');

      await tester.tap(find.text('Create Account & Start Onboarding'));
      await tester.pumpAndSettle();

      expect(find.text('Passwords do not match'), findsOneWidget);
    });

    testWidgets('toggles password visibility icons', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create Account'));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.visibility_outlined), findsNWidgets(2));

      // Toggle first password visibility
      await tester.tap(find.byIcon(Icons.visibility_outlined).first);
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.visibility_off_outlined), findsOneWidget);
      expect(find.byIcon(Icons.visibility_outlined), findsOneWidget);
    });

    testWidgets('successful signup routes to RegistrationIncompleteScreen (Admin Approval not bypassed)',
        (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create Account'));
      await tester.pumpAndSettle();

      final textFields = find.byType(TextFormField);
      await tester.enterText(textFields.at(0), 'Ramesh');
      await tester.enterText(textFields.at(1), 'Kumar');
      await tester.enterText(textFields.at(2), '9876543210');
      await tester.enterText(textFields.at(3), 'ramesh@example.com');
      await tester.enterText(textFields.at(4), 'Secret123');
      await tester.enterText(textFields.at(5), 'Secret123');

      await tester.tap(find.text('Create Account & Start Onboarding'));
      await tester.pumpAndSettle();

      // Verify payload passed to backend repository
      expect(fakeAuthRepository.lastSignupPayload?['first_name'], 'Ramesh');
      expect(fakeAuthRepository.lastSignupPayload?['last_name'], 'Kumar');
      expect(fakeAuthRepository.lastSignupPayload?['mobile_number'], '9876543210');
      expect(fakeAuthRepository.lastSignupPayload?['email'], 'ramesh@example.com');

      // Verify routed to RegistrationIncompleteScreen because registration_status is not_started
      expect(find.byType(RegistrationIncompleteScreen), findsOneWidget);
      expect(find.text('Registration Incomplete'), findsOneWidget);
      expect(find.byType(HomeScreen), findsNothing);
    });
  });

  group('Onboarding Status & Admin Approval Routing Tests', () {
    testWidgets('user with submitted / under_review routes to PendingReviewScreen and cannot access HomeScreen',
        (tester) async {
      fakeAuthRepository.mockUser = const AuthUser(
        id: 3,
        username: 'tech_pending',
        email: 'pending@calservices.com',
        firstName: 'Pending',
        lastName: 'Tech',
        role: 'employee',
        companyId: 1,
        companyName: 'CalServices Operations',
        isSuperuser: false,
        employeeId: 'EMP-1003',
        registrationStatus: 'under_review',
      );

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.byType(PendingReviewScreen), findsOneWidget);
      expect(find.text('Application Under Review'), findsOneWidget);
      expect(find.byType(HomeScreen), findsNothing);
    });

    testWidgets('user with correction_required routes to CorrectionRequiredScreen',
        (tester) async {
      fakeAuthRepository.mockUser = const AuthUser(
        id: 4,
        username: 'tech_correct',
        email: 'correct@calservices.com',
        firstName: 'Correction',
        lastName: 'Tech',
        role: 'employee',
        companyId: 1,
        companyName: 'CalServices Operations',
        isSuperuser: false,
        employeeId: 'EMP-1004',
        registrationStatus: 'correction_required',
      );

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.byType(CorrectionRequiredScreen), findsOneWidget);
      expect(find.text('Corrections Needed'), findsOneWidget);
      expect(find.byType(HomeScreen), findsNothing);
    });

    testWidgets('user with rejected status routes to RejectedScreen', (tester) async {
      fakeAuthRepository.mockUser = const AuthUser(
        id: 5,
        username: 'tech_rejected',
        email: 'rejected@calservices.com',
        firstName: 'Rejected',
        lastName: 'Tech',
        role: 'employee',
        companyId: 1,
        companyName: 'CalServices Operations',
        isSuperuser: false,
        employeeId: 'EMP-1005',
        registrationStatus: 'rejected',
      );

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.byType(RejectedScreen), findsOneWidget);
      expect(find.text('Application Declined'), findsOneWidget);
      expect(find.byType(HomeScreen), findsNothing);
    });

    testWidgets('user with approved status routes to HomeScreen', (tester) async {
      fakeAuthRepository.mockUser = const AuthUser(
        id: 6,
        username: 'tech_approved',
        email: 'approved@calservices.com',
        firstName: 'Approved',
        lastName: 'Tech',
        role: 'employee',
        companyId: 1,
        companyName: 'CalServices Operations',
        isSuperuser: false,
        employeeId: 'EMP-1006',
        registrationStatus: 'approved',
      );

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.byType(HomeScreen), findsOneWidget);
    });
  });
}
