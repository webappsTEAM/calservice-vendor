import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/data/admin_finance_repository.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/finance/widgets/admin_adjustment_dialog.dart';
import 'package:mobile/routing/app_routes.dart';
import 'package:mobile/shared/widgets/workforce_avatar.dart';

/// Card component for an individual technician wallet on the Admin Wallets screen.
class AdminWalletCard extends ConsumerWidget {
  const AdminWalletCard({
    super.key,
    required this.wallet,
    this.onViewTransactions,
    this.onViewDetails,
  });

  final AdminWallet wallet;
  final VoidCallback? onViewTransactions;
  final VoidCallback? onViewDetails;

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
              backgroundColor: isCurrentlyActive
                  ? const Color(0xFFDC2626)
                  : const Color(0xFF059669),
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
            SnackBar(
              content:
                  Text('Wallet for ${wallet.employeeName} is now $targetStatus.'),
              backgroundColor: const Color(0xFF059669),
            ),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Failed to update status: $e'),
              backgroundColor: const Color(0xFFDC2626),
            ),
          );
        }
      }
    }
  }

  void _showDetailSheet(BuildContext context, WidgetRef ref) {
    final statusColor = _statusColor(wallet.status);

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        padding: const EdgeInsets.all(AppSpacing.lg),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: SafeArea(
          top: false,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Handle Bar
                Center(
                  child: Container(
                    width: 36,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: AppSpacing.md),
                    decoration: BoxDecoration(
                      color: const Color(0xFFCBD5E1),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),

                // Technician Info Header
                Row(
                  children: [
                    WorkforceAvatar(
                      imageUrl: wallet.employeeAvatar,
                      name: wallet.employeeName,
                      initial: wallet.employeeName.isNotEmpty
                          ? wallet.employeeName[0].toUpperCase()
                          : 'T',
                      radius: 24,
                      fontSize: 16,
                      backgroundColor:
                          const Color(0xFF004E89).withValues(alpha: 0.1),
                      foregroundColor: const Color(0xFF004E89),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            wallet.employeeName,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                              color: Color(0xFF0F172A),
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'Technician ID: #${wallet.employeeId} · ${wallet.currency}',
                            style: const TextStyle(
                              fontSize: 12,
                              fontFamily: 'monospace',
                              color: Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(
                            color: statusColor.withValues(alpha: 0.35),
                            width: 0.8),
                      ),
                      child: Text(
                        wallet.statusDisplay,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: statusColor,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                const Divider(height: 1, color: Color(0xFFF1F5F9)),
                const SizedBox(height: AppSpacing.md),

                // Financial Summary
                const Text(
                  'Financial Summary',
                  style: TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 10),

                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: Column(
                    children: [
                      _sheetRow('Available Balance',
                          '₹${wallet.availableBalance.toStringAsFixed(2)}',
                          isBold: true, valueColor: const Color(0xFF004E89)),
                      const Divider(height: 14, color: Color(0xFFE2E8F0)),
                      _sheetRow('T+7 Pending Hold',
                          '₹${wallet.pendingBalance.toStringAsFixed(2)}',
                          valueColor: const Color(0xFFD97706)),
                      const Divider(height: 14, color: Color(0xFFE2E8F0)),
                      _sheetRow('Total Earned (Lifetime)',
                          '₹${wallet.lifetimeEarnings.toStringAsFixed(2)}',
                          valueColor: const Color(0xFF059669)),
                      const Divider(height: 14, color: Color(0xFFE2E8F0)),
                      _sheetRow('Total Withdrawn',
                          '₹${wallet.totalWithdrawn.toStringAsFixed(2)}',
                          valueColor: const Color(0xFF2563EB)),
                      if (wallet.outstandingRecovery > 0) ...[
                        const Divider(height: 14, color: Color(0xFFE2E8F0)),
                        _sheetRow('Outstanding Recovery',
                            '₹${wallet.outstandingRecovery.toStringAsFixed(2)}',
                            valueColor: const Color(0xFFDC2626)),
                      ],
                      if (wallet.nextSettlementDate != null) ...[
                        const Divider(height: 14, color: Color(0xFFE2E8F0)),
                        _sheetRow(
                          'Next Settlement Date',
                          '${wallet.nextSettlementDate!.day.toString().padLeft(2, '0')}/${wallet.nextSettlementDate!.month.toString().padLeft(2, '0')}/${wallet.nextSettlementDate!.year}',
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),

                // Quick Actions
                const Text(
                  'Quick Actions',
                  style: TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 10),

                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          Navigator.of(ctx).pop();
                          ref
                              .read(adminSelectedTechnicianProvider.notifier)
                              .state = wallet;
                          context.push(AppRoutes.adminFinanceTransactions);
                        },
                        icon: const Icon(Icons.receipt_long_rounded, size: 16),
                        label: const Text('Transactions'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFF0F172A),
                          side: const BorderSide(color: Color(0xFFCBD5E1)),
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          textStyle: const TextStyle(
                              fontSize: 12, fontWeight: FontWeight.w700),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          Navigator.of(ctx).pop();
                          context.push(AppRoutes.adminFinanceWithdrawals);
                        },
                        icon: const Icon(Icons.payments_rounded, size: 16),
                        label: const Text('Withdrawals'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFF0F172A),
                          side: const BorderSide(color: Color(0xFFCBD5E1)),
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          textStyle: const TextStyle(
                              fontSize: 12, fontWeight: FontWeight.w700),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          Navigator.of(ctx).pop();
                          AdminAdjustmentDialog.show(context, wallet);
                        },
                        icon: const Icon(Icons.tune_rounded, size: 16),
                        label: const Text('Adjust Balance'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFF0F172A),
                          side: const BorderSide(color: Color(0xFFCBD5E1)),
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          textStyle: const TextStyle(
                              fontSize: 12, fontWeight: FontWeight.w700),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          Navigator.of(ctx).pop();
                          _toggleLock(context, ref);
                        },
                        icon: Icon(
                          wallet.isLocked
                              ? Icons.lock_open_rounded
                              : Icons.lock_outline_rounded,
                          size: 16,
                          color: wallet.isLocked
                              ? const Color(0xFF059669)
                              : const Color(0xFFDC2626),
                        ),
                        label: Text(
                          wallet.isLocked ? 'Unlock Wallet' : 'Lock Wallet',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: wallet.isLocked
                                ? const Color(0xFF059669)
                                : const Color(0xFFDC2626),
                          ),
                        ),
                        style: OutlinedButton.styleFrom(
                          side: BorderSide(
                            color: wallet.isLocked
                                ? const Color(0xFFA7F3D0)
                                : const Color(0xFFFECDD3),
                          ),
                          padding: const EdgeInsets.symmetric(vertical: 10),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _sheetRow(String label, String value,
      {bool isBold = false, Color? valueColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: Color(0xFF64748B),
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          value,
          style: TextStyle(
            fontSize: isBold ? 14 : 12.5,
            fontFamily: 'monospace',
            fontWeight: isBold ? FontWeight.w900 : FontWeight.w700,
            color: valueColor ?? const Color(0xFF0F172A),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusColor = _statusColor(wallet.status);

    return InkWell(
      onTap: onViewDetails ?? () => _showDetailSheet(context, ref),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        margin: const EdgeInsets.only(bottom: AppSpacing.md),
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: wallet.isLocked
                ? const Color(0xFFFECDD3)
                : const Color(0xFFE2E8F0),
            width: wallet.isLocked ? 1.2 : 1.0,
          ),
          boxShadow: const [
            BoxShadow(
              color: Color(0x040F172A),
              blurRadius: 6,
              offset: Offset(0, 2),
            ),
          ],
        ),
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
                      WorkforceAvatar(
                        imageUrl: wallet.employeeAvatar,
                        name: wallet.employeeName,
                        initial: wallet.employeeName.isNotEmpty
                            ? wallet.employeeName[0].toUpperCase()
                            : 'T',
                        radius: 18,
                        fontSize: 14,
                        backgroundColor:
                            const Color(0xFF004E89).withValues(alpha: 0.1),
                        foregroundColor: const Color(0xFF004E89),
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
                                color: Color(0xFF0F172A),
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'EMP-${wallet.employeeId}  •  ${wallet.currency}',
                              style: const TextStyle(
                                fontSize: 11.5,
                                fontFamily: 'monospace',
                                color: Color(0xFF64748B),
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
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                        color: statusColor.withValues(alpha: 0.35),
                        width: 0.8),
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
            const Divider(color: Color(0xFFF1F5F9), height: 1),
            const SizedBox(height: AppSpacing.md),

            // ── 2. Available Balance & T+7 Pending ─────────────────────────
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Available Balance',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF64748B),
                        ),
                      ),
                      const SizedBox(height: 2),
                      FittedBox(
                        fit: BoxFit.scaleDown,
                        alignment: Alignment.centerLeft,
                        child: Text(
                          '₹${wallet.availableBalance.toStringAsFixed(2)}',
                          style: const TextStyle(
                            fontSize: 17,
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w900,
                            color: Color(0xFF004E89),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      const Text(
                        'T+7 Pending',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF64748B),
                        ),
                      ),
                      const SizedBox(height: 2),
                      FittedBox(
                        fit: BoxFit.scaleDown,
                        alignment: Alignment.centerRight,
                        child: Text(
                          '₹${wallet.pendingBalance.toStringAsFixed(2)}',
                          style: const TextStyle(
                            fontSize: 15,
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w800,
                            color: Color(0xFFD97706),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),

            // ── 3. Total Earned & Total Withdrawn Metrics ─────────────────
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Total Earned',
                          style: TextStyle(
                              fontSize: 10.5, color: Color(0xFF64748B)),
                        ),
                        const SizedBox(height: 1),
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            '₹${wallet.lifetimeEarnings.toStringAsFixed(2)}',
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF059669),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                      width: 1, height: 24, color: const Color(0xFFE2E8F0)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Total Withdrawn',
                          style: TextStyle(
                              fontSize: 10.5, color: Color(0xFF64748B)),
                        ),
                        const SizedBox(height: 1),
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            '₹${wallet.totalWithdrawn.toStringAsFixed(2)}',
                            style: const TextStyle(
                              fontSize: 12.5,
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
                // View Details
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed:
                        onViewDetails ?? () => _showDetailSheet(context, ref),
                    icon: const Icon(Icons.info_outline_rounded, size: 14),
                    label: const Text(
                      'View Details',
                      style:
                          TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                    ),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF0F172A),
                      side: const BorderSide(color: Color(0xFFCBD5E1)),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 8),
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
                      wallet.isLocked
                          ? Icons.lock_open_rounded
                          : Icons.lock_outline_rounded,
                      size: 14,
                      color: wallet.isLocked
                          ? const Color(0xFF059669)
                          : const Color(0xFFDC2626),
                    ),
                    label: Text(
                      wallet.isLocked ? 'Unlock' : 'Lock',
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w700,
                        color: wallet.isLocked
                            ? const Color(0xFF059669)
                            : const Color(0xFFDC2626),
                      ),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(
                        color: wallet.isLocked
                            ? const Color(0xFFA7F3D0)
                            : const Color(0xFFFECDD3),
                      ),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 8),
                      minimumSize: const Size(0, 36),
                    ),
                  ),
                ),
                const SizedBox(width: 8),

                // Transactions / Ledger
                Expanded(
                  child: FilledButton(
                    onPressed: onViewTransactions ??
                        () {
                          ref
                              .read(adminSelectedTechnicianProvider.notifier)
                              .state = wallet;
                          context.push(AppRoutes.adminFinanceTransactions);
                        },
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF004E89),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 8),
                      minimumSize: const Size(0, 36),
                    ),
                    child: const Text(
                      'Ledger',
                      style: TextStyle(
                          fontSize: 11.5, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

