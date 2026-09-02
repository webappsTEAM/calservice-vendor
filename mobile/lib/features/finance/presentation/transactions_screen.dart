import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/finance/presentation/finance_providers.dart';
import 'package:mobile/features/finance/presentation/widgets/transaction_detail_sheet.dart';
import 'package:mobile/features/finance/presentation/widgets/transaction_list_tile.dart';
import 'package:mobile/routing/app_routes.dart';
import 'package:mobile/shared/widgets/empty_state.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';

/// Transactions Ledger screen for technician financial history.
///
/// Features:
/// - Breadcrumb: Back to Wallet action.
/// - Title: Financial Ledger & Transactions
/// - Subtitle: Immutable audit log of all commission earnings, T+7 releases, and withdrawal debits.
/// - Top actions: Refresh & Filter sheet.
/// - Filter modal with Type & Status.
/// - Real API transaction ledger with details on tap.
class TransactionsScreen extends ConsumerStatefulWidget {
  const TransactionsScreen({super.key});

  @override
  ConsumerState<TransactionsScreen> createState() => _TransactionsScreenState();
}

class _TransactionsScreenState extends ConsumerState<TransactionsScreen> {
  bool _isRefreshing = false;

  Future<void> _handleRefresh() async {
    if (_isRefreshing) return;
    setState(() => _isRefreshing = true);
    try {
      ref.invalidate(walletTransactionsProvider);
      await ref.read(walletTransactionsProvider.future);
    } catch (_) {
    } finally {
      if (mounted) {
        setState(() => _isRefreshing = false);
      }
    }
  }

