import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/data/admin_finance_repository.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/finance/widgets/admin_complete_payout_dialog.dart';
import 'package:mobile/features/admin/presentation/finance/widgets/admin_fail_payout_dialog.dart';

/// Card component representing a technician payout withdrawal request.
class AdminWithdrawalCard extends ConsumerWidget {
  const AdminWithdrawalCard({
    super.key,
    required this.withdrawal,
  });

  final AdminWithdrawal withdrawal;

  Color _statusColor(String status) {
    switch (status) {
      case 'COMPLETED':
        return const Color(0xFF059669); // Emerald
      case 'PROCESSING':
        return const Color(0xFF2563EB); // Blue
      case 'REQUESTED':
        return const Color(0xFFD97706); // Amber
      case 'FAILED':
        return const Color(0xFFDC2626); // Rose
      case 'CANCELLED':
      default:
        return const Color(0xFF64748B); // Slate
    }
  }

  Future<void> _startProcessing(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Start Processing Payout'),
        content: Text(
          'Mark payout #${withdrawal.id} for ${withdrawal.employeeName} (₹${withdrawal.amount.toStringAsFixed(2)}) as PROCESSING?\n\nThis indicates you have initiated the NEFT/IMPS bank transfer.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFF2563EB)),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Start Processing'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await ref.read(adminFinanceRepositoryProvider).startProcessingWithdrawal(withdrawal.id);
        ref.invalidate(adminWithdrawalsProvider);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Payout #${withdrawal.id} is now PROCESSING.')),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to process payout: $e')),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusColor = _statusColor(withdrawal.status);
    final account = withdrawal.payoutAccountDisplay;

    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: withdrawal.isRequested
              ? const Color(0xFFFDE68A)
              : (withdrawal.isProcessing ? const Color(0xFFBFDBFE) : AppColors.border),
          width: (withdrawal.isRequested || withdrawal.isProcessing) ? 1.2 : 1.0,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── 1. Header: Request ID & Status Badge ─────────────────────
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceMuted,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Text(
                        'REQ #${withdrawal.id}',
                        style: const TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w800,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ),
                    if (withdrawal.requestedAt != null) ...[
                      const SizedBox(width: 8),
                      Text(
                        '${withdrawal.requestedAt!.day}/${withdrawal.requestedAt!.month}/${withdrawal.requestedAt!.year}',
                        style: TextStyle(fontSize: 11, color: AppColors.textMuted),
                      ),
                    ],
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: statusColor.withValues(alpha: 0.35), width: 0.8),
                  ),
                  child: Text(
                    withdrawal.statusDisplay,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: statusColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),

            // ── 2. Technician & Amount Row ───────────────────────────────
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        withdrawal.employeeName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      if (withdrawal.employeeId != null)
                        Text(
                          'EMP-${withdrawal.employeeId}',
                          style: TextStyle(
                            fontSize: 11.5,
                            fontFamily: 'monospace',
                            color: AppColors.textMuted,
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  '₹${withdrawal.amount.toStringAsFixed(2)}',
                  style: const TextStyle(
                    fontSize: 20,
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.w900,
                    color: Color(0xFF004E89),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),

            // ── 3. Bank Account Details Box ──────────────────────────────
            Container(
              padding: const EdgeInsets.all(AppSpacing.sm),
              decoration: BoxDecoration(
                color: AppColors.surfaceMuted,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.account_balance_rounded, size: 15, color: Color(0xFF004E89)),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          account?.bankName ?? 'Direct Bank Transfer',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                        ),
                      ),
                      Text(
                        account?.maskedAccountDisplay ?? '••••',
                        style: const TextStyle(
                          fontSize: 12,
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                  if (account?.accountHolderName != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      'Payee: ${account!.accountHolderName}',
                      style: TextStyle(fontSize: 11, color: AppColors.textMuted),
                    ),
                  ],
                ],
              ),
            ),

            // ── 4. UTR / Failure Reason Notice ───────────────────────────
            if (withdrawal.isCompleted && withdrawal.bankTransactionId != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFFECFDF5),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFFA7F3D0)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.check_circle_rounded, size: 14, color: Color(0xFF059669)),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'UTR / Bank Ref: ${withdrawal.bankTransactionId}',
                        style: const TextStyle(
                          fontSize: 11.5,
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF065F46),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            if (withdrawal.isFailed && withdrawal.failureReason != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFF1F2),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFFFECDD3)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.error_outline_rounded, size: 14, color: Color(0xFFDC2626)),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'Reason: ${withdrawal.failureReason}',
                        style: const TextStyle(fontSize: 11.5, color: Color(0xFF9F1239)),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // ── 5. Operational Action Buttons ────────────────────────────
            if (withdrawal.isRequested) ...[
              const SizedBox(height: AppSpacing.md),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => AdminFailPayoutDialog.show(context, withdrawal),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: const Color(0xFFDC2626),
                        side: const BorderSide(color: Color(0xFFFECDD3)),
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        minimumSize: const Size(0, 36),
                      ),
                      child: const Text('Reject / Fail', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    flex: 2,
                    child: FilledButton.icon(
                      onPressed: () => _startProcessing(context, ref),
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFF2563EB),
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        minimumSize: const Size(0, 36),
                      ),
                      icon: const Icon(Icons.sync_rounded, size: 14),
                      label: const Text('Start Processing', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                    ),
                  ),
                ],
              ),
            ] else if (withdrawal.isProcessing) ...[
              const SizedBox(height: AppSpacing.md),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => AdminFailPayoutDialog.show(context, withdrawal),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: const Color(0xFFDC2626),
                        side: const BorderSide(color: Color(0xFFFECDD3)),
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        minimumSize: const Size(0, 36),
                      ),
                      child: const Text('Mark Failed', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    flex: 2,
                    child: FilledButton.icon(
                      onPressed: () => AdminCompletePayoutDialog.show(context, withdrawal),
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFF059669),
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        minimumSize: const Size(0, 36),
                      ),
                      icon: const Icon(Icons.check_circle_rounded, size: 14),
                      label: const Text('Complete Payout (UTR)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
