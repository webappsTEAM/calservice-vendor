import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/finance/presentation/finance_providers.dart';
import 'package:mobile/features/finance/presentation/widgets/add_bank_account_sheet.dart';
import 'package:mobile/features/finance/presentation/widgets/request_withdrawal_sheet.dart';
import 'package:mobile/features/finance/presentation/widgets/transaction_detail_sheet.dart';
import 'package:mobile/features/finance/presentation/widgets/transaction_list_tile.dart';
import 'package:mobile/routing/app_routes.dart';
import 'package:mobile/shared/widgets/app_card.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';

/// Main Technician Earnings & Wallet Screen.
///
/// Features:
/// - Authoritative 60% job commission earnings, T+7 settlement releases, and bank payouts.
/// - Top action buttons: Refresh and Withdraw Funds.
/// - 4 authoritative summary metric cards (Available, Pending T+7, Lifetime, Withdrawn).
/// - Withdrawal eligibility card with progress toward ₹5,000 threshold.
/// - Recent ledger activity preview with "Full Ledger →" link.
/// - Bank accounts preview with "Add Bank Account" link.
/// - Commission & Payout policy educational card.
class WalletScreen extends ConsumerStatefulWidget {
  const WalletScreen({super.key});

  @override
  ConsumerState<WalletScreen> createState() => _WalletScreenState();
}

class _WalletScreenState extends ConsumerState<WalletScreen> {
  bool _isRefreshing = false;

