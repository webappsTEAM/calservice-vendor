import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/config/app_config.dart';
import 'package:mobile/core/storage/token_storage.dart';
import 'package:mobile/features/admin/presentation/admin_home_screen.dart';
import 'package:mobile/features/auth/data/auth_api.dart';
import 'package:mobile/features/auth/data/auth_repository.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/domain/provider_registration_result.dart';
import 'package:mobile/features/auth/presentation/create_account_screen.dart';
import 'package:mobile/features/auth/presentation/provider_register_screen.dart';
import 'package:mobile/features/onboarding/data/onboarding_storage.dart';
import 'package:mobile/features/superadmin/presentation/superadmin_dashboard_screen.dart';
import 'package:mobile/routing/app_router.dart';

class _MockTokenStorage extends TokenStorage {
  String? _accessToken;
  String? _refreshToken;

  @override
  Future<String?> readAccessToken() async => _accessToken;

  @override
  Future<String?> readRefreshToken() async => _refreshToken;

  @override
  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    _accessToken = accessToken;
    _refreshToken = refreshToken;
  }

  @override
  Future<void> clear() async {
    _accessToken = null;
    _refreshToken = null;
  }
}

class _FakeOnboardingStorage extends OnboardingStorage {
  _FakeOnboardingStorage({this.completed = true});
  bool completed;

  @override
  Future<bool> hasCompletedOnboarding() async => completed;

  @override
  Future<void> setOnboardingCompleted() async {
    completed = true;
  }

  @override
  Future<void> clear() async {
    completed = false;
  }
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository({required super.authApi, required super.tokenStorage});

  AuthUser? mockUser;
  bool shouldThrow = false;
  bool delayRegister = false;
  String? throwMessage;
  ProviderRegistrationResult? mockProviderResult;
  Map<String, dynamic>? lastProviderSignupPayload;
  Map<String, dynamic>? lastSignupPayload;

  @override
  Future<AuthUser?> restoreSession() async => mockUser;

  @override
  Future<AuthUser> login({required String identifier, required String password}) async {
    if (shouldThrow) throw Exception(throwMessage ?? 'Invalid credentials');
    return mockUser ??
        const AuthUser(
          id: 1,
          username: 'provider_admin',
          email: 'admin@provider.com',
          firstName: 'Rajesh',
          lastName: 'Kumar',
          role: 'manager',
          companyId: 1092,
          companyName: 'Apex Plumbing Solutions',
          isSuperuser: false,
          employeeId: null,
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
    dynamic companyId,
  }) async {
    if (shouldThrow) throw Exception(throwMessage ?? 'Email already registered');
    lastSignupPayload = {
      'first_name': firstName,
      if (lastName != null && lastName.isNotEmpty) 'last_name': lastName,
      'mobile_number': mobileNumber,
      'email': email,
      'password': password,
      'company_id': ?companyId,
    };
    return const AuthUser(
      id: 2,
      username: 'tech_worker',
      email: 'worker@provider.com',
      firstName: 'Worker',
      lastName: 'One',
      role: 'employee',
      companyId: 1092,
      companyName: 'Apex Plumbing Solutions',
      isSuperuser: false,
      employeeId: 'EMP-1002',
      registrationStatus: 'not_started',
    );
  }

  @override
  Future<ProviderRegistrationResult> registerProvider({
    required String businessName,
    required String contactFirstName,
    String? contactLastName,
    required String mobileNumber,
    required String email,
    required String password,
    String? address,
    String? city,
  }) async {
    if (delayRegister) {
      await Future<void>.delayed(const Duration(milliseconds: 300));
    }
    if (shouldThrow) throw Exception(throwMessage ?? 'Business registration failed');
    lastProviderSignupPayload = {
      'business_name': businessName,
      'contact_first_name': contactFirstName,
      if (contactLastName != null && contactLastName.isNotEmpty) 'contact_last_name': contactLastName,
      'mobile_number': mobileNumber,
      'email': email,
      'password': password,
      if (address != null && address.isNotEmpty) 'address': address,
      if (city != null && city.isNotEmpty) 'city': city,
    };
    return mockProviderResult ??
        const ProviderRegistrationResult(
          message: 'Provider registered successfully',
          accessToken: 'fake_jwt_token',
          refreshToken: 'fake_refresh_token',
          token: 'fake_jwt_token',
          company: ProviderCompanyInfo(
            id: 1092,
            slug: 'apex-plumbing',
            companyName: 'Apex Plumbing Solutions',
          ),
          user: AuthUser(
            id: 42,
            username: 'apex_admin',
            email: 'admin@apexplumbing.com',
            firstName: 'Rajesh',
            lastName: 'Kumar',
            role: 'manager',
            companyId: 1092,
            companyName: 'Apex Plumbing Solutions',
            isSuperuser: false,
            employeeId: null,
            registrationStatus: 'approved',
          ),
        );
  }
}

