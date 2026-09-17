import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../routing/app_routes.dart';
import '../../../../shared/widgets/workforce_avatar.dart';
import '../../../auth/presentation/auth_controller.dart';

/// The official Admin Navigation Drawer for Workforce Mobile.
/// Provides role-aware, grouped, collapsible navigation matching the SEVO web portal structure:
///
/// Super Admin / Platform Admin:
/// - SEVO Platform / Superadmin Console Header
/// - Platform Dashboard
/// - PLATFORM GOVERNANCE: Vendor Directory, Workforce Roster, Applications Approval, Service Providers
/// - OPERATIONS HUB: AC Estimations, Field Jobs, Dispatch Radar, Skills Master, Scorecards
/// - FINANCE & TREASURY: Platform Treasury, Transactions, Withdrawals, Payout Accounts
/// - TELEMETRY & AUDITS: Database & Egress, Reports & Audits
/// - BOTTOM: System Settings, Log Out
///
/// Vendor Admin / Manager:
/// - SEVO / WORKFORCE ADMIN Header
/// - Home
/// - WORKFORCE: Employees, Applications, Services, Skills
/// - OPERATIONS: Jobs, Dispatch, Live Workforce
/// - FINANCE: Wallets, Transactions, Withdrawals, Bank Accounts
/// - MONITORING: Database & Egress
/// - REPORTS: Reports
/// - SETTINGS: Settings
/// - BOTTOM: Log Out
class AdminDrawer extends ConsumerStatefulWidget {
  const AdminDrawer({super.key});

  @override
  ConsumerState<AdminDrawer> createState() => _AdminDrawerState();
}

class _AdminDrawerState extends ConsumerState<AdminDrawer> {
  // Super Admin Collapsible Group States
  bool _governanceExpanded = true;
  bool _operationsHubExpanded = true;
  bool _financeTreasuryExpanded = true;
  bool _telemetryAuditsExpanded = true;

  // Vendor Admin Collapsible Group States
  bool _workforceExpanded = true;
  bool _operationsExpanded = true;
  bool _financeExpanded = true;
  bool _telemetryExpanded = true;

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final user = authState.user;
    final isSuperAdmin = user?.isSuperAdmin == true;
    final displayName = user?.displayName ?? (isSuperAdmin ? 'Platform Admin' : 'Admin');
    final initial = displayName.isNotEmpty ? displayName[0].toUpperCase() : 'A';
    final email = user?.email ?? '';
    final photoUrl = user?.avatar;

    // Active route detection
    String currentLocation = '';
    try {
      currentLocation = GoRouterState.of(context).matchedLocation;
    } catch (_) {}