  Future<void> _handleRefresh() async {
    if (_isRefreshing) return;
    setState(() => _isRefreshing = true);
    try {
      ref.invalidate(employeeWalletProvider);
      ref.invalidate(walletTransactionsProvider);
      ref.invalidate(walletWithdrawalsProvider);
      ref.invalidate(payoutAccountsProvider);
      await ref.read(employeeWalletProvider.future);
    } catch (_) {
    } finally {
      if (mounted) {
        setState(() => _isRefreshing = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final walletAsync = ref.watch(employeeWalletProvider);
    final transactionsAsync = ref.watch(walletTransactionsProvider);
    final accountsAsync = ref.watch(payoutAccountsProvider);
    final eligibility = ref.watch(withdrawalEligibilityProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: const WorkforceAppBar(
        titleText: 'Technician Earnings & Wallet',
        showBrand: false,
        showStatusSubBar: false,
      ),
      body: RefreshIndicator(
        onRefresh: _handleRefresh,
        child: walletAsync.when(
          loading: () => const _WalletLoadingSkeleton(),
          error: (err, _) => _WalletErrorView(
            error: err.toString(),
            onRetry: _handleRefresh,
          ),
          data: (wallet) {
            final recentTransactions = transactionsAsync.valueOrNull?.results ?? [];
            final accounts = accountsAsync.valueOrNull ?? [];

            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.lg,
                AppSpacing.md,
                AppSpacing.lg,
                AppSpacing.xxl,
              ),
              children: [
                // ── Subtitle & Top Actions Row ───────────────────────────────
                Text(
                  'Authoritative 60% job commission earnings, T+7 settlement releases, and bank payouts.',
                  style: TextStyle(
                    fontSize: 12.5,
                    color: AppColors.textMuted,
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: AppSpacing.md),

                // Top Actions: [ Refresh ]  [ Withdraw Funds ]
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _isRefreshing ? null : _handleRefresh,
                        icon: _isRefreshing
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Color(0xFF004E89),
                                ),
                              )
                            : const Icon(Icons.refresh_rounded, size: 16),
                        label: const Text(
                          'Refresh',
                          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                        ),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: () => context.push(AppRoutes.earningsWithdrawals),
                        icon: const Icon(Icons.arrow_outward_rounded, size: 16),
                        label: const Text(
                          'Withdraw Funds',
                          style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                        ),
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFF004E89), // Peacock Blue branding
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.lg),

                // ── 4 Wallet Summary Cards ───────────────────────────────────
                // Row 1: Available Balance & Pending Settlement
                Row(
                  children: [
                    Expanded(
                      child: _SummaryMetricCard(
                        title: 'Available Balance',
                        amount: '₹${wallet.availableBalance.toStringAsFixed(2)}',
                        supportingText: 'Ready for withdrawal (min ₹5,000)',
                        icon: Icons.account_balance_wallet_rounded,
                        iconColor: const Color(0xFF059669),
                        accentBorderColor: const Color(0xFF10B981).withValues(alpha: 0.3),
                        bgColor: const Color(0xFFECFDF5),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _SummaryMetricCard(
                        title: 'Pending Settlement',
                        amount: '₹${wallet.pendingBalance.toStringAsFixed(2)}',
                        supportingText: 'T+7 settlement hold',
                        icon: Icons.hourglass_top_rounded,
                        iconColor: const Color(0xFFD97706),
                        accentBorderColor: const Color(0xFFF59E0B).withValues(alpha: 0.3),
                        bgColor: const Color(0xFFFFFBEB),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),

                // Row 2: Lifetime Commission & Total Withdrawn
                Row(
                  children: [
                    Expanded(
                      child: _SummaryMetricCard(
                        title: 'Lifetime Commission',
                        amount: '₹${wallet.lifetimeEarnings.toStringAsFixed(2)}',
                        supportingText: 'Cumulative 60% earnings',
                        icon: Icons.trending_up_rounded,
                        iconColor: const Color(0xFF004E89),
                        accentBorderColor: const Color(0xFF004E89).withValues(alpha: 0.25),
                        bgColor: const Color(0xFFEFF6FF),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _SummaryMetricCard(
                        title: 'Total Withdrawn',
                        amount: '₹${wallet.totalWithdrawn.toStringAsFixed(2)}',
                        supportingText: 'Disbursed to bank accounts',
                        icon: Icons.outbox_rounded,
                        iconColor: const Color(0xFF4F46E5),
                        accentBorderColor: const Color(0xFF6366F1).withValues(alpha: 0.25),
                        bgColor: const Color(0xFFF5F3FF),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.lg),

                // ── Withdrawal Eligibility Progress Card ─────────────────────
                AppCard(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Row(
                              children: [
                                Icon(
                                  eligibility.isEligible
                                      ? Icons.check_circle_outline_rounded
                                      : Icons.info_outline_rounded,
                                  size: 18,
                                  color: eligibility.isEligible
                                      ? const Color(0xFF059669)
                                      : const Color(0xFFD97706),
                                ),
                                const SizedBox(width: 6),
                                Flexible(
                                  child: Text(
                                    eligibility.isEligible
                                        ? 'Eligible for Payout'
                                        : 'Withdrawal Threshold',
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w800,
                                      color: eligibility.isEligible
                                          ? const Color(0xFF059669)
                                          : const Color(0xFF92400E),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFFEFF6FF),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: const Color(0xFFBFDBFE)),
                            ),
                            child: const Text(
                              '60% Tech Share',
                              style: TextStyle(
                                fontSize: 9.5,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF1D4ED8),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.sm),

                      if (eligibility.isEligible) ...[
                        Text(
                          'You have ₹${wallet.availableBalance.toStringAsFixed(2)} available for instant payout request.',
                          style: TextStyle(
                            fontSize: 12,
                            color: AppColors.textSecondary,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        FilledButton.icon(
                          onPressed: () => RequestWithdrawalSheet.show(context),
                          icon: const Icon(Icons.arrow_outward_rounded, size: 16),
                          label: Text(
                              'Request Payout (₹${wallet.availableBalance.toStringAsFixed(2)})'),
                          style: FilledButton.styleFrom(
                            backgroundColor: const Color(0xFF059669),
                            foregroundColor: Colors.white,
                            minimumSize: const Size.fromHeight(42),
                            textStyle: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                          ),
                        ),
                      ] else ...[
                        // Progress bar towards ₹5,000 min
                        ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: LinearProgressIndicator(
                            value: eligibility.progressRatio,
                            minHeight: 8,
                            backgroundColor: AppColors.border,
                            valueColor:
                                const AlwaysStoppedAnimation<Color>(Color(0xFF004E89)),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              'Available: ₹${wallet.availableBalance.toStringAsFixed(2)}',
                              style: const TextStyle(
                                fontSize: 11,
                                fontFamily: 'monospace',
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const Text(
                              'Min: ₹5,000.00',
                              style: TextStyle(
                                fontSize: 11,
                                fontFamily: 'monospace',
                                fontWeight: FontWeight.w700,
                                color: Color(0xFFD97706),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          eligibility.reason ??
                              'You need ₹${eligibility.shortfall.toStringAsFixed(2)} more to request a withdrawal.',
                          style: TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),

                // ── 5. Recent Ledger Entries Section ─────────────────────────
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Expanded(
                      child: _SectionTitle(title: 'Recent Ledger Entries'),
                    ),
                    TextButton(
                      onPressed: () => context.push(AppRoutes.earningsTransactions),
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 6),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      child: const Text(
                        'Full Ledger →',
                        style: TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF004E89),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),

                if (recentTransactions.isEmpty) ...[
                  AppCard(
                    padding: const EdgeInsets.all(AppSpacing.xl),
                    child: Center(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        child: Text(
                          'No transactions recorded yet. Complete customer jobs to earn commission.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 13,
                            color: AppColors.textMuted,
                            height: 1.4,
                          ),
                        ),
                      ),
                    ),
                  ),
                ] else ...[
                  ...recentTransactions.take(3).map(
                        (txn) => TransactionListTile(
                          transaction: txn,
                          onTap: () => TransactionDetailSheet.show(context, txn),
                        ),
                      ),
                ],
                const SizedBox(height: AppSpacing.lg),

                // ── 6. Bank Accounts Preview Section ─────────────────────────
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Expanded(
                      child: _SectionTitle(title: 'Bank Accounts'),
                    ),
                    TextButton.icon(
                      onPressed: () async {
                        final added = await AddBankAccountSheet.show(context);
                        if (added == true) {
                          ref.invalidate(payoutAccountsProvider);
                          ref.invalidate(withdrawalEligibilityProvider);
                        }
                      },
                      icon: const Icon(Icons.add_rounded, size: 16, color: Color(0xFF004E89)),
                      label: const Text(
                        'Add',
                        style: TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF004E89),
                        ),
                      ),
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 6),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),

                if (accounts.isEmpty) ...[
                  AppCard(
                    padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
                    child: Column(
                      children: [
                        Icon(Icons.account_balance_outlined, size: 36, color: AppColors.textMuted),
                        const SizedBox(height: 8),
                        const Text(
                          'No bank accounts linked',
                          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
                        ),
                        const SizedBox(height: 12),
                        FilledButton.icon(
                          onPressed: () async {
                            final added = await AddBankAccountSheet.show(context);
                            if (added == true) {
                              ref.invalidate(payoutAccountsProvider);
                              ref.invalidate(withdrawalEligibilityProvider);
                            }
                          },
                          icon: const Icon(Icons.add_rounded, size: 16),
                          label: const Text('Add Bank Account'),
                          style: FilledButton.styleFrom(
                            backgroundColor: const Color(0xFF004E89),
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                        ),
                      ],
                    ),
                  ),
                ] else ...[
                  InkWell(
                    onTap: () => context.push(AppRoutes.earningsBankAccount),
                    borderRadius: BorderRadius.circular(12),
                    child: AppCard(
                      padding: const EdgeInsets.all(AppSpacing.md),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: accounts.take(2).map((account) {
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFEFF6FF),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: const Icon(
                                    Icons.account_balance_rounded,
                                    size: 18,
                                    color: Color(0xFF1D4ED8),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        account.bankName,
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w700,
                                          fontSize: 13,
                                        ),
                                      ),
                                      Text(
                                        '${account.accountHolderName} • ${account.maskedAccountNumber}',
                                        style: TextStyle(
                                          fontSize: 11.5,
                                          color: AppColors.textMuted,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                if (account.isVerified)
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 6,
                                      vertical: 2,
                                    ),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFECFDF5),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: const Text(
                                      'VERIFIED',
                                      style: TextStyle(
                                        fontSize: 9.5,
                                        fontWeight: FontWeight.w800,
                                        color: Color(0xFF059669),
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: AppSpacing.lg),

                // ── 7. Commission & Payout Policy Card ───────────────────────
                AppCard(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(
                            Icons.verified_user_outlined,
                            size: 18,
                            color: Color(0xFF004E89),
                          ),
                          const SizedBox(width: 8),
                          const Text(
                            'Commission & Payout Policy',
                            style: TextStyle(
                              fontSize: 13.5,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF0A2540),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      _policyBullet('Technicians receive 60% of gross payment on completed jobs.'),
                      _policyBullet('Company retains 40% covering platform & GST obligations.'),
                      _policyBullet('Settlements move from Pending to Available in 7 days (T+7).'),
                      _policyBullet('Minimum payout threshold: ₹5,000 INR.'),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _policyBullet(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 4, right: 8),
            child: Icon(Icons.circle, size: 5, color: Color(0xFF004E89)),
          ),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontSize: 11.5,
                color: AppColors.textSecondary,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// 2x2 Summary Metric Card with supporting text.
class _SummaryMetricCard extends StatelessWidget {
  const _SummaryMetricCard({
    required this.title,
    required this.amount,
    required this.supportingText,
    required this.icon,
    required this.iconColor,
    required this.accentBorderColor,
    required this.bgColor,
  });

  final String title;
  final String amount;
  final String supportingText;
  final IconData icon;
  final Color iconColor;
  final Color accentBorderColor;
  final Color bgColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accentBorderColor),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textMuted,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.all(5),
                decoration: BoxDecoration(
                  color: bgColor,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Icon(icon, size: 14, color: iconColor),
              ),
            ],
          ),
          const SizedBox(height: 6),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              amount,
              style: const TextStyle(
                fontSize: 20,
                fontFamily: 'monospace',
                fontWeight: FontWeight.w900,
                color: Color(0xFF0A2540),
                letterSpacing: -0.5,
              ),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            supportingText,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 10,
              color: AppColors.textMuted,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
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
        Flexible(
          child: Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
            ),
          ),
        ),
      ],
    );
  }
}

class _WalletLoadingSkeleton extends StatelessWidget {
  const _WalletLoadingSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        Container(
          height: 160,
          decoration: BoxDecoration(
            color: AppColors.border.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(20),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Container(
          height: 100,
          decoration: BoxDecoration(
            color: AppColors.border.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Container(
          height: 180,
          decoration: BoxDecoration(
            color: AppColors.border.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ],
    );
  }
}

class _WalletErrorView extends StatelessWidget {
  const _WalletErrorView({
    required this.error,
    required this.onRetry,
  });

  final String error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.account_balance_wallet_outlined,
              size: 48,
              color: Color(0xFFE11D48),
            ),
            const SizedBox(height: AppSpacing.md),
            const Text(
              'Failed to load wallet data',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(
              error,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: AppColors.textMuted),
            ),
            const SizedBox(height: AppSpacing.lg),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded, size: 16),
              label: const Text('Try Again'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF004E89),
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
