import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/admin/presentation/admin_destination_screens.dart';
import '../features/admin/presentation/admin_home_screen.dart';
import '../features/admin/presentation/applications/admin_application_detail_screen.dart';
import '../features/admin/presentation/applications/admin_applications_screen.dart';
import '../features/admin/presentation/employees/admin_employees_screen.dart';
import '../features/admin/presentation/skills/admin_skills_screen.dart';
import '../features/auth/presentation/auth_controller.dart';
import '../features/auth/presentation/create_account_screen.dart';
import '../features/auth/presentation/employee_only_screen.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/dashboard/presentation/home_screen.dart';
import '../features/documents/presentation/documents_screen.dart';
import '../features/finance/presentation/bank_accounts_screen.dart';
import '../features/finance/presentation/transactions_screen.dart';
import '../features/finance/presentation/wallet_screen.dart';
import '../features/finance/presentation/withdrawals_screen.dart';
import '../features/admin/presentation/finance/admin_bank_accounts_screen.dart';
import '../features/admin/presentation/finance/admin_transactions_screen.dart';
import '../features/admin/presentation/finance/admin_wallets_screen.dart';
import '../features/admin/presentation/finance/admin_withdrawals_screen.dart';
import '../features/admin/presentation/monitoring/admin_database_egress_screen.dart';
import '../features/jobs/presentation/job_detail_screen.dart';
import '../features/jobs/presentation/jobs_screen.dart';
import '../features/locations/presentation/locations_screen.dart';
import '../features/more/presentation/more_screen.dart';
import '../features/notifications/presentation/notifications_screen.dart';
import '../features/onboarding/presentation/onboarding_controller.dart';
import '../features/onboarding/presentation/onboarding_screen.dart';
import '../features/onboarding_status/presentation/correction_required_screen.dart';
import '../features/onboarding_status/presentation/pending_review_screen.dart';
import '../features/onboarding_status/presentation/registration_incomplete_screen.dart';
import '../features/onboarding_status/presentation/rejected_screen.dart';
import '../features/onboarding_wizard/presentation/onboarding_wizard_screen.dart';
import '../features/performance/presentation/performance_screen.dart';
import '../features/profile/presentation/profile_screen.dart';
import '../features/services/presentation/services_screen.dart';
import '../features/settings/presentation/account_security_screen.dart';
import '../features/settings/presentation/appearance_screen.dart';
import '../features/settings/presentation/notification_settings_screen.dart';
import '../features/settings/presentation/privacy_data_screen.dart';
import '../features/settings/presentation/settings_screen.dart';
import '../shared/widgets/app_shell_scaffold.dart';
import 'app_routes.dart';

/// Turns one or more Streams into a Listenable so go_router's `refreshListenable` can
/// react to auth-state and onboarding-state changes and re-run its `redirect` logic.
class CompositeGoRouterRefreshStream extends ChangeNotifier {
  CompositeGoRouterRefreshStream(List<Stream<dynamic>> streams) {
    for (final stream in streams) {
      _subscriptions.add(stream.listen((_) => notifyListeners()));
    }
  }

  final List<StreamSubscription<dynamic>> _subscriptions = [];

  @override
  void dispose() {
    for (final sub in _subscriptions) {
      sub.cancel();
    }
    super.dispose();
  }
}

/// Paths that live inside the authenticated employee app (the bottom-nav
/// shell and anything pushed on top of it, like job detail).
bool _isEmployeeAppPath(String location) {
  return location.startsWith(AppRoutes.home) ||
      location.startsWith(AppRoutes.jobs) ||
      location.startsWith(AppRoutes.notifications) ||
      location.startsWith(AppRoutes.more) ||
      location.startsWith(AppRoutes.earnings);
}

/// Paths that live inside the authenticated admin app.
bool _isAdminAppPath(String location) {
  return location.startsWith('/admin') ||
      location.startsWith('/workforce/admin') ||
      location.startsWith(AppRoutes.notifications) ||
      location.startsWith(AppRoutes.more);
}