    return Drawer(
      backgroundColor: Colors.white,
      child: SafeArea(
        child: Column(
          children: [
            // ── Drawer Header ──────────────────────────────────────────────
            Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xFF0A2540), // Deep Peacock Navy
                    Color(0xFF004E89), // Peacock Blue
                  ],
                ),
                border: Border(bottom: BorderSide(color: Color(0x33004E89))),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.asset(
                          'assets/images/sevo_logo.png',
                          width: 36,
                          height: 36,
                          fit: BoxFit.contain,
                          errorBuilder: (context, error, stackTrace) => Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(
                              color: const Color(0xFF2563EB),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: const Center(
                              child: Icon(
                                Icons.handyman_rounded,
                                color: Colors.white,
                                size: 20,
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              isSuperAdmin ? 'SEVO Platform' : 'SEVO',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 16,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 0.8,
                              ),
                            ),
                            Container(
                              margin: const EdgeInsets.only(top: 2),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 1.5,
                              ),
                              decoration: BoxDecoration(
                                color: isSuperAdmin
                                    ? const Color(0xFFD97706).withValues(alpha: 0.35)
                                    : const Color(0xFF059669).withValues(alpha: 0.35),
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(
                                  color: isSuperAdmin
                                      ? const Color(0xFFFBBF24).withValues(alpha: 0.5)
                                      : const Color(0xFF34D399).withValues(alpha: 0.5),
                                  width: 0.6,
                                ),
                              ),
                              child: Text(
                                isSuperAdmin ? 'Superadmin Console' : 'WORKFORCE ADMIN',
                                style: TextStyle(
                                  color: isSuperAdmin
                                      ? const Color(0xFFFDE68A)
                                      : const Color(0xFF6EE7B7),
                                  fontSize: 8.5,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 0.6,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Row(
                    children: [
                      WorkforceAvatar(
                        imageUrl: photoUrl,
                        name: displayName,
                        initial: initial,
                        radius: 19,
                        fontSize: 14,
                        backgroundColor: Colors.white.withValues(alpha: 0.15),
                        foregroundColor: Colors.white,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              displayName,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                                fontWeight: FontWeight.w800,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            if (email.isNotEmpty)
                              Text(
                                email,
                                style: const TextStyle(
                                  color: Color(0xFFBAE6FD),
                                  fontSize: 11,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 7,
                          vertical: 2.5,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFEF3C7),
                          borderRadius: BorderRadius.circular(5),
                          border: Border.all(color: const Color(0xFFFDE68A), width: 0.8),
                        ),
                        child: Text(
                          isSuperAdmin ? 'SUPERADMIN' : 'ADMIN',
                          style: const TextStyle(
                            color: Color(0xFF92400E),
                            fontSize: 9.5,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 0.4,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // ── Scrollable Menu ────────────────────────────────────────────
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.sm,
                  vertical: AppSpacing.md,
                ),
                children: [
                  if (isSuperAdmin) ...[
                    // ==========================================
                    // SUPER ADMIN NAVIGATION
                    // ==========================================

                    // TOP: Platform Dashboard
                    _DrawerNavItem(
                      icon: Icons.dashboard_rounded,
                      label: 'Platform Dashboard',
                      route: AppRoutes.superAdminDashboard,
                      isActive: currentLocation == AppRoutes.superAdminDashboard ||
                          currentLocation == '/superadmin' ||
                          currentLocation == '/superadmin/home' ||
                          currentLocation == '/superadmin/dashboard' ||
                          currentLocation == '/workforce/admin',
                      onTap: () {
                        Navigator.of(context).pop();
                        context.go(AppRoutes.superAdminDashboard);
                      },
                    ),

                    const SizedBox(height: AppSpacing.sm),
                    const Divider(height: 1),
                    const SizedBox(height: AppSpacing.xs),

                    // 1. PLATFORM GOVERNANCE
                    _DrawerGroupHeader(
                      title: 'PLATFORM GOVERNANCE',
                      isExpanded: _governanceExpanded,
                      onToggle: () =>
                          setState(() => _governanceExpanded = !_governanceExpanded),
                    ),
                    if (_governanceExpanded) ...[
                      _DrawerNavItem(
                        icon: Icons.business_rounded,
                        label: 'Vendor Directory',
                        route: AppRoutes.superAdminVendors,
                        isActive: currentLocation.startsWith('/superadmin/vendors') ||
                            currentLocation.startsWith('/workforce/platform/vendors') ||
                            currentLocation.startsWith('/platform/vendors'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.superAdminVendors);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.groups_rounded,
                        iconColor: const Color(0xFF004E89),
                        label: 'Workforce Roster',
                        route: AppRoutes.superAdminWorkforce,
                        isActive: currentLocation.startsWith('/superadmin/workforce') ||
                            currentLocation.startsWith('/workforce/platform/workforce') ||
                            currentLocation.startsWith('/platform/workforce'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.superAdminWorkforce);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.assignment_ind_rounded,
                        iconColor: const Color(0xFF2563EB),
                        label: 'Applications Approval',
                        route: AppRoutes.superAdminApplications,
                        isActive: currentLocation.startsWith('/superadmin/applications') ||
                            currentLocation.startsWith('/workforce/platform/applications') ||
                            currentLocation.startsWith('/platform/applications'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.superAdminApplications);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.domain_verification_rounded,
                        label: 'Service Providers',
                        route: '/workforce/platform/providers',
                        isActive: currentLocation.startsWith('/workforce/platform/providers'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go('/workforce/platform/providers');
                        },
                      ),
                    ],

                    const SizedBox(height: AppSpacing.sm),
                    const Divider(height: 1),
                    const SizedBox(height: AppSpacing.xs),

                    // 2. OPERATIONS HUB
                    _DrawerGroupHeader(
                      title: 'OPERATIONS HUB',
                      isExpanded: _operationsHubExpanded,
                      onToggle: () =>
                          setState(() => _operationsHubExpanded = !_operationsHubExpanded),
                    ),
                    if (_operationsHubExpanded) ...[
                      _DrawerNavItem(
                        icon: Icons.calculate_rounded,
                        iconColor: const Color(0xFF004E89),
                        label: 'AC Estimations',
                        route: AppRoutes.estimates,
                        isActive: currentLocation == AppRoutes.estimates ||
                            currentLocation.startsWith('/estimates') ||
                            currentLocation.startsWith('/more/estimates') ||
                            currentLocation.startsWith('/admin/estimates'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.estimates);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.fact_check_rounded,
                        iconColor: const Color(0xFF2563EB),
                        label: 'Quotation Approvals',
                        route: AppRoutes.adminQuotationApprovals,
                        isActive: currentLocation.startsWith('/admin/quotations') ||
                            currentLocation.startsWith('/workforce/admin/quotations'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminQuotationApprovals);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.receipt_long_rounded,
                        iconColor: const Color(0xFF0D9488),
                        label: 'Invoices',
                        route: AppRoutes.adminInvoices,
                        isActive: currentLocation.startsWith('/admin/invoices') ||
                            currentLocation.startsWith('/workforce/admin/invoices'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminInvoices);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.work_rounded,
                        label: 'Field Jobs',
                        route: AppRoutes.adminJobs,
                        isActive: currentLocation.startsWith('/admin/jobs') ||
                            currentLocation.startsWith('/workforce/admin/jobs'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminJobs);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.radar_rounded,
                        iconColor: const Color(0xFF059669),
                        label: 'Dispatch Radar',
                        route: AppRoutes.adminDispatch,
                        isActive: currentLocation.startsWith('/admin/dispatch') ||
                            currentLocation.startsWith('/admin/live-workforce') ||
                            currentLocation.startsWith('/workforce/admin/dispatch'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminDispatch);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.military_tech_rounded,
                        label: 'Skills Master',
                        route: AppRoutes.adminSkills,
                        isActive: currentLocation.startsWith('/admin/skills') ||
                            currentLocation.startsWith('/workforce/admin/skills'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminSkills);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.price_change_rounded,
                        iconColor: const Color(0xFF7C3AED),
                        label: 'Pricing Approval',
                        route: AppRoutes.adminPricingApprovals,
                        isActive: currentLocation.startsWith('/admin/pricing-approvals') ||
                            currentLocation.startsWith('/workforce/admin/pricing-approvals'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminPricingApprovals);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.score_rounded,
                        iconColor: const Color(0xFFD97706),
                        label: 'Scorecards',
                        route: AppRoutes.adminScorecards,
                        isActive: currentLocation.startsWith('/admin/scorecards') ||
                            currentLocation.startsWith('/workforce/admin/scorecards') ||
                            currentLocation.startsWith('/performance') ||
                            currentLocation.startsWith('/more/performance'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminScorecards);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.health_and_safety_rounded,
                        iconColor: const Color(0xFF059669),
                        label: 'Social Security',
                        route: AppRoutes.adminSocialSecurity,
                        isActive: currentLocation.startsWith('/admin/social-security') ||
                            currentLocation.startsWith('/workforce/admin/social-security'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminSocialSecurity);
                        },
                      ),
                    ],

                    const SizedBox(height: AppSpacing.sm),
                    const Divider(height: 1),
                    const SizedBox(height: AppSpacing.xs),

                    // 3. FINANCE & TREASURY
                    _DrawerGroupHeader(
                      title: 'FINANCE & TREASURY',
                      isExpanded: _financeTreasuryExpanded,
                      onToggle: () => setState(
                          () => _financeTreasuryExpanded = !_financeTreasuryExpanded),
                    ),
                    if (_financeTreasuryExpanded) ...[
                      _DrawerNavItem(
                        icon: Icons.account_balance_wallet_rounded,
                        iconColor: const Color(0xFF004E89),
                        label: 'Platform Treasury',
                        route: AppRoutes.adminFinanceWallets,
                        isActive: currentLocation.startsWith('/admin/finance/wallets') ||
                            currentLocation.startsWith('/workforce/admin/finance/wallets'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminFinanceWallets);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.receipt_long_rounded,
                        iconColor: const Color(0xFF0D9488),
                        label: 'Transactions',
                        route: AppRoutes.adminFinanceTransactions,
                        isActive: currentLocation.startsWith('/admin/finance/transactions') ||
                            currentLocation.startsWith('/workforce/admin/finance/transactions'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminFinanceTransactions);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.payments_rounded,
                        iconColor: const Color(0xFF059669),
                        label: 'Withdrawals',
                        route: AppRoutes.adminFinanceWithdrawals,
                        isActive: currentLocation.startsWith('/admin/finance/withdrawals') ||
                            currentLocation.startsWith('/workforce/admin/finance/withdrawals'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminFinanceWithdrawals);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.account_balance_rounded,
                        iconColor: const Color(0xFF6366F1),
                        label: 'Payout Accounts',
                        route: AppRoutes.adminFinanceBankAccounts,
                        isActive: currentLocation.startsWith('/admin/finance/bank-accounts') ||
                            currentLocation.startsWith('/workforce/admin/finance/bank-accounts'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminFinanceBankAccounts);
                        },
                      ),
                    ],

                    const SizedBox(height: AppSpacing.sm),
                    const Divider(height: 1),
                    const SizedBox(height: AppSpacing.xs),

                    // 4. TELEMETRY & AUDITS
                    _DrawerGroupHeader(
                      title: 'TELEMETRY & AUDITS',
                      isExpanded: _telemetryAuditsExpanded,
                      onToggle: () => setState(
                          () => _telemetryAuditsExpanded = !_telemetryAuditsExpanded),
                    ),
                    if (_telemetryAuditsExpanded) ...[
                      _DrawerNavItem(
                        icon: Icons.data_usage_rounded,
                        iconColor: const Color(0xFF0284C7),
                        label: 'Database & Egress',
                        route: AppRoutes.adminMonitoringDatabaseEgress,
                        isActive: currentLocation
                                .startsWith('/admin/monitoring/database-egress') ||
                            currentLocation
                                .startsWith('/workforce/admin/monitoring/database-egress'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminMonitoringDatabaseEgress);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.bar_chart_rounded,
                        label: 'Reports & Audits',
                        route: AppRoutes.adminReports,
                        isActive: currentLocation.startsWith('/admin/reports') ||
                            currentLocation.startsWith('/workforce/admin/reports'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminReports);
                        },
                      ),
                    ],
                  ] else ...[
                    // ==========================================
                    // VENDOR ADMIN NAVIGATION
                    // ==========================================

                    // 0. COMPANY HEADER CARD
                    Container(
                      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEFF6FF),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFFBFDBFE)),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 30,
                            height: 30,
                            decoration: BoxDecoration(
                              color: const Color(0xFF004E89),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Icon(
                              Icons.apartment_rounded,
                              color: Colors.white,
                              size: 17,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  user?.companyName ?? 'Vendor Business',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w800,
                                    color: Color(0xFF0A2540),
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                const Text(
                                  'Company Portal',
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w600,
                                    color: Color(0xFF2563EB),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),

                    // 1. COMPANY HOME
                    _DrawerNavItem(
                      icon: Icons.home_rounded,
                      label: 'Company Home',
                      route: AppRoutes.adminHome,
                      isActive: currentLocation == '/admin/home' ||
                          currentLocation == '/workforce/admin' ||
                          currentLocation == AppRoutes.adminHome,
                      onTap: () {
                        Navigator.of(context).pop();
                        context.go(AppRoutes.adminHome);
                      },
                    ),

                    const SizedBox(height: AppSpacing.sm),
                    const Divider(height: 1),
                    const SizedBox(height: AppSpacing.xs),

                    // 2. MY WORKFORCE GROUP
                    _DrawerGroupHeader(
                      title: 'MY WORKFORCE',
                      isExpanded: _workforceExpanded,
                      onToggle: () =>
                          setState(() => _workforceExpanded = !_workforceExpanded),
                    ),
                    if (_workforceExpanded) ...[
                      _DrawerNavItem(
                        icon: Icons.people_alt_rounded,
                        label: 'Tied Technicians',
                        route: AppRoutes.adminTiedTechnicians,
                        isActive: currentLocation.startsWith('/admin/technician-network') ||
                            currentLocation.startsWith('/workforce/admin/technician-network'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminTiedTechnicians);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.mail_outline_rounded,
                        iconColor: const Color(0xFF2563EB),
                        label: 'Send Invitations',
                        route: AppRoutes.adminVendorInvitations,
                        isActive: currentLocation.startsWith('/admin/vendor-invitations') ||
                            currentLocation.startsWith('/workforce/admin/vendor-invitations'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminVendorInvitations);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.how_to_reg_rounded,
                        iconColor: const Color(0xFF004E89),
                        label: 'Employee Roster',
                        route: AppRoutes.adminEmployees,
                        isActive: currentLocation.startsWith('/admin/employees') ||
                            currentLocation.startsWith('/workforce/admin/employees'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminEmployees);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.assignment_ind_rounded,
                        iconColor: const Color(0xFF0D9488),
                        label: 'Applications',
                        route: AppRoutes.adminApplications,
                        isActive: currentLocation.startsWith('/admin/applications') ||
                            currentLocation.startsWith('/workforce/admin/applications'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminApplications);
                        },
                      ),
                    ],

                    const SizedBox(height: AppSpacing.sm),
                    const Divider(height: 1),
                    const SizedBox(height: AppSpacing.xs),

                    // 3. OPERATIONS GROUP
                    _DrawerGroupHeader(
                      title: 'OPERATIONS',
                      isExpanded: _operationsExpanded,
                      onToggle: () =>
                          setState(() => _operationsExpanded = !_operationsExpanded),
                    ),
                    if (_operationsExpanded) ...[
                      _DrawerNavItem(
                        icon: Icons.work_rounded,
                        label: 'Field Jobs',
                        route: AppRoutes.adminJobs,
                        isActive: currentLocation.startsWith('/admin/jobs') ||
                            currentLocation.startsWith('/workforce/admin/jobs'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminJobs);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.send_rounded,
                        iconColor: const Color(0xFF059669),
                        label: 'Dispatch Radar',
                        route: AppRoutes.adminDispatch,
                        isActive: currentLocation.startsWith('/admin/dispatch') ||
                            currentLocation.startsWith('/admin/live-workforce') ||
                            currentLocation.startsWith('/workforce/admin/dispatch'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminDispatch);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.apartment_rounded,
                        iconColor: const Color(0xFF7C3AED),
                        label: 'Company Profile',
                        route: AppRoutes.adminProviderProfile,
                        isActive: currentLocation.startsWith('/admin/provider-profile') ||
                            currentLocation.startsWith('/workforce/admin/provider-profile') ||
                            currentLocation.startsWith('/workforce/provider/profile'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminProviderProfile);
                        },
                      ),
                    ],

                    const SizedBox(height: AppSpacing.sm),
                    const Divider(height: 1),
                    const SizedBox(height: AppSpacing.xs),

                    // 4. FINANCE & LEDGER GROUP
                    _DrawerGroupHeader(
                      title: 'FINANCE & LEDGER',
                      isExpanded: _financeExpanded,
                      onToggle: () => setState(() => _financeExpanded = !_financeExpanded),
                    ),
                    if (_financeExpanded) ...[
                      _DrawerNavItem(
                        icon: Icons.account_balance_wallet_rounded,
                        iconColor: const Color(0xFF004E89),
                        label: 'Company Wallet',
                        route: AppRoutes.adminFinanceWallets,
                        isActive: currentLocation.startsWith('/admin/finance/wallets') ||
                            currentLocation.startsWith('/workforce/admin/finance/wallets'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminFinanceWallets);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.receipt_long_rounded,
                        iconColor: const Color(0xFF0D9488),
                        label: 'Transactions',
                        route: AppRoutes.adminFinanceTransactions,
                        isActive: currentLocation.startsWith('/admin/finance/transactions') ||
                            currentLocation.startsWith('/workforce/admin/finance/transactions'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminFinanceTransactions);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.payments_rounded,
                        iconColor: const Color(0xFF059669),
                        label: 'Withdrawals',
                        route: AppRoutes.adminFinanceWithdrawals,
                        isActive: currentLocation.startsWith('/admin/finance/withdrawals') ||
                            currentLocation.startsWith('/workforce/admin/finance/withdrawals'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminFinanceWithdrawals);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.account_balance_rounded,
                        iconColor: const Color(0xFF6366F1),
                        label: 'Payout Accounts',
                        route: AppRoutes.adminFinanceBankAccounts,
                        isActive: currentLocation.startsWith('/admin/finance/bank-accounts') ||
                            currentLocation.startsWith('/workforce/admin/finance/bank-accounts'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminFinanceBankAccounts);
                        },
                      ),
                    ],

                    const SizedBox(height: AppSpacing.sm),
                    const Divider(height: 1),
                    const SizedBox(height: AppSpacing.xs),

                    // 5. TELEMETRY GROUP
                    _DrawerGroupHeader(
                      title: 'TELEMETRY',
                      isExpanded: _telemetryExpanded,
                      onToggle: () =>
                          setState(() => _telemetryExpanded = !_telemetryExpanded),
                    ),
                    if (_telemetryExpanded) ...[
                      _DrawerNavItem(
                        icon: Icons.data_usage_rounded,
                        iconColor: const Color(0xFF0284C7),
                        label: 'Database & Egress',
                        route: AppRoutes.adminMonitoringDatabaseEgress,
                        isActive: currentLocation
                                .startsWith('/admin/monitoring/database-egress') ||
                            currentLocation
                                .startsWith('/workforce/admin/monitoring/database-egress'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminMonitoringDatabaseEgress);
                        },
                      ),
                      _DrawerNavItem(
                        icon: Icons.bar_chart_rounded,
                        iconColor: const Color(0xFF004E89),
                        label: 'Reports & Audits',
                        route: AppRoutes.adminReports,
                        isActive: currentLocation.startsWith('/admin/reports') ||
                            currentLocation.startsWith('/workforce/admin/reports'),
                        onTap: () {
                          Navigator.of(context).pop();
                          context.go(AppRoutes.adminReports);
                        },
                      ),
                    ],
                  ],
                ],
              ),
            ),

