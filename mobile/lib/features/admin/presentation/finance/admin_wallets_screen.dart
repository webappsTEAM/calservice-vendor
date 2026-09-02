import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/routing/app_routes.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';
import 'package:mobile/features/admin/presentation/widgets/admin_drawer.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/finance/widgets/admin_wallet_card.dart';

/// Admin Screen: Technician Wallets & Financial Oversight.
class AdminWalletsScreen extends ConsumerStatefulWidget {
  const AdminWalletsScreen({super.key});

  @override
  ConsumerState<AdminWalletsScreen> createState() => _AdminWalletsScreenState();
}

class _AdminWalletsScreenState extends ConsumerState<AdminWalletsScreen> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final walletsAsync = ref.watch(adminWalletsProvider);
    final summary = ref.watch(adminWalletSummaryProvider);
    final filteredWallets = ref.watch(filteredAdminWalletsProvider);
    final currentStatusFilter = ref.watch(adminWalletStatusFilterProvider);
    final pendingPayoutsCount = ref.watch(adminPendingWithdrawalsCountProvider);

    return Scaffold(
      appBar: const WorkforceAppBar(
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(adminWalletsProvider);
          ref.invalidate(adminWithdrawalsProvider);
          await ref.read(adminWalletsProvider.future);
        },
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.md,
            AppSpacing.md,
            AppSpacing.md,
            AppSpacing.xxl,
          ),
          children: [
            // ── 1. Page Header & Manage Payouts Action ───────────────────
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Technician Wallets & Financial Oversight',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w900,
                          color: Color(0xFF0A2540),
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        'Monitor technician earnings (60% commission share), pending T+7 settlements, and payout disbursements.',
                        style: TextStyle(
                          fontSize: 12,
                          color: AppColors.textMuted,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),

            // Quick Payout Action Button
            FilledButton.icon(
              onPressed: () => context.push(AppRoutes.adminFinanceWithdrawals),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF004E89),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              icon: const Icon(Icons.payments_rounded, size: 18),
              label: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Manage Payout Requests', style: TextStyle(fontWeight: FontWeight.w800)),
                  if (pendingPayoutsCount > 0) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF59E0B),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        '$pendingPayoutsCount Pending',
                        style: const TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w900,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            // ── 2. Summary Overview Cards ─────────────────────────────────
            if (summary != null) ...[
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth >= 500;
                  final card1 = _SummaryMetricCard(
                    title: 'Technicians with Wallets',
                    value: summary.totalWallets.toString(),
                    subtitle: '${summary.activeWalletsCount} Active • ${summary.lockedWalletsCount} Locked',
                    icon: Icons.people_alt_rounded,
                    iconColor: const Color(0xFF2563EB),
                    iconBgColor: const Color(0xFFEFF6FF),
                  );
                  final card2 = _SummaryMetricCard(
                    title: 'Total Available Balances',
                    value: '₹${summary.totalAvailableBalance.toStringAsFixed(2)}',
                    subtitle: 'Ready for withdrawal',
                    icon: Icons.account_balance_wallet_rounded,
                    iconColor: const Color(0xFF059669),
                    iconBgColor: const Color(0xFFECFDF5),
                  );
                  final card3 = _SummaryMetricCard(
                    title: 'Total in T+7 Hold',
                    value: '₹${summary.totalPendingBalance.toStringAsFixed(2)}',
                    subtitle: 'Pending settlement',
                    icon: Icons.hourglass_top_rounded,
                    iconColor: const Color(0xFFD97706),
                    iconBgColor: const Color(0xFFFFFBEB),
                  );
                  final card4 = _SummaryMetricCard(
                    title: 'Total Disbursed',
                    value: '₹${summary.totalDisbursed.toStringAsFixed(2)}',
                    subtitle: 'Lifetime payouts',
                    icon: Icons.check_circle_rounded,
                    iconColor: const Color(0xFF7C3AED),
                    iconBgColor: const Color(0xFFF5F3FF),
                  );

                  if (isWide) {
                    return Column(
                      children: [
                        Row(children: [Expanded(child: card1), const SizedBox(width: 10), Expanded(child: card2)]),
                        const SizedBox(height: 10),
                        Row(children: [Expanded(child: card3), const SizedBox(width: 10), Expanded(child: card4)]),
                      ],
                    );
                  }

                  return Column(
                    children: [
                      card1,
                      const SizedBox(height: 8),
                      card2,
                      const SizedBox(height: 8),
                      card3,
                      const SizedBox(height: 8),
                      card4,
                    ],
                  );
                },
              ),
              const SizedBox(height: AppSpacing.lg),
            ],

            // ── 3. Search & Filter Bar ────────────────────────────────────
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    onChanged: (val) => ref.read(adminWalletSearchQueryProvider.notifier).state = val,
                    decoration: InputDecoration(
                      hintText: 'Search by technician name or ID...',
                      prefixIcon: const Icon(Icons.search_rounded, size: 18),
                      suffixIcon: _searchController.text.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear_rounded, size: 16),
                              onPressed: () {
                                _searchController.clear();
                                ref.read(adminWalletSearchQueryProvider.notifier).state = '';
                              },
                            )
                          : null,
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),

            // Status Filter Chips
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _filterChip(ref, label: 'All Statuses', filterValue: 'ALL', current: currentStatusFilter),
                  const SizedBox(width: 6),
                  _filterChip(ref, label: 'Active', filterValue: 'ACTIVE', current: currentStatusFilter),
                  const SizedBox(width: 6),
                  _filterChip(ref, label: 'Locked', filterValue: 'LOCKED', current: currentStatusFilter),
                  const SizedBox(width: 6),
                  _filterChip(ref, label: 'Suspended', filterValue: 'SUSPENDED', current: currentStatusFilter),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 4. Technician Wallets List ────────────────────────────────
            walletsAsync.when(
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(vertical: AppSpacing.xxl),
                child: Center(
                  child: SizedBox(
                    width: 28,
                    height: 28,
                    child: CircularProgressIndicator(strokeWidth: 2.5),
                  ),
                ),
              ),
              error: (error, stack) {
                debugPrint('AdminWalletsScreen error: $error\n$stack');
                final message = error is DioException
                    ? describeDioError(error, fallback: 'Failed to load technician wallet data.')
                    : error.toString();

                return Container(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFFECDD3)),
                  ),
                  child: Column(
                    children: [
                      const Icon(Icons.error_outline_rounded, size: 40, color: Color(0xFFE11D48)),
                      const SizedBox(height: AppSpacing.md),
                      const Text(
                        'Failed to load technician wallet data',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        message,
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                      ),
                      const SizedBox(height: AppSpacing.md),
                      FilledButton.icon(
                        onPressed: () => ref.invalidate(adminWalletsProvider),
                        icon: const Icon(Icons.refresh_rounded, size: 16),
                        label: const Text('Retry'),
                        style: FilledButton.styleFrom(backgroundColor: const Color(0xFF004E89)),
                      ),
                    ],
                  ),
                );
              },
              data: (_) {
                if (filteredWallets.isEmpty) {
                  return Container(
                    padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 20),
                    alignment: Alignment.center,
                    child: Column(
                      children: [
                        Icon(Icons.account_balance_wallet_outlined, size: 48, color: AppColors.textMuted),
                        const SizedBox(height: 12),
                        const Text(
                          'No technician wallets match your filter.',
                          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Try clearing search or changing status filter.',
                          style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                        ),
                      ],
                    ),
                  );
                }

                return Column(
                  children: filteredWallets.map((wallet) {
                    return AdminWalletCard(
                      wallet: wallet,
                      onViewTransactions: () {
                        ref.read(adminSelectedTechnicianProvider.notifier).state = wallet;
                        context.push(AppRoutes.adminFinanceTransactions);
                      },
                    );
                  }).toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _filterChip(
    WidgetRef ref, {
    required String label,
    required String filterValue,
    required String current,
  }) {
    final isSelected = current == filterValue;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          ref.read(adminWalletStatusFilterProvider.notifier).state = filterValue;
        }
      },
      selectedColor: const Color(0xFF004E89),
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
        color: isSelected ? Colors.white : const Color(0xFF475569),
      ),
      backgroundColor: AppColors.surfaceMuted,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    );
  }
}

class _SummaryMetricCard extends StatelessWidget {
  const _SummaryMetricCard({
    required this.title,
    required this.value,
    required this.subtitle,
    required this.icon,
    required this.iconColor,
    required this.iconBgColor,
  });

  final String title;
  final String value;
  final String subtitle;
  final IconData icon;
  final Color iconColor;
  final Color iconBgColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: iconBgColor,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 20, color: iconColor),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textMuted),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 1),
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 15,
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.w900,
                    color: Color(0xFF0F172A),
                  ),
                ),
                Text(
                  subtitle,
                  style: TextStyle(fontSize: 10.5, color: AppColors.textMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
