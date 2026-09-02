import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/finance/data/finance_repository.dart';
import 'package:mobile/features/finance/domain/payout_account.dart';
import 'package:mobile/features/finance/presentation/finance_providers.dart';
import 'package:mobile/features/finance/presentation/widgets/add_bank_account_sheet.dart';
import 'package:mobile/features/finance/presentation/widgets/bank_account_card.dart';
import 'package:mobile/routing/app_routes.dart';
import 'package:mobile/shared/widgets/app_card.dart';
import 'package:mobile/shared/widgets/empty_state.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';

/// Bank accounts management screen for technician payouts.
///
/// Features:
/// - Breadcrumb: Back to Wallet action.
/// - Screen title: Payout Bank Accounts
/// - Subtitle: Manage your linked bank accounts for direct commission withdrawals.
/// - Top actions: Refresh & Add Bank Account (always visible).
/// - Security Banner: Secure Account Masking.
/// - Empty state: No Bank Accounts Linked + Add Bank Account button.
/// - Masked account list (•••• 1234) with deactivate action.
class BankAccountsScreen extends ConsumerStatefulWidget {
  const BankAccountsScreen({super.key});

  @override
  ConsumerState<BankAccountsScreen> createState() => _BankAccountsScreenState();
}

class _BankAccountsScreenState extends ConsumerState<BankAccountsScreen> {
  bool _isRefreshing = false;

  Future<void> _handleRefresh() async {
    if (_isRefreshing) return;
    setState(() => _isRefreshing = true);
    try {
      ref.invalidate(payoutAccountsProvider);
      await ref.read(payoutAccountsProvider.future);
    } catch (_) {
    } finally {
      if (mounted) {
        setState(() => _isRefreshing = false);
      }
    }
  }

  Future<void> _openAddAccount() async {
    final added = await AddBankAccountSheet.show(context);
    if (added == true) {
      ref.invalidate(payoutAccountsProvider);
      ref.invalidate(withdrawalEligibilityProvider);
    }
  }

  Future<void> _deactivateAccount(PayoutAccount account) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Deactivate Bank Account'),
        content: Text(
          'Are you sure you want to remove ${account.bankName} (${account.maskedAccountNumber}) from your payout accounts?',
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
            child: const Text('Deactivate'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await ref.read(financeRepositoryProvider).deactivatePayoutAccount(account.id);
      ref.invalidate(payoutAccountsProvider);
      ref.invalidate(withdrawalEligibilityProvider);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${account.bankName} account deactivated.'),
            backgroundColor: const Color(0xFF059669),
          ),
        );
      }
    } on DioException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(describeDioError(e, fallback: 'Failed to deactivate account.')),
            backgroundColor: const Color(0xFFE11D48),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final accountsAsync = ref.watch(payoutAccountsProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: const WorkforceAppBar(
        titleText: 'Payout Bank Accounts',
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
              'Payout Bank Accounts',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                color: Color(0xFF0A2540),
              ),
            ),
            const SizedBox(height: 2),
            Text(
              'Manage your linked bank accounts for direct commission withdrawals.',
              style: TextStyle(
                fontSize: 12,
                color: AppColors.textMuted,
                height: 1.35,
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── Top Actions: [ Refresh ]  [ Add Bank Account ] ──────────────
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
                    onPressed: _openAddAccount,
                    icon: const Icon(Icons.add_rounded, size: 16),
                    label: const FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text('Add Bank Account', style: TextStyle(fontWeight: FontWeight.w800)),
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

            // ── Security Banner ─────────────────────────────────────────────
            Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: const Color(0xFFEFF6FF),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFBFDBFE)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.shield_outlined,
                    size: 20,
                    color: Color(0xFF1D4ED8),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Secure Account Masking',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF1E40AF),
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          'Full bank account numbers are submitted via encrypted transport and discarded immediately after extracting the last 4 digits.',
                          style: TextStyle(
                            fontSize: 11.5,
                            color: const Color(0xFF1E40AF).withValues(alpha: 0.85),
                            height: 1.35,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            // ── Accounts Section Header ─────────────────────────────────────
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
                  'LINKED PAYOUT ACCOUNTS',
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

            // ── Async Accounts List ─────────────────────────────────────────
            accountsAsync.when(
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
                        'Failed to load bank accounts',
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
              data: (accounts) {
                if (accounts.isEmpty) {
                  return AppCard(
                    padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
                    child: Column(
                      children: [
                        const EmptyState(
                          icon: Icons.account_balance_outlined,
                          title: 'No Bank Accounts Linked',
                          message:
                              'Add a verified bank account to enable self-service payouts.',
                        ),
                        const SizedBox(height: AppSpacing.md),
                        FilledButton.icon(
                          onPressed: _openAddAccount,
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
                  );
                }

                return Column(
                  children: accounts.map((account) {
                    return BankAccountCard(
                      account: account,
                      onDelete: () => _deactivateAccount(account),
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
