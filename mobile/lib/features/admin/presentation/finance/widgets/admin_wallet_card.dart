import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/data/admin_finance_repository.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/finance/widgets/admin_adjustment_dialog.dart';

/// Card component for an individual technician wallet on the Admin Wallets screen.
class AdminWalletCard extends ConsumerWidget {
  const AdminWalletCard({
    super.key,
    required this.wallet,
    this.onViewTransactions,
  });

  final AdminWallet wallet;
  final VoidCallback? onViewTransactions;

  Color _statusColor(String status) {
    switch (status) {
      case 'ACTIVE':
        return const Color(0xFF059669); // Emerald
      case 'LOCKED':
        return const Color(0xFFDC2626); // Rose
      case 'SUSPENDED':
        return const Color(0xFFD97706); // Amber
      case 'CLOSED':
      default:
        return const Color(0xFF64748B); // Slate
    }
  }

  Future<void> _toggleLock(BuildContext context, WidgetRef ref) async {
    final isCurrentlyActive = wallet.isActive;
    final targetStatus = isCurrentlyActive ? 'LOCKED' : 'ACTIVE';
    final actionName = isCurrentlyActive ? 'Lock' : 'Unlock';

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('$actionName Technician Wallet'),
        content: Text(
          isCurrentlyActive
              ? 'Are you sure you want to lock the wallet for ${wallet.employeeName}? The technician will not be able to request withdrawals or receive automatic payout releases.'
              : 'Unlock wallet for ${wallet.employeeName} to restore standard operational status?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: isCurrentlyActive ? const Color(0xFFDC2626) : const Color(0xFF059669),
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(actionName),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await ref.read(adminFinanceRepositoryProvider).updateWalletStatus(
              employeeId: wallet.employeeId,
              status: targetStatus,
              reason: 'Admin $actionName via mobile app',
            );
        ref.invalidate(adminWalletsProvider);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Wallet for ${wallet.employeeName} is now $targetStatus.')),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to update status: $e')),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusColor = _statusColor(wallet.status);

    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: wallet.isLocked
              ? const Color(0xFFFECDD3)
              : AppColors.border,
          width: wallet.isLocked ? 1.2 : 1.0,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── 1. Header: Technician Info & Status Badge ─────────────────
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 18,
                        backgroundColor: const Color(0xFF004E89).withValues(alpha: 0.1),
                        child: Text(
                          wallet.employeeName.isNotEmpty
                              ? wallet.employeeName[0].toUpperCase()
                              : 'T',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF004E89),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              wallet.employeeName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 14.5,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'EMP-${wallet.employeeId}  •  ${wallet.currency}',
                              style: TextStyle(
                                fontSize: 11.5,
                                fontFamily: 'monospace',
                                color: AppColors.textMuted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: statusColor.withValues(alpha: 0.35), width: 0.8),
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
                        wallet.statusDisplay,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: statusColor,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Divider(color: AppColors.border, height: 1),
            const SizedBox(height: AppSpacing.md),

            // ── 2. Available Balance Highlight ────────────────────────────
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Available Balance',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textMuted,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '₹${wallet.availableBalance.toStringAsFixed(2)}',
                      style: const TextStyle(
                        fontSize: 18,
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w900,
                        color: Color(0xFF004E89),
                      ),
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'Pending (T+7 Hold)',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textMuted,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '₹${wallet.pendingBalance.toStringAsFixed(2)}',
                      style: const TextStyle(
                        fontSize: 14.5,
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w800,
                        color: Color(0xFFD97706),
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),

            // ── 3. Lifetime & Disbursed Metrics ───────────────────────────
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.surfaceMuted,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Lifetime Earnings',
                          style: TextStyle(fontSize: 10.5, color: AppColors.textMuted),
                        ),
                        const SizedBox(height: 1),
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            '₹${wallet.lifetimeEarnings.toStringAsFixed(0)}',
                            style: const TextStyle(
                              fontSize: 13,
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF059669),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(width: 1, height: 24, color: AppColors.border),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Total Withdrawn',
                          style: TextStyle(fontSize: 10.5, color: AppColors.textMuted),
                        ),
                        const SizedBox(height: 1),
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            '₹${wallet.totalWithdrawn.toStringAsFixed(0)}',
                            style: const TextStyle(
                              fontSize: 13,
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF2563EB),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 4. Action Buttons ─────────────────────────────────────────
            Row(
              children: [
                // Manual Adjustment
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => AdminAdjustmentDialog.show(context, wallet),
                    icon: const Icon(Icons.tune_rounded, size: 14),
                    label: const Text('Adjust', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                      minimumSize: const Size(0, 36),
                    ),
                  ),
                ),
                const SizedBox(width: 8),

                // Lock / Unlock
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _toggleLock(context, ref),
                    icon: Icon(
                      wallet.isLocked ? Icons.lock_open_rounded : Icons.lock_outline_rounded,
                      size: 14,
                      color: wallet.isLocked ? const Color(0xFF059669) : const Color(0xFFDC2626),
                    ),
                    label: Text(
                      wallet.isLocked ? 'Unlock' : 'Lock',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: wallet.isLocked ? const Color(0xFF059669) : const Color(0xFFDC2626),
                      ),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(
                        color: wallet.isLocked ? const Color(0xFFA7F3D0) : const Color(0xFFFECDD3),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                      minimumSize: const Size(0, 36),
                    ),
                  ),
                ),
                const SizedBox(width: 8),

                // Ledger / Transactions
                if (onViewTransactions != null)
                  FilledButton(
                    onPressed: onViewTransactions,
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF004E89),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      minimumSize: const Size(0, 36),
                    ),
                    child: const Text('Ledger', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
