import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../../routing/app_routes.dart';
import '../../../shared/widgets/app_card.dart';
import '../../../shared/widgets/workforce_app_bar.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../jobs/presentation/jobs_providers.dart';
import '../../profile/presentation/profile_providers.dart';

/// The official SEVO Workforce Account & Navigation Hub.
///
/// Features:
/// - Peacock gradient technician hero header with avatar & live presence status.
/// - Quick stats strip (Active Jobs, Completed, Authorized Services).
/// - Modern grouped navigation cards with peacock icon highlights & chevrons.
/// - Clean settings & logout actions.
class MoreScreen extends ConsumerWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    final profileAsync = ref.watch(employeeProfileProvider);
    final activeJobsAsync = ref.watch(activeJobsProvider);
    final completedJobsAsync = ref.watch(completedJobsProvider);

    final displayName = user?.displayName ?? 'Technician';
    final initial = displayName.isNotEmpty ? displayName[0].toUpperCase() : 'T';
    final email = user?.email ?? '';
    final phone = profileAsync.valueOrNull?.displayPhone ?? '';
    final isOnline = profileAsync.valueOrNull?.isOnline ?? false;
    final hasActiveJob = ref.watch(hasActiveJobProvider);
    final servicesCount = profileAsync.valueOrNull?.approvedServices.length ?? 0;

    final statusText = hasActiveJob
        ? 'ON JOB'
        : (isOnline ? 'AVAILABLE' : 'OFFLINE');
    final statusColor = hasActiveJob
        ? const Color(0xFFF59E0B)
        : (isOnline ? const Color(0xFF10B981) : const Color(0xFF94A3B8));

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: const WorkforceAppBar(
        titleText: 'Account Hub',
        showBrand: true,
        showStatusSubBar: false,
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(employeeProfileProvider);
          ref.invalidate(activeJobsProvider);
          ref.invalidate(completedJobsProvider);
          await ref.read(employeeProfileProvider.future);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.md,
            AppSpacing.lg,
            AppSpacing.xxl,
          ),
          children: [
            // ── 1. Peacock Gradient Profile Hero ───────────────────────────
            Container(
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xFF0A2540), // Deep Navy
                    Color(0xFF004E89), // Peacock Blue
                    Color(0xFF065F46), // Emerald
                  ],
                ),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF004E89).withValues(alpha: 0.25),
                    blurRadius: 16,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Stack(
                children: [
                  Positioned(
                    right: -20,
                    top: -20,
                    child: Container(
                      width: 110,
                      height: 110,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white.withValues(alpha: 0.05),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Stack(
                              children: [
                                CircleAvatar(
                                  radius: 28,
                                  backgroundColor: Colors.white.withValues(alpha: 0.2),
                                  child: Text(
                                    initial,
                                    style: const TextStyle(
                                      fontSize: 22,
                                      fontWeight: FontWeight.w900,
                                      color: Colors.white,
                                    ),
                                  ),
                                ),
                                Positioned(
                                  right: 0,
                                  bottom: 0,
                                  child: Container(
                                    width: 14,
                                    height: 14,
                                    decoration: BoxDecoration(
                                      color: statusColor,
                                      shape: BoxShape.circle,
                                      border: Border.all(color: Colors.white, width: 2),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(width: AppSpacing.md),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    displayName,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontSize: 17,
                                      fontWeight: FontWeight.w800,
                                      color: Colors.white,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    email.isNotEmpty ? email : phone,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontSize: 12.5,
                                      color: Colors.white.withValues(alpha: 0.8),
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 2,
                                    ),
                                    decoration: BoxDecoration(
                                      color: statusColor.withValues(alpha: 0.25),
                                      borderRadius: BorderRadius.circular(999),
                                      border: Border.all(
                                        color: statusColor.withValues(alpha: 0.6),
                                        width: 0.8,
                                      ),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Container(
                                          width: 6,
                                          height: 6,
                                          decoration: BoxDecoration(
                                            color: statusColor,
                                            shape: BoxShape.circle,
                                          ),
                                        ),
                                        const SizedBox(width: 5),
                                        Text(
                                          statusText,
                                          style: TextStyle(
                                            fontSize: 10,
                                            fontWeight: FontWeight.w800,
                                            letterSpacing: 0.6,
                                            color: Colors.white,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            IconButton(
                              onPressed: () => context.push('/more/profile'),
                              icon: const Icon(
                                Icons.edit_note_rounded,
                                color: Colors.white,
                                size: 22,
                              ),
                              tooltip: 'Edit Profile',
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.md),
                        Divider(
                          color: Colors.white.withValues(alpha: 0.15),
                          height: 1,
                        ),
                        const SizedBox(height: AppSpacing.md),
                        // Quick Stats Strip
                        Row(
                          children: [
                            _HeroStat(
                              label: 'Active',
                              value: '${activeJobsAsync.valueOrNull?.length ?? 0}',
                              icon: Icons.bolt_rounded,
                            ),
                            Container(
                              width: 1,
                              height: 24,
                              color: Colors.white.withValues(alpha: 0.15),
                            ),
                            _HeroStat(
                              label: 'Completed',
                              value: '${completedJobsAsync.valueOrNull?.length ?? 0}',
                              icon: Icons.task_alt_rounded,
                            ),
                            Container(
                              width: 1,
                              height: 24,
                              color: Colors.white.withValues(alpha: 0.15),
                            ),
                            _HeroStat(
                              label: 'Services',
                              value: '$servicesCount',
                              icon: Icons.build_rounded,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            // ── 2. My Work Section ─────────────────────────────────────────
            _SectionHeader(title: 'MY WORK'),
            const SizedBox(height: 6),
            AppCard(
              padding: EdgeInsets.zero,
              child: Column(
                children: [
                  _NavRow(
                    icon: Icons.work_outline_rounded,
                    iconBg: const Color(0xFF004E89),
                    title: 'Jobs Workspace',
                    subtitle: 'Manage active, completed, and assigned jobs',
                    onTap: () => context.go('/jobs'),
                  ),
                  Divider(color: AppColors.border, height: 1),
                  _NavRow(
                    icon: Icons.insights_rounded,
                    iconBg: const Color(0xFF0D9488),
                    title: 'Performance & Statistics',
                    subtitle: 'Track completion rate, ratings, and stats',
                    onTap: () => context.push('/more/performance'),
                  ),
                ],
              ),
            ),
            // ── 3. Earnings Section ────────────────────────────────────────
            _SectionHeader(title: 'EARNINGS'),
            const SizedBox(height: 6),
            AppCard(
              padding: EdgeInsets.zero,
              child: Column(
                children: [
                  _NavRow(
                    icon: Icons.account_balance_wallet_outlined,
                    iconBg: const Color(0xFF004E89), // Peacock Blue
                    title: 'My Wallet',
                    subtitle: 'Balances, T+7 hold, eligibility & payouts',
                    onTap: () => context.push(AppRoutes.earningsWallet),
                  ),
                  Divider(color: AppColors.border, height: 1),
                  _NavRow(
                    icon: Icons.receipt_long_rounded,
                    iconBg: const Color(0xFF059669), // Emerald
                    title: 'Transactions',
                    subtitle: 'Full double-entry ledger & commissions',
                    onTap: () => context.push(AppRoutes.earningsTransactions),
                  ),
                  Divider(color: AppColors.border, height: 1),
                  _NavRow(
                    icon: Icons.payments_outlined,
                    iconBg: const Color(0xFFD97706), // Amber
                    title: 'Withdrawals',
                    subtitle: 'Payout requests, UTRs & disbursement status',
                    onTap: () => context.push(AppRoutes.earningsWithdrawals),
                  ),
                  Divider(color: AppColors.border, height: 1),
                  _NavRow(
                    icon: Icons.account_balance_outlined,
                    iconBg: const Color(0xFF6366F1), // Indigo
                    title: 'Bank Account',
                    subtitle: 'Manage linked payout destination accounts',
                    onTap: () => context.push(AppRoutes.earningsBankAccount),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            // ── 4. Profile & Credentials Section ───────────────────────────
            _SectionHeader(title: 'PROFILE & CREDENTIALS'),
            const SizedBox(height: 6),
            AppCard(
              padding: EdgeInsets.zero,
              child: Column(
                children: [
                  _NavRow(
                    icon: Icons.person_outline_rounded,
                    iconBg: const Color(0xFF2563EB),
                    title: 'My Profile',
                    subtitle: 'Personal details, bio, language & contact',
                    onTap: () => context.push('/more/profile'),
                  ),
                  Divider(color: AppColors.border, height: 1),
                  _NavRow(
                    icon: Icons.shield_outlined,
                    iconBg: const Color(0xFF059669),
                    title: 'Documents & Verification',
                    subtitle: 'Identity verification, trade licenses & proof',
                    onTap: () => context.push('/more/documents'),
                  ),
                  Divider(color: AppColors.border, height: 1),
                  _NavRow(
                    icon: Icons.handyman_outlined,
                    iconBg: const Color(0xFFD97706),
                    title: 'Authorized Services',
                    subtitle: 'Catalog permissions & requested categories',
                    onTap: () => context.push('/more/services'),
                  ),
                  Divider(color: AppColors.border, height: 1),
                  _NavRow(
                    icon: Icons.location_on_outlined,
                    iconBg: const Color(0xFF6366F1),
                    title: 'Saved Locations',
                    subtitle: 'Dispatch territory, home base & job sites',
                    onTap: () => context.push('/more/locations'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            // ── 4. System & Preferences Section ────────────────────────────
            _SectionHeader(title: 'SYSTEM & PREFERENCES'),
            const SizedBox(height: 6),
            AppCard(
              padding: EdgeInsets.zero,
              child: Column(
                children: [
                  _NavRow(
                    icon: Icons.notifications_none_rounded,
                    iconBg: const Color(0xFF3B82F6),
                    title: 'Notifications',
                    subtitle: 'Dispatch alerts, reminders & updates',
                    onTap: () => context.push('/notifications'),
                  ),
                  Divider(color: AppColors.border, height: 1),
                  _NavRow(
                    icon: Icons.tune_rounded,
                    iconBg: const Color(0xFF64748B),
                    title: 'Settings & Appearance',
                    subtitle: 'Theme, density, motion & preferences',
                    onTap: () => context.push('/more/settings'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.xl),

            // ── 5. Logout Action ───────────────────────────────────────────
            OutlinedButton.icon(
              onPressed: () async {
                final confirmed = await showDialog<bool>(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: const Text('Log Out'),
                    content: const Text(
                      'Are you sure you want to log out of SEVO Workforce?',
                    ),
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
                if (confirmed == true && context.mounted) {
                  await ref.read(authControllerProvider.notifier).logout();
                }
              },
              icon: const Icon(Icons.logout_rounded, color: Color(0xFFDC2626)),
              label: const Text(
                'Log Out',
                style: TextStyle(
                  color: Color(0xFFDC2626),
                  fontWeight: FontWeight.w700,
                  fontSize: 14,
                ),
              ),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Color(0xFFFECDD3)),
                backgroundColor: const Color(0xFFFFF1F2),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.button),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            Center(
              child: Text(
                'SEVO WORKFORCE · v1.0.0',
                style: TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                  color: AppColors.textMuted,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroStat extends StatelessWidget {
  const _HeroStat({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 16, color: const Color(0xFF6EE7B7)),
          const SizedBox(width: 6),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                value,
                style: const TextStyle(
                  fontSize: 14.5,
                  fontWeight: FontWeight.w900,
                  color: Colors.white,
                ),
              ),
              Text(
                label,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: Colors.white.withValues(alpha: 0.75),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 3,
          height: 12,
          margin: const EdgeInsets.only(right: 6),
          decoration: BoxDecoration(
            color: const Color(0xFF004E89),
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        Text(
          title,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.8,
            color: AppColors.textMuted,
          ),
        ),
      ],
    );
  }
}

class _NavRow extends StatelessWidget {
  const _NavRow({
    required this.icon,
    required this.iconBg,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final Color iconBg;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: 14,
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: iconBg.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, size: 19, color: iconBg),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 11.5,
                      color: AppColors.textMuted,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              size: 20,
              color: AppColors.textMuted,
            ),
          ],
        ),
      ),
    );
  }
}