            // ── Drawer Footer: System Settings & Log Out ───────────────────
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm,
                vertical: AppSpacing.xs,
              ),
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: Color(0xFFE2E8F0))),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _DrawerNavItem(
                    icon: Icons.settings_rounded,
                    iconColor: const Color(0xFF64748B),
                    label: 'System Settings',
                    route: isSuperAdmin ? AppRoutes.adminSettings : AppRoutes.adminHome,
                    isActive: isSuperAdmin
                        ? (currentLocation == AppRoutes.adminSettings ||
                            currentLocation.startsWith('/admin/settings') ||
                            currentLocation.startsWith('/workforce/admin/settings'))
                        : false,
                    onTap: () {
                      Navigator.of(context).pop();
                      if (isSuperAdmin) {
                        context.go(AppRoutes.adminSettings);
                      } else {
                        context.go(AppRoutes.adminHome);
                      }
                    },
                  ),
                  ListTile(
                    dense: true,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.card),
                    ),
                    leading: const Icon(Icons.logout_rounded, color: Color(0xFFDC2626), size: 20),
                    title: const Text(
                      'Log Out',
                      style: TextStyle(
                        color: Color(0xFFDC2626),
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                      ),
                    ),
                    onTap: () async {
                      Navigator.of(context).pop();
                      final confirmed = await showDialog<bool>(
                        context: context,
                        builder: (ctx) => AlertDialog(
                          title: const Text('Log Out'),
                          content: const Text('Are you sure you want to log out of Workforce?'),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.of(ctx).pop(false),
                              child: const Text('Cancel'),
                            ),
                            FilledButton(
                              style: FilledButton.styleFrom(
                                backgroundColor: const Color(0xFFDC2626),
                              ),
                              onPressed: () => Navigator.of(ctx).pop(true),
                              child: const Text('Log Out'),
                            ),
                          ],
                        ),
                      );
                      if (confirmed == true) {
                        await ref.read(authControllerProvider.notifier).logout();
                      }
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DrawerGroupHeader extends StatelessWidget {
  const _DrawerGroupHeader({
    required this.title,
    required this.isExpanded,
    required this.onToggle,
  });

  final String title;
  final bool isExpanded;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onToggle,
      borderRadius: BorderRadius.circular(6),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 10.5,
                fontWeight: FontWeight.w800,
                color: Color(0xFF94A3B8),
                letterSpacing: 0.8,
              ),
            ),
            Icon(
              isExpanded ? Icons.keyboard_arrow_down_rounded : Icons.keyboard_arrow_right_rounded,
              size: 16,
              color: const Color(0xFF94A3B8),
            ),
          ],
        ),
      ),
    );
  }
}

class _DrawerNavItem extends StatelessWidget {
  const _DrawerNavItem({
    required this.icon,
    this.iconColor,
    required this.label,
    required this.route,
    required this.isActive,
    required this.onTap,
  });

  final IconData icon;
  final Color? iconColor;
  final String label;
  final String route;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final effectiveIconColor = isActive
        ? const Color(0xFF004E89) // Peacock Blue
        : (iconColor ?? const Color(0xFF64748B));

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 1.5),
      child: Material(
        color: isActive ? const Color(0xFFEFF6FF) : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: onTap,
          child: Container(
            decoration: isActive
                ? const BoxDecoration(
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(8),
                      bottomLeft: Radius.circular(8),
                    ),
                    border: Border(left: BorderSide(color: Color(0xFF004E89), width: 3.5)),
                  )
                : null,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
            child: Row(
              children: [
                Icon(icon, color: effectiveIconColor, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: isActive ? FontWeight.w800 : FontWeight.w600,
                      color: isActive ? const Color(0xFF0A2540) : const Color(0xFF334155),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