  void _showFilterSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
      ),
      builder: (ctx) => const _TransactionFilterSheet(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final filter = ref.watch(transactionFilterProvider);
    final transactionsAsync = ref.watch(walletTransactionsProvider);
    final isFiltered = filter.type != 'ALL' || filter.status != 'ALL' || filter.direction != 'ALL';

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: const WorkforceAppBar(
        titleText: 'Financial Ledger & Transactions',
        showBrand: false,
        showStatusSubBar: false,
      ),
      body: Column(
        children: [
          // ── Header / Breadcrumb & Title Area ───────────────────────────
          Container(
            color: AppColors.surface,
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.md,
              AppSpacing.sm,
              AppSpacing.md,
              AppSpacing.sm,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Breadcrumb: Back to Wallet
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

                // Screen title & top actions row
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Financial Ledger & Transactions',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                              color: Color(0xFF0A2540),
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'Immutable audit log of all commission earnings, T+7 releases, and withdrawal debits.',
                            style: TextStyle(
                              fontSize: 11.5,
                              color: AppColors.textMuted,
                              height: 1.3,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    // Action icons: Refresh & Filter
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          onPressed: _isRefreshing ? null : _handleRefresh,
                          icon: _isRefreshing
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.refresh_rounded),
                          tooltip: 'Refresh',
                          color: const Color(0xFF004E89),
                        ),
                        Badge(
                          isLabelVisible: isFiltered,
                          backgroundColor: const Color(0xFF004E89),
                          label: const Text('•', style: TextStyle(fontSize: 10)),
                          child: IconButton(
                            onPressed: () => _showFilterSheet(context),
                            icon: const Icon(Icons.tune_rounded),
                            tooltip: 'Filter',
                            color: isFiltered ? const Color(0xFF004E89) : AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
          Divider(color: AppColors.border, height: 1),

          // ── Active Filter Bar (when filters applied) ───────────────────
          if (isFiltered)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 6),
              color: const Color(0xFFEFF6FF),
              child: Row(
                children: [
                  const Icon(Icons.filter_list_rounded, size: 14, color: Color(0xFF004E89)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          if (filter.type != 'ALL')
                            Padding(
                              padding: const EdgeInsets.only(right: 6),
                              child: Chip(
                                label: Text(
                                  _filterLabelForType(filter.type),
                                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700),
                                ),
                                deleteIcon: const Icon(Icons.close_rounded, size: 12),
                                onDeleted: () {
                                  ref.read(transactionFilterProvider.notifier).state =
                                      filter.copyWith(type: 'ALL', page: 1);
                                },
                                padding: EdgeInsets.zero,
                                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                            ),
                          if (filter.status != 'ALL')
                            Padding(
                              padding: const EdgeInsets.only(right: 6),
                              child: Chip(
                                label: Text(
                                  _filterLabelForStatus(filter.status),
                                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700),
                                ),
                                deleteIcon: const Icon(Icons.close_rounded, size: 12),
                                onDeleted: () {
                                  ref.read(transactionFilterProvider.notifier).state =
                                      filter.copyWith(status: 'ALL', page: 1);
                                },
                                padding: EdgeInsets.zero,
                                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                            ),
                          if (filter.direction != 'ALL')
                            Chip(
                              label: Text(
                                filter.direction == 'CREDIT' ? 'Credits (+)' : 'Debits (-)',
                                style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700),
                              ),
                              deleteIcon: const Icon(Icons.close_rounded, size: 12),
                              onDeleted: () {
                                ref.read(transactionFilterProvider.notifier).state =
                                    filter.copyWith(direction: 'ALL', page: 1);
                              },
                              padding: EdgeInsets.zero,
                              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                        ],
                      ),
                    ),
                  ),
                  TextButton(
                    onPressed: () {
                      ref.read(transactionFilterProvider.notifier).state =
                          const TransactionFilterState();
                    },
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      minimumSize: Size.zero,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    child: const Text(
                      'Clear',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF004E89)),
                    ),
                  ),
                ],
              ),
            ),

          // ── Transaction List / Empty States ────────────────────────────
          Expanded(
            child: RefreshIndicator(
              onRefresh: _handleRefresh,
              child: transactionsAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (err, _) => Center(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.xl),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.error_outline_rounded, size: 40, color: Color(0xFFE11D48)),
                        const SizedBox(height: AppSpacing.md),
                        const Text(
                          'Failed to load transactions',
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
                data: (response) {
                  final transactions = response.results;

                  if (transactions.isEmpty) {
                    return ListView(
                      padding: const EdgeInsets.all(AppSpacing.xl),
                      children: [
                        EmptyState(
                          icon: Icons.receipt_long_outlined,
                          title: isFiltered ? 'No Matches Found' : 'No Transactions Recorded',
                          message: isFiltered
                              ? 'No ledger records found matching your filters.'
                              : 'No transactions recorded yet. Complete customer jobs to earn commission.',
                        ),
                        if (isFiltered) ...[
                          const SizedBox(height: AppSpacing.md),
                          Center(
                            child: TextButton.icon(
                              onPressed: () {
                                ref.read(transactionFilterProvider.notifier).state =
                                    const TransactionFilterState();
                              },
                              icon: const Icon(Icons.clear_rounded, size: 16),
                              label: const Text('Reset Filters'),
                            ),
                          ),
                        ],
                      ],
                    );
                  }

                  return ListView.builder(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    itemCount: transactions.length + (response.totalPages > 1 ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index < transactions.length) {
                        final txn = transactions[index];
                        return TransactionListTile(
                          transaction: txn,
                          onTap: () => TransactionDetailSheet.show(context, txn),
                        );
                      }

                      // Pagination Controls
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.chevron_left_rounded),
                              onPressed: response.page > 1
                                  ? () {
                                      ref.read(transactionFilterProvider.notifier).state =
                                          filter.copyWith(page: response.page - 1);
                                    }
                                  : null,
                            ),
                            Text(
                              'Page ${response.page} of ${response.totalPages}',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                color: AppColors.textSecondary,
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.chevron_right_rounded),
                              onPressed: response.page < response.totalPages
                                  ? () {
                                      ref.read(transactionFilterProvider.notifier).state =
                                          filter.copyWith(page: response.page + 1);
                                    }
                                  : null,
                            ),
                          ],
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _filterLabelForType(String type) {
    switch (type) {
      case 'SERVICE_EARNING':
        return 'Service Earnings (60%)';
      case 'SETTLEMENT_RELEASE':
        return 'Settlement Release (T+7)';
      case 'WITHDRAWAL':
        return 'Withdrawals';
      case 'WITHDRAWAL_REVERSAL':
        return 'Withdrawal Reversals';
      case 'ADJUSTMENT_CREDIT':
        return 'Admin Credits';
      case 'ADJUSTMENT_DEBIT':
        return 'Admin Debits';
      default:
        return type;
    }
  }

  String _filterLabelForStatus(String status) {
    switch (status) {
      case 'COMPLETED':
        return 'Completed';
      case 'PENDING':
        return 'Pending Settlement';
      case 'REVERSED':
        return 'Reversed';
      default:
        return status;
    }
  }
}

/// Mobile filter bottom sheet for transaction type and status.
class _TransactionFilterSheet extends ConsumerStatefulWidget {
  const _TransactionFilterSheet();

