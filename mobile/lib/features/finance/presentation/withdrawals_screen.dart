import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/finance/data/finance_repository.dart';
import 'package:mobile/features/finance/domain/wallet_withdrawal.dart';
import 'package:mobile/features/finance/presentation/finance_providers.dart';
import 'package:mobile/features/finance/presentation/widgets/request_withdrawal_sheet.dart';
import 'package:mobile/features/finance/presentation/widgets/withdrawal_card.dart';
import 'package:mobile/routing/app_routes.dart';
import 'package:mobile/shared/widgets/app_card.dart';
import 'package:mobile/shared/widgets/empty_state.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';

/// Payout Withdrawals tracking screen for technicians.
///
/// Features:
/// - Breadcrumb: Back to Wallet action.
/// - Screen title: Payouts & Withdrawals
/// - Subtitle: Track payout disbursement status or request a new direct bank withdrawal.
/// - Top actions: Refresh & New Payout Request.
/// - Authoritative Available for Payout card with ₹5,000 minimum threshold.
/// - Withdrawal List showing ID, amount, date, status, masked account, UTR, failure reason.
class WithdrawalsScreen extends ConsumerStatefulWidget {
  const WithdrawalsScreen({super.key});

  @override
  ConsumerState<WithdrawalsScreen> createState() => _WithdrawalsScreenState();
}

class _WithdrawalsScreenState extends ConsumerState<WithdrawalsScreen> {
  bool _isRefreshing = false;

  Future<void> _handleRefresh() async {
    if (_isRefreshing) return;
    setState(() => _isRefreshing = true);
    try {
      ref.invalidate(walletWithdrawalsProvider);
      ref.invalidate(employeeWalletProvider);
      await ref.read(walletWithdrawalsProvider.future);
    } catch (_) {
    } finally {
      if (mounted) {
        setState(() => _isRefreshing = false);
      }
    }
  }

  Future<void> _cancelWithdrawal(WalletWithdrawal withdrawal) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel Withdrawal Request'),
        content: Text(
          'Are you sure you want to cancel the payout request of ₹${withdrawal.amount.toStringAsFixed(2)}? The funds will remain in your available balance.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Keep Request'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFFDC2626),
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Cancel Request'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await ref.read(financeRepositoryProvider).cancelWithdrawal(withdrawal.id);
      ref.invalidate(walletWithdrawalsProvider);
      ref.invalidate(employeeWalletProvider);
      ref.invalidate(walletTransactionsProvider);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Withdrawal #${withdrawal.id} cancelled successfully.'),
            backgroundColor: const Color(0xFF059669),
          ),
        );
      }
    } on DioException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(describeDioError(e, fallback: 'Failed to cancel withdrawal.')),
            backgroundColor: const Color(0xFFE11D48),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final withdrawalsAsync = ref.watch(walletWithdrawalsProvider);
    final walletAsync = ref.watch(employeeWalletProvider);
    final availableBalance = walletAsync.valueOrNull?.availableBalance ?? 0.0;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: const WorkforceAppBar(
        titleText: 'Payouts & Withdrawals',
        showBrand: false,
        showStatusSubBar: false,
      ),
      body: RefreshIndicator(
        onRefresh: _handleRefresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.sm,
            AppSpacing.lg,
            AppSpacing.xxl,
          ),
          children: [
            // ── Breadcrumb: Back to Wallet ──────────────────────────────────
            InkWell(
              onTap: () {
                if (context.canPop()) {
                  context.pop();
                } else {
                  context.go(AppRoutes.earningsWallet);
                }
              },
              borderRadius: BorderRadius.circular(6),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 2),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: const [
                    Icon(Icons.arrow_back_rounded, size: 16, color: Color(0xFF004E89)),
                    SizedBox(width: 4),
                    Text(
                      'Back to Wallet',
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF004E89),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 6),

            // ── Screen Title & Subtitle ─────────────────────────────────────
            const Text(
              'Payouts & Withdrawals',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                color: Color(0xFF0A2540),
              ),
            ),
            const SizedBox(height: 2),
            Text(
              'Track payout disbursement status or request a new direct bank withdrawal.',
              style: TextStyle(
                fontSize: 12,
                color: AppColors.textMuted,
                height: 1.35,
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── Top Actions: [ Refresh ]  [ New Payout Request ] ─────────────
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _isRefreshing ? null : _handleRefresh,
                    icon: _isRefreshing
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.refresh_rounded, size: 16),
                    label: const FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text('Refresh', style: TextStyle(fontWeight: FontWeight.w700)),
                    ),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () => RequestWithdrawalSheet.show(context),
                    icon: const Icon(Icons.add_rounded, size: 16),
                    label: const FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text('New Payout Request', style: TextStyle(fontWeight: FontWeight.w800)),
                    ),
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF004E89),
                      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),

            // ── Available for Payout Card ───────────────────────────────────
            Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: const Color(0xFFECFDF5),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Expanded(
                        child: Text(
                          'Available for Payout',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF065F46),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: const Color(0xFFA7F3D0)),
                        ),
                        child: const Text(
                          '₹5,000 INR Min',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF059669),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '₹${availableBalance.toStringAsFixed(2)}',
                    style: const TextStyle(
                      fontSize: 24,
                      fontFamily: 'monospace',
                      fontWeight: FontWeight.w900,
                      color: Color(0xFF065F46),
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: const [
                      Icon(Icons.bolt_rounded, size: 13, color: Color(0xFF059669)),
                      SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          'Direct NEFT/IMPS transfer to verified bank accounts',
                          style: TextStyle(
                            fontSize: 11,
                            color: Color(0xFF047857),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            // ── Withdrawal Requests Section Header ──────────────────────────
            Row(
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
                const Text(
                  'PAYOUT REQUEST HISTORY',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.8,
                    color: Color(0xFF64748B),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // ── Async Withdrawal Requests List ──────────────────────────────
            withdrawalsAsync.when(
              loading: () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(AppSpacing.xxl),
                  child: CircularProgressIndicator(),
                ),
              ),
              error: (err, _) => Center(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.error_outline_rounded, size: 40, color: Color(0xFFE11D48)),
                      const SizedBox(height: AppSpacing.md),
                      const Text(
                        'Failed to load withdrawals',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        err.toString(),
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                      ),
                      const SizedBox(height: AppSpacing.md),
                      ElevatedButton.icon(
                        onPressed: _handleRefresh,
                        icon: const Icon(Icons.refresh_rounded, size: 16),
                        label: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              ),
              data: (withdrawals) {
                if (withdrawals.isEmpty) {
                  return AppCard(
                    padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
                    child: Column(
                      children: [
                        const EmptyState(
                          icon: Icons.payments_outlined,
                          title: 'No withdrawal requests recorded',
                          message:
                              'When your balance reaches ₹5,000, you can request payouts directly here.',
                        ),
                        const SizedBox(height: AppSpacing.md),
                        FilledButton.icon(
                          onPressed: () => RequestWithdrawalSheet.show(context),
                          icon: const Icon(Icons.add_rounded, size: 16),
                          label: const Text('New Payout Request'),
                          style: FilledButton.styleFrom(
                            backgroundColor: const Color(0xFF004E89),
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                        ),
                      ],
                    ),
                  );
                }

                return Column(
                  children: withdrawals.map((withdrawal) {
                    return WithdrawalCard(
                      withdrawal: withdrawal,
                      onCancel: withdrawal.isCancellable
                          ? () => _cancelWithdrawal(withdrawal)
                          : null,
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
}
