import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/finance/widgets/admin_add_bank_account_sheet.dart';
import 'package:mobile/features/admin/presentation/finance/widgets/admin_bank_account_card.dart';
import 'package:mobile/features/admin/presentation/widgets/admin_drawer.dart';
import 'package:mobile/shared/widgets/async_value_view.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';

/// Admin Screen: Bank Accounts verification & disbursement destinations.
class AdminBankAccountsScreen extends ConsumerStatefulWidget {
  const AdminBankAccountsScreen({super.key});

  @override
  ConsumerState<AdminBankAccountsScreen> createState() => _AdminBankAccountsScreenState();
}

class _AdminBankAccountsScreenState extends ConsumerState<AdminBankAccountsScreen> {
  String _statusFilter = 'ALL';

  @override
  Widget build(BuildContext context) {
    final accountsAsync = ref.watch(adminBankAccountsProvider);

    return Scaffold(
      appBar: const WorkforceAppBar(
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(adminBankAccountsProvider);
          await ref.read(adminBankAccountsProvider.future);
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
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Bank Accounts',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w900,
                          color: Color(0xFF0A2540),
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        'Payout accounts for withdrawal disbursement',
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

            // ── Prominent Primary Add Account Button ─────────────────────
            FilledButton.icon(
              onPressed: () => AdminAddBankAccountSheet.show(context),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF004E89), // Peacock Blue branding
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              icon: const Icon(Icons.add_rounded, size: 20),
              label: const Text(
                '+ Add Account',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5),
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 2. Filter Chips ──────────────────────────────────────────
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _filterChip(label: 'All Accounts', value: 'ALL'),
                  const SizedBox(width: 6),
                  _filterChip(label: 'Pending Review', value: 'PENDING_REVIEW'),
                  const SizedBox(width: 6),
                  _filterChip(label: 'Verified', value: 'VERIFIED'),
                  const SizedBox(width: 6),
                  _filterChip(label: 'Rejected', value: 'REJECTED'),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 3. Bank Accounts List ────────────────────────────────────
            AsyncValueView<List<dynamic>>(
              value: accountsAsync,
              onRetry: () => ref.invalidate(adminBankAccountsProvider),
              builder: (context, accounts) {
                final filtered = accounts.where((acct) {
                  if (_statusFilter != 'ALL' && acct.verificationStatus != _statusFilter) {
                    return false;
                  }
                  return true;
                }).toList();

                if (filtered.isEmpty) {
                  return Container(
                    padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 16),
                    alignment: Alignment.center,
                    child: Column(
                      children: [
                        // Bank Account Empty-State Icon
                        Container(
                          padding: const EdgeInsets.all(18),
                          decoration: BoxDecoration(
                            color: const Color(0xFF004E89).withValues(alpha: 0.08),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.account_balance_outlined,
                            size: 52,
                            color: Color(0xFF004E89),
                          ),
                        ),
                        const SizedBox(height: 16),

                        // Title
                        const Text(
                          'No bank accounts added',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 16.5,
                            color: Color(0xFF0A2540),
                          ),
                        ),
                        const SizedBox(height: 6),

                        // Description
                        Text(
                          'Add a bank account to enable withdrawal disbursement.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 24),

                        // Security notice card
                        Container(
                          padding: const EdgeInsets.all(AppSpacing.md),
                          decoration: BoxDecoration(
                            color: const Color(0xFFEFF6FF),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: const Color(0xFFBFDBFE)),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.shield_outlined, size: 18, color: Color(0xFF1D4ED8)),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: const [
                                    Text(
                                      'Security',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w800,
                                        color: Color(0xFF1E3A8A),
                                      ),
                                    ),
                                    SizedBox(height: 3),
                                    Text(
                                      'Full account numbers are never stored in our system. Only the last 4 digits are displayed for identification. Newly added accounts are pending admin verification before they can be used for withdrawals.',
                                      style: TextStyle(
                                        fontSize: 11.5,
                                        color: Color(0xFF1E40AF),
                                        height: 1.35,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                }

                return Column(
                  children: filtered.map((acct) {
                    return AdminBankAccountCard(account: acct);
                  }).toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _filterChip({required String label, required String value}) {
    final isSelected = _statusFilter == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          setState(() => _statusFilter = value);
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