  @override
  ConsumerState<_TransactionFilterSheet> createState() => _TransactionFilterSheetState();
}

class _TransactionFilterSheetState extends ConsumerState<_TransactionFilterSheet> {
  late String _selectedType;
  late String _selectedStatus;
  late String _selectedDirection;

  static const List<Map<String, String>> _types = [
    {'label': 'All Transaction Types', 'value': 'ALL'},
    {'label': 'Service Earnings (60%)', 'value': 'SERVICE_EARNING'},
    {'label': 'Settlement Release (T+7)', 'value': 'SETTLEMENT_RELEASE'},
    {'label': 'Withdrawals', 'value': 'WITHDRAWAL'},
    {'label': 'Withdrawal Reversals', 'value': 'WITHDRAWAL_REVERSAL'},
    {'label': 'Admin Credits', 'value': 'ADJUSTMENT_CREDIT'},
    {'label': 'Admin Debits', 'value': 'ADJUSTMENT_DEBIT'},
  ];

  static const List<Map<String, String>> _statuses = [
    {'label': 'All Statuses', 'value': 'ALL'},
    {'label': 'Completed', 'value': 'COMPLETED'},
    {'label': 'Pending Settlement', 'value': 'PENDING'},
    {'label': 'Reversed', 'value': 'REVERSED'},
  ];

  static const List<Map<String, String>> _directions = [
    {'label': 'All Directions', 'value': 'ALL'},
    {'label': 'Credits (+)', 'value': 'CREDIT'},
    {'label': 'Debits (-)', 'value': 'DEBIT'},
  ];

  @override
  void initState() {
    super.initState();
    final filter = ref.read(transactionFilterProvider);
    _selectedType = filter.type;
    _selectedStatus = filter.status;
    _selectedDirection = filter.direction;
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          AppSpacing.md,
          AppSpacing.lg,
          AppSpacing.lg,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Handle
            Center(
              child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.sm),

            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Filter Transactions',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),

            // Section 1: Transaction Type
            const Text(
              'TRANSACTION TYPE',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.8,
                color: Color(0xFF64748B),
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: _types.map((t) {
                final isSelected = _selectedType == t['value'];
                return ChoiceChip(
                  label: Text(t['label']!),
                  selected: isSelected,
                  selectedColor: const Color(0xFF004E89),
                  labelStyle: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    color: isSelected ? Colors.white : AppColors.textSecondary,
                  ),
                  onSelected: (selected) {
                    if (selected) setState(() => _selectedType = t['value']!);
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: AppSpacing.md),

            // Section 2: Status
            const Text(
              'STATUS',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.8,
                color: Color(0xFF64748B),
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: _statuses.map((s) {
                final isSelected = _selectedStatus == s['value'];
                return ChoiceChip(
                  label: Text(s['label']!),
                  selected: isSelected,
                  selectedColor: const Color(0xFF004E89),
                  labelStyle: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    color: isSelected ? Colors.white : AppColors.textSecondary,
                  ),
                  onSelected: (selected) {
                    if (selected) setState(() => _selectedStatus = s['value']!);
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: AppSpacing.md),

            // Section 3: Direction (Credits/Debits)
            const Text(
              'FLOW DIRECTION',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.8,
                color: Color(0xFF64748B),
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: _directions.map((d) {
                final isSelected = _selectedDirection == d['value'];
                return ChoiceChip(
                  label: Text(d['label']!),
                  selected: isSelected,
                  selectedColor: const Color(0xFF004E89),
                  labelStyle: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    color: isSelected ? Colors.white : AppColors.textSecondary,
                  ),
                  onSelected: (selected) {
                    if (selected) setState(() => _selectedDirection = d['value']!);
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: AppSpacing.lg),

            // Actions: Reset & Apply
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () {
                      ref.read(transactionFilterProvider.notifier).state =
                          const TransactionFilterState();
                      Navigator.of(context).pop();
                    },
                    child: const Text('Reset All'),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  flex: 2,
                  child: FilledButton(
                    onPressed: () {
                      ref.read(transactionFilterProvider.notifier).state =
                          TransactionFilterState(
                        type: _selectedType,
                        status: _selectedStatus,
                        direction: _selectedDirection,
                        page: 1,
                      );
                      Navigator.of(context).pop();
                    },
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF004E89),
                    ),
                    child: const Text('Apply Filters'),
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