final appRouterProvider = Provider<GoRouter>((ref) {
  // Watching `.notifier` (a stable reference) rather than the provider's
  // value means this GoRouter is built once, not recreated on every state
  // change — live updates instead flow through refreshListenable below.
  final authController = ref.watch(authControllerProvider.notifier);
  final onboardingController = ref.watch(onboardingControllerProvider.notifier);

  return GoRouter(
    initialLocation: AppRoutes.splash,
    refreshListenable: CompositeGoRouterRefreshStream([
      authController.stream,
      onboardingController.stream,
    ]),
    redirect: (context, state) {
      final authState = ref.read(authControllerProvider);
      final onboardingCompleted = ref.read(onboardingControllerProvider);
      final location = state.matchedLocation;

      // 1. Still resolving session or onboarding completion flag from storage
      if (authState.status == AuthStatus.unknown || onboardingCompleted == null) {
        return location == AppRoutes.splash ? null : AppRoutes.splash;
      }

      // 2. Unauthenticated flow
      if (authState.status == AuthStatus.unauthenticated) {
        // Fresh user / first launch: route to intro onboarding walkthrough
        if (!onboardingCompleted) {
          if (location == AppRoutes.createAccount) return null;
          return location == AppRoutes.onboarding ? null : AppRoutes.onboarding;
        }

        // Returning user who has completed or skipped onboarding
        if (location == AppRoutes.createAccount || location == AppRoutes.onboarding) {
          return null;
        }
        return location == AppRoutes.login ? null : AppRoutes.login;
      }

      // 3. Authenticated flow
      final user = authState.user!;

      // 1. Admin / Management Accounts
      if (user.isAdmin) {
        return _isAdminAppPath(location) ? null : AppRoutes.adminHome;
      }

      // 2. Employee Accounts
      if (!user.isEmployee) {
        return location == AppRoutes.employeeOnly ? null : AppRoutes.employeeOnly;
      }

      switch (user.registrationStatus) {
        case 'approved':
          return _isEmployeeAppPath(location) ? null : AppRoutes.home;
        case 'submitted':
        case 'under_review':
          return location == AppRoutes.pendingReview ? null : AppRoutes.pendingReview;
        case 'correction_required':
          if (location == AppRoutes.onboardingWizard) return null;
          return location == AppRoutes.correctionRequired ? null : AppRoutes.correctionRequired;
        case 'rejected':
          return location == AppRoutes.rejected ? null : AppRoutes.rejected;
        default: // not_started, in_progress, or anything unrecognized
          if (location == AppRoutes.onboardingWizard) return null;
          return location == AppRoutes.registrationIncomplete
              ? null
              : AppRoutes.registrationIncomplete;
      }
    },
    routes: [
      GoRoute(
        path: AppRoutes.splash,
        builder: (context, state) => const _SplashScreen(),
      ),
      GoRoute(
        path: AppRoutes.onboarding,
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: AppRoutes.createAccount,
        builder: (context, state) => const CreateAccountScreen(),
      ),
      GoRoute(
        path: AppRoutes.onboardingWizard,
        builder: (context, state) {
          final stepParam = state.uri.queryParameters['step'];
          final initialStep = stepParam != null ? int.tryParse(stepParam) : null;
          return OnboardingWizardScreen(initialStep: initialStep);
        },
      ),
      GoRoute(
        path: AppRoutes.pendingReview,
        builder: (context, state) => const PendingReviewScreen(),
      ),
      GoRoute(
        path: AppRoutes.correctionRequired,
        builder: (context, state) => const CorrectionRequiredScreen(),
      ),
      GoRoute(
        path: AppRoutes.rejected,
        builder: (context, state) => const RejectedScreen(),
      ),
      GoRoute(
        path: AppRoutes.registrationIncomplete,
        builder: (context, state) => const RegistrationIncompleteScreen(),
      ),
      GoRoute(
        path: AppRoutes.employeeOnly,
        builder: (context, state) => const EmployeeOnlyScreen(),
      ),
      // ── Admin Routes ───────────────────────────────────────────────────────
      GoRoute(
        path: AppRoutes.adminHome,
        builder: (context, state) => const AdminHomeScreen(),
      ),
      GoRoute(
        path: '/workforce/admin',
        redirect: (context, state) => AppRoutes.adminHome,
      ),
      GoRoute(
        path: AppRoutes.adminEmployees,
        builder: (context, state) => const AdminEmployeesScreen(),
      ),
      GoRoute(
        path: '/workforce/admin/employees',
        redirect: (context, state) => AppRoutes.adminEmployees,
      ),
      GoRoute(
        path: AppRoutes.adminApplications,
        builder: (context, state) {
          final status = state.uri.queryParameters['status'];
          return AdminApplicationsScreen(statusFilter: status);
        },
      ),
      GoRoute(
        path: '/workforce/admin/applications',
        redirect: (context, state) =>
            '${AppRoutes.adminApplications}${state.uri.query.isNotEmpty ? '?${state.uri.query}' : ''}',
      ),
      GoRoute(
        path: AppRoutes.adminApplicationDetail,
        builder: (context, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '') ?? 0;
          return AdminApplicationDetailScreen(applicationId: id);
        },
      ),
      GoRoute(
        path: '/workforce/admin/applications/:id',
        redirect: (context, state) => '/admin/applications/${state.pathParameters['id']}',
      ),
      GoRoute(
        path: AppRoutes.adminServices,
        builder: (context, state) => const AdminPlaceholderScreen(
          title: 'Workforce Services Catalog',
          module: 'Services',
          description: 'Master service categories, pricing matrices, and dispatch prerequisites',
        ),
      ),
      GoRoute(
        path: '/workforce/admin/services',
        redirect: (context, state) => AppRoutes.adminServices,
      ),
      GoRoute(
        path: AppRoutes.adminSkills,
        builder: (context, state) => const AdminSkillsScreen(),
      ),
      GoRoute(
        path: '/workforce/admin/skills',
        redirect: (context, state) => AppRoutes.adminSkills,
      ),
      GoRoute(
        path: AppRoutes.adminJobs,
        builder: (context, state) => const AdminJobsScreen(),
      ),
      GoRoute(
        path: '/workforce/admin/jobs',
        redirect: (context, state) => AppRoutes.adminJobs,
      ),
      GoRoute(
        path: AppRoutes.adminDispatch,
        builder: (context, state) {
          final jobId = state.uri.queryParameters['job_id'] ??
              state.uri.queryParameters['jobId'];
          final tab = int.tryParse(state.uri.queryParameters['tab'] ?? '') ?? 0;
          return AdminDispatchScreen(jobId: jobId, initialTabIndex: tab);
        },
      ),
      GoRoute(
        path: '/workforce/admin/dispatch',
        redirect: (context, state) =>
            '${AppRoutes.adminDispatch}${state.uri.query.isNotEmpty ? '?${state.uri.query}' : ''}',
      ),
      GoRoute(
        path: AppRoutes.adminLiveWorkforce,
        builder: (context, state) => const AdminDispatchScreen(
          initialTabIndex: 1,
        ),
      ),
      GoRoute(
        path: '/workforce/admin/operations',
        redirect: (context, state) => AppRoutes.adminDispatch,
      ),
      GoRoute(
        path: AppRoutes.adminReports,
        builder: (context, state) => const AdminReportsScreen(),
      ),
      GoRoute(
        path: '/workforce/admin/reports',
        redirect: (context, state) => AppRoutes.adminReports,
      ),
      GoRoute(
        path: AppRoutes.adminSettings,
        builder: (context, state) => const AdminPlaceholderScreen(
          title: 'System Settings & Controls',
          module: 'Settings',
          description: 'Tenant parameters, radius rules, and dispatch expiration ring timings',
        ),
      ),
      GoRoute(
        path: '/workforce/admin/settings',
        redirect: (context, state) => AppRoutes.adminSettings,
      ),
      // Admin Finance Routes
      GoRoute(
        path: AppRoutes.adminFinanceWallets,
        builder: (context, state) => const AdminWalletsScreen(),
      ),
      GoRoute(
        path: '/workforce/admin/finance/wallets',
        redirect: (context, state) => AppRoutes.adminFinanceWallets,
      ),
      GoRoute(
        path: AppRoutes.adminFinanceTransactions,
        builder: (context, state) => const AdminTransactionsScreen(),
      ),
      GoRoute(
        path: '/workforce/admin/finance/transactions',
        redirect: (context, state) => AppRoutes.adminFinanceTransactions,
      ),
      GoRoute(
        path: AppRoutes.adminFinanceWithdrawals,
        builder: (context, state) => const AdminWithdrawalsScreen(),
      ),
      GoRoute(
        path: '/workforce/admin/finance/withdrawals',
        redirect: (context, state) => AppRoutes.adminFinanceWithdrawals,
      ),
      GoRoute(
        path: AppRoutes.adminFinanceBankAccounts,
        builder: (context, state) => const AdminBankAccountsScreen(),
      ),
      GoRoute(
        path: '/workforce/admin/finance/bank-accounts',
        redirect: (context, state) => AppRoutes.adminFinanceBankAccounts,
      ),
      // Admin Monitoring Routes
      GoRoute(
        path: AppRoutes.adminMonitoringDatabaseEgress,
        builder: (context, state) => const AdminDatabaseEgressScreen(),
      ),
      GoRoute(
        path: '/workforce/admin/monitoring/database-egress',
        redirect: (context, state) => AppRoutes.adminMonitoringDatabaseEgress,
      ),
      // Employee Earnings Routes
      GoRoute(
        path: AppRoutes.earnings,
        redirect: (context, state) => AppRoutes.earningsWallet,
      ),
      GoRoute(
        path: AppRoutes.earningsWallet,
        builder: (context, state) => const WalletScreen(),
      ),
      GoRoute(
        path: AppRoutes.earningsTransactions,
        builder: (context, state) => const TransactionsScreen(),
      ),
      GoRoute(
        path: AppRoutes.earningsWithdrawals,
        builder: (context, state) => const WithdrawalsScreen(),
      ),
      GoRoute(
        path: AppRoutes.earningsBankAccount,
        builder: (context, state) => const BankAccountsScreen(),
      ),
      // Aliases
      GoRoute(
        path: '/more/finance',
        redirect: (context, state) => AppRoutes.earningsWallet,
      ),
      GoRoute(
        path: '/more/finance/transactions',
        redirect: (context, state) => AppRoutes.earningsTransactions,
      ),
      GoRoute(
        path: '/more/finance/withdrawals',
        redirect: (context, state) => AppRoutes.earningsWithdrawals,
      ),
      GoRoute(
        path: '/more/finance/bank-accounts',
        redirect: (context, state) => AppRoutes.earningsBankAccount,
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            AppShellScaffold(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.home,
                builder: (context, state) => const HomeScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.jobs,
                builder: (context, state) => const JobsScreen(),
                routes: [
                  GoRoute(
                    path: ':id',
                    builder: (context, state) {
                      final id = int.tryParse(state.pathParameters['id'] ?? '') ?? -1;
                      return JobDetailScreen(jobId: id);
                    },
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.notifications,
                builder: (context, state) => const NotificationsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.more,
                builder: (context, state) => const MoreScreen(),
                routes: [
                  GoRoute(
                    path: 'performance',
                    builder: (context, state) => const PerformanceScreen(),
                  ),
                  GoRoute(
                    path: 'profile',
                    builder: (context, state) => const ProfileScreen(),
                  ),
                  GoRoute(
                    path: 'documents',
                    builder: (context, state) => const DocumentsScreen(),
                  ),
                  GoRoute(
                    path: 'services',
                    builder: (context, state) => const ServicesScreen(),
                  ),
                  GoRoute(
                    path: 'locations',
                    builder: (context, state) => const LocationsScreen(),
                  ),
                  GoRoute(
                    path: 'settings',
                    builder: (context, state) => const SettingsScreen(),
                    routes: [
                      GoRoute(
                        path: 'security',
                        builder: (context, state) => const AccountSecurityScreen(),
                      ),
                      GoRoute(
                        path: 'appearance',
                        builder: (context, state) => const AppearanceScreen(),
                      ),
                      GoRoute(
                        path: 'notifications',
                        builder: (context, state) => const NotificationSettingsScreen(),
                      ),
                      GoRoute(
                        path: 'privacy',
                        builder: (context, state) => const PrivacyDataScreen(),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    ],
  );
});

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Verifying session...'),
          ],
        ),
      ),
    );
  }
}