void main() {
  late _MockTokenStorage mockTokenStorage;
  late _FakeAuthRepository fakeAuthRepository;
  late _FakeOnboardingStorage fakeOnboardingStorage;

  setUp(() {
    mockTokenStorage = _MockTokenStorage();
    fakeAuthRepository = _FakeAuthRepository(
      authApi: AuthApi(Dio()),
      tokenStorage: mockTokenStorage,
    );
    fakeOnboardingStorage = _FakeOnboardingStorage(completed: true);
  });

  Widget createTestApp() {
    return ProviderScope(
      overrides: [
        tokenStorageProvider.overrideWithValue(mockTokenStorage),
        authRepositoryProvider.overrideWithValue(fakeAuthRepository),
        onboardingStorageProvider.overrideWithValue(fakeOnboardingStorage),
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

  Future<void> navigateToProviderRegister(WidgetTester tester) async {
    await tester.pumpWidget(createTestApp());
    await tester.pumpAndSettle();

    // From LoginScreen, scroll to Create Account if needed and tap it
    final createAccountFinder = find.text('Create Account');
    await tester.scrollUntilVisible(
      createAccountFinder,
      50,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(createAccountFinder);
    await tester.pumpAndSettle();

    // From CreateAccountScreen, scroll to "Sign up here" and tap it
    final signUpLink = find.text('Sign up here');
    await tester.scrollUntilVisible(
      signUpLink,
      50,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(signUpLink);
    await tester.pumpAndSettle();
  }

  group('ProviderRegisterScreen & Authentication Tests', () {
    // 1. Provider registration screen renders correctly
    testWidgets('1. Provider registration screen renders correctly with all fields and headers', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await navigateToProviderRegister(tester);

      expect(find.byType(ProviderRegisterScreen), findsOneWidget);
      expect(find.text('Register Your Service Business'), findsOneWidget);
      expect(
        find.text('For plumbing, electrical, carpentry and other provider businesses with their own team'),
        findsOneWidget,
      );

      // Section headers
      expect(find.text('BUSINESS INFORMATION'), findsOneWidget);
      expect(find.text('CONTACT PERSON'), findsOneWidget);
      expect(find.text('SECURITY CREDENTIALS'), findsOneWidget);

      // Field labels
      expect(find.textContaining('Business Name'), findsOneWidget);
      expect(find.textContaining('City'), findsOneWidget);
      expect(find.textContaining('Address (Optional)'), findsOneWidget);
      expect(find.textContaining('Contact First Name'), findsOneWidget);
      expect(find.textContaining('Contact Last Name'), findsOneWidget);
      expect(find.textContaining('Mobile Number'), findsOneWidget);
      expect(find.textContaining('Email Address'), findsOneWidget);
      expect(find.textContaining('Password'), findsWidgets);
      expect(find.textContaining('Confirm Password'), findsOneWidget);

      // Buttons and links
      expect(find.text('Register Business'), findsOneWidget);
      expect(find.text('Signing up as an individual technician instead? '), findsOneWidget);
      expect(find.text('Sign up here'), findsOneWidget);
      expect(find.text('Already have an account? '), findsOneWidget);
      expect(find.text('Sign In'), findsOneWidget);
    });

    // 2. Required field validation
    testWidgets('2. Validates required fields on empty submit', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await navigateToProviderRegister(tester);

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pumpAndSettle();

      expect(find.text('Business name is required'), findsOneWidget);
      expect(find.text('Contact first name is required'), findsOneWidget);
      expect(find.text('Mobile number is required'), findsOneWidget);
      expect(find.text('Email address is required'), findsOneWidget);
      expect(find.text('Password is required'), findsOneWidget);
    });

    // 3. Email validation
    testWidgets('3. Validates email format properly', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await navigateToProviderRegister(tester);

      final emailField = find.widgetWithText(TextFormField, 'business@example.com');
      await tester.scrollUntilVisible(emailField, 80, scrollable: find.byType(Scrollable).first);
      await tester.enterText(emailField, 'not-a-valid-email');

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pumpAndSettle();

      expect(find.text('Enter a valid email address'), findsOneWidget);
    });

    // 3b. Mobile validation
    testWidgets('3b. Validates mobile number format and length', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await navigateToProviderRegister(tester);

      final mobileField = find.widgetWithText(TextFormField, '10-digit mobile number');
      await tester.scrollUntilVisible(mobileField, 80, scrollable: find.byType(Scrollable).first);
      await tester.enterText(mobileField, '12345');

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pumpAndSettle();

      expect(find.text('Enter a valid 10-digit mobile number'), findsOneWidget);
    });

    // 3c. Password validation
    testWidgets('3c. Validates minimum 6-character password requirement', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await navigateToProviderRegister(tester);

      final passwordField = find.widgetWithText(TextFormField, 'Minimum 6 characters');
      await tester.scrollUntilVisible(passwordField, 80, scrollable: find.byType(Scrollable).first);
      await tester.enterText(passwordField, '123');

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pumpAndSettle();

      expect(find.text('Password must be at least 6 characters'), findsOneWidget);
    });

    // 4. Password confirmation validation
    testWidgets('4. Validates password mismatch', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await navigateToProviderRegister(tester);

      final passwordField = find.widgetWithText(TextFormField, 'Minimum 6 characters');
      final confirmPasswordField = find.widgetWithText(TextFormField, 'Re-enter password');

      await tester.scrollUntilVisible(passwordField, 80, scrollable: find.byType(Scrollable).first);
      await tester.enterText(passwordField, 'Password123');

      await tester.scrollUntilVisible(confirmPasswordField, 80, scrollable: find.byType(Scrollable).first);
      await tester.enterText(confirmPasswordField, 'Different123');

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pumpAndSettle();

      expect(find.text('Passwords do not match'), findsOneWidget);
    });

    // 4b. Password show/hide visibility toggle
    testWidgets('4b. Toggles password visibility icons', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await navigateToProviderRegister(tester);

      final visibilityIcons = find.byIcon(Icons.visibility_off_outlined);
      expect(visibilityIcons, findsNWidgets(2));

      // Tap first visibility icon
      await tester.scrollUntilVisible(visibilityIcons.first, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(visibilityIcons.first);
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.visibility_outlined), findsOneWidget);
      expect(find.byIcon(Icons.visibility_off_outlined), findsOneWidget);
    });

    // 5. Technician signup → provider signup navigation
    testWidgets('5. Technician signup navigates to provider signup when clicking Sign up here', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Go to technician signup
      final createAccountFinder = find.text('Create Account');
      await tester.scrollUntilVisible(createAccountFinder, 50, scrollable: find.byType(Scrollable).first);
      await tester.tap(createAccountFinder);
      await tester.pumpAndSettle();

      expect(find.byType(CreateAccountScreen), findsOneWidget);
      expect(find.text('Join the Workforce Platform'), findsOneWidget);
      expect(find.text('Registering a service provider business instead? '), findsOneWidget);

      // Scroll to "Sign up here" and tap
      final signUpLink = find.text('Sign up here');
      await tester.scrollUntilVisible(signUpLink, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(signUpLink);
      await tester.pumpAndSettle();

      expect(find.byType(ProviderRegisterScreen), findsOneWidget);
      expect(find.text('Register Your Service Business'), findsOneWidget);
    });

    // 6. Provider signup → technician signup navigation
    testWidgets('6. Provider signup navigates back to technician signup', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await navigateToProviderRegister(tester);
      expect(find.byType(ProviderRegisterScreen), findsOneWidget);

      // Scroll to "Sign up here" under "Signing up as an individual technician instead?"
      final signUpLink = find.text('Sign up here');
      await tester.scrollUntilVisible(signUpLink, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(signUpLink);
      await tester.pumpAndSettle();

      expect(find.byType(CreateAccountScreen), findsOneWidget);
      expect(find.text('Join the Workforce Platform'), findsOneWidget);
    });

    // 7. Loading / submitting state
    testWidgets('7. Displays loading state while submitting form', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      fakeAuthRepository.delayRegister = true;

      await navigateToProviderRegister(tester);

      // Fill valid form
      await tester.enterText(find.widgetWithText(TextFormField, 'e.g. Apex Plumbing Solutions'), 'Apex Services');
      await tester.enterText(find.widgetWithText(TextFormField, 'First name'), 'Rajesh');
      await tester.enterText(find.widgetWithText(TextFormField, '10-digit mobile number'), '9876543210');
      await tester.enterText(find.widgetWithText(TextFormField, 'business@example.com'), 'rajesh@apex.com');
      await tester.enterText(find.widgetWithText(TextFormField, 'Minimum 6 characters'), 'Secret123');
      await tester.enterText(find.widgetWithText(TextFormField, 'Re-enter password'), 'Secret123');

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pump(const Duration(milliseconds: 50)); // Advance frame to capture in-flight progress state

      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      await tester.pumpAndSettle();
      fakeAuthRepository.delayRegister = false;
    });

    // 8. Successful provider registration success screen
    testWidgets('8. Successful registration shows provider success screen with business name', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await navigateToProviderRegister(tester);

      await tester.enterText(find.widgetWithText(TextFormField, 'e.g. Apex Plumbing Solutions'), 'Apex Plumbing Solutions');
      await tester.enterText(find.widgetWithText(TextFormField, 'First name'), 'Rajesh');
      await tester.enterText(find.widgetWithText(TextFormField, 'Last name (optional)'), 'Kumar');
      await tester.enterText(find.widgetWithText(TextFormField, '10-digit mobile number'), '9876543210');
      await tester.enterText(find.widgetWithText(TextFormField, 'business@example.com'), 'admin@apexplumbing.com');
      await tester.enterText(find.widgetWithText(TextFormField, 'Minimum 6 characters'), 'Secret123');
      await tester.enterText(find.widgetWithText(TextFormField, 'Re-enter password'), 'Secret123');

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pumpAndSettle();

      // Verify success screen is displayed
      expect(find.text('Apex Plumbing Solutions is registered'), findsOneWidget);
      expect(
        find.text("Share this link with your own workers so they join your team's wallet instead of signing up as independent technicians:"),
        findsOneWidget,
      );
      expect(find.text('WORKER INVITATION LINK'), findsOneWidget);
      expect(find.text('Go to Dashboard'), findsOneWidget);
    });

    // 9. Dynamic company invitation URL generation
    testWidgets('9. Generates dynamic invitation URL with real company ID', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      fakeAuthRepository.mockProviderResult = const ProviderRegistrationResult(
        message: 'Registered',
        accessToken: 'tok_1',
        refreshToken: 'tok_2',
        token: 'tok_1',
        company: ProviderCompanyInfo(
          id: 5432,
          slug: 'speedy-electricians',
          companyName: 'Speedy Electricians',
        ),
        user: AuthUser(
          id: 99,
          username: 'speedy_admin',
          email: 'admin@speedy.com',
          firstName: 'Suresh',
          lastName: 'Patel',
          role: 'manager',
          companyId: 5432,
          companyName: 'Speedy Electricians',
          isSuperuser: false,
          employeeId: null,
          registrationStatus: 'approved',
        ),
      );

      await navigateToProviderRegister(tester);

      await tester.enterText(find.widgetWithText(TextFormField, 'e.g. Apex Plumbing Solutions'), 'Speedy Electricians');
      await tester.enterText(find.widgetWithText(TextFormField, 'First name'), 'Suresh');
      await tester.enterText(find.widgetWithText(TextFormField, '10-digit mobile number'), '9876543210');
      await tester.enterText(find.widgetWithText(TextFormField, 'business@example.com'), 'admin@speedy.com');
      await tester.enterText(find.widgetWithText(TextFormField, 'Minimum 6 characters'), 'Secret123');
      await tester.enterText(find.widgetWithText(TextFormField, 'Re-enter password'), 'Secret123');

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pumpAndSettle();

      final expectedUrl = '${AppConfig.backendBaseUrl}/workforce/signup?company_id=5432';
      expect(find.text(expectedUrl), findsOneWidget);
    });

    // 10. Copy invitation link
    testWidgets('10. Copying invitation link sets clipboard data and displays SnackBar', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      String? copiedClipboardText;
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        (MethodCall methodCall) async {
          if (methodCall.method == 'Clipboard.setData') {
            copiedClipboardText = (methodCall.arguments as Map)['text'] as String?;
            return null;
          }
          return null;
        },
      );

      await navigateToProviderRegister(tester);

      await tester.enterText(find.widgetWithText(TextFormField, 'e.g. Apex Plumbing Solutions'), 'Apex Plumbing');
      await tester.enterText(find.widgetWithText(TextFormField, 'First name'), 'Rajesh');
      await tester.enterText(find.widgetWithText(TextFormField, '10-digit mobile number'), '9876543210');
      await tester.enterText(find.widgetWithText(TextFormField, 'business@example.com'), 'admin@apex.com');
      await tester.enterText(find.widgetWithText(TextFormField, 'Minimum 6 characters'), 'Secret123');
      await tester.enterText(find.widgetWithText(TextFormField, 'Re-enter password'), 'Secret123');

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pumpAndSettle();

      // Tap Copy button
      await tester.tap(find.text('Copy'));
      await tester.pump();

      expect(find.text('Invitation link copied'), findsOneWidget);
      expect(copiedClipboardText, contains('company_id=1092'));
    });

    // 11. Go to Dashboard navigation based on role
    testWidgets('11. Go to Dashboard navigates to Admin Home for provider manager', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await navigateToProviderRegister(tester);

      await tester.enterText(find.widgetWithText(TextFormField, 'e.g. Apex Plumbing Solutions'), 'Apex Plumbing');
      await tester.enterText(find.widgetWithText(TextFormField, 'First name'), 'Rajesh');
      await tester.enterText(find.widgetWithText(TextFormField, '10-digit mobile number'), '9876543210');
      await tester.enterText(find.widgetWithText(TextFormField, 'business@example.com'), 'admin@apex.com');
      await tester.enterText(find.widgetWithText(TextFormField, 'Minimum 6 characters'), 'Secret123');
      await tester.enterText(find.widgetWithText(TextFormField, 'Re-enter password'), 'Secret123');

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pumpAndSettle();

      // Tap Go to Dashboard
      await tester.tap(find.text('Go to Dashboard'));
      await tester.pumpAndSettle();

      // Manager / Admin routes to AdminHomeScreen
      expect(find.byType(AdminHomeScreen), findsOneWidget);
    });

    testWidgets('11b. Go to Dashboard navigates to Superadmin Dashboard for superadmin user', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      fakeAuthRepository.mockProviderResult = const ProviderRegistrationResult(
        message: 'Registered',
        accessToken: 'tok_super',
        refreshToken: 'tok_super_ref',
        token: 'tok_super',
        company: ProviderCompanyInfo(
          id: 1,
          slug: 'master-ops',
          companyName: 'Master Operations',
        ),
        user: AuthUser(
          id: 1,
          username: 'superadmin_ops',
          email: 'superadmin@ops.com',
          firstName: 'Master',
          lastName: 'Admin',
          role: 'superadmin',
          companyId: 1,
          companyName: 'Master Operations',
          isSuperuser: true,
          employeeId: null,
          registrationStatus: 'approved',
        ),
      );

      await navigateToProviderRegister(tester);

      await tester.enterText(find.widgetWithText(TextFormField, 'e.g. Apex Plumbing Solutions'), 'Master Operations');
      await tester.enterText(find.widgetWithText(TextFormField, 'First name'), 'Master');
      await tester.enterText(find.widgetWithText(TextFormField, '10-digit mobile number'), '9876543210');
      await tester.enterText(find.widgetWithText(TextFormField, 'business@example.com'), 'superadmin@ops.com');
      await tester.enterText(find.widgetWithText(TextFormField, 'Minimum 6 characters'), 'Secret123');
      await tester.enterText(find.widgetWithText(TextFormField, 'Re-enter password'), 'Secret123');

      final submitBtn = find.text('Register Business');
      await tester.scrollUntilVisible(submitBtn, 80, scrollable: find.byType(Scrollable).first);
      await tester.tap(submitBtn);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Go to Dashboard'));
      await tester.pumpAndSettle();

      expect(find.byType(SuperAdminDashboardScreen), findsOneWidget);
    });

    // 12 & 13. Responsive testing at 320px, 360px, 390px, 412px with zero RenderFlex overflow
    const testScreenSizes = [
      Size(320, 568), // Compact Android (e.g. small device)
      Size(360, 640), // Standard Android
      Size(390, 844), // Modern Standard iOS / Android
      Size(412, 915), // Large Android
    ];

    for (final size in testScreenSizes) {
      testWidgets('12 & 13. Renders cleanly with zero overflow on ${size.width}x${size.height}', (tester) async {
        tester.view.physicalSize = size;
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() => tester.view.resetPhysicalSize());
        addTearDown(() => tester.view.resetDevicePixelRatio());

        await navigateToProviderRegister(tester);

        expect(tester.takeException(), isNull);

        // Test scrolling down and up
        await tester.drag(find.byType(SingleChildScrollView), const Offset(0, -300));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
      });
    }
  });
}
