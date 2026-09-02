import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/shared/widgets/async_value_view.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';
import 'package:mobile/features/admin/presentation/widgets/admin_drawer.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/finance/widgets/admin_withdrawal_card.dart';

/// Admin Screen: Technician Payout Requests & Disbursement Processing.
class AdminWithdrawalsScreen extends ConsumerWidget {
  const AdminWithdrawalsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final withdrawalsAsync = ref.watch(adminWithdrawalsProvider);
    final currentStatusFilter = ref.watch(adminWithdrawalStatusFilterProvider);

    return Scaffold(
      appBar: const WorkforceAppBar(
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(adminWithdrawalsProvider);
          await ref.read(adminWithdrawalsProvider.future);
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
            // ── 1. Page Header ───────────────────────────────────────────
            const Text(
              'Technician Payout Requests',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                color: Color(0xFF0A2540),
              ),
            ),
            const SizedBox(height: 3),
            Text(
              'Review and process bank transfer payouts requested by technicians (minimum ₹5,000 threshold).',
              style: TextStyle(
                fontSize: 12,
                color: AppColors.textMuted,
                height: 1.35,
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 2. Status Filter Chips ───────────────────────────────────
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _filterChip(ref, label: 'All Requests', value: 'ALL', current: currentStatusFilter),
                  const SizedBox(width: 6),
                  _filterChip(ref, label: 'Requested', value: 'REQUESTED', current: currentStatusFilter),
                  const SizedBox(width: 6),
                  _filterChip(ref, label: 'Processing', value: 'PROCESSING', current: currentStatusFilter),
                  const SizedBox(width: 6),
                  _filterChip(ref, label: 'Completed', value: 'COMPLETED', current: currentStatusFilter),
                  const SizedBox(width: 6),
                  _filterChip(ref, label: 'Failed', value: 'FAILED', current: currentStatusFilter),
                  const SizedBox(width: 6),
                  _filterChip(ref, label: 'Cancelled', value: 'CANCELLED', current: currentStatusFilter),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 3. Withdrawals List ──────────────────────────────────────
            AsyncValueView<List<dynamic>>(
              value: withdrawalsAsync,
              onRetry: () => ref.invalidate(adminWithdrawalsProvider),
              builder: (context, withdrawals) {
                if (withdrawals.isEmpty) {
                  return Container(
                    padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 20),
                    alignment: Alignment.center,
                    child: Column(
                      children: [
                        Icon(Icons.payments_outlined, size: 48, color: AppColors.textMuted),
                        const SizedBox(height: 12),
                        const Text(
                          'No payout requests found.',
                          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'There are currently no withdrawal requests matching this status.',
                          style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                        ),
                      ],
                    ),
                  );
                }

                return Column(
                  children: withdrawals.map((w) {
                    return AdminWithdrawalCard(withdrawal: w);
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
    required String value,
    required String current,
  }) {
    final isSelected = current == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          ref.read(adminWithdrawalStatusFilterProvider.notifier).state = value;
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
