import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/shared/widgets/async_value_view.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';
import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/admin/presentation/widgets/admin_drawer.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/finance/widgets/admin_transaction_tile.dart';

/// Admin Screen: Transaction Ledger with full filtering and audit trail.
class AdminTransactionsScreen extends ConsumerStatefulWidget {
  const AdminTransactionsScreen({super.key});

  @override
  ConsumerState<AdminTransactionsScreen> createState() => _AdminTransactionsScreenState();
}

class _AdminTransactionsScreenState extends ConsumerState<AdminTransactionsScreen> {
  int _currentPage = 1;
  String? _selectedType;
  String? _selectedDirection;
  String? _selectedStatus;
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final walletsAsync = ref.watch(adminWalletsProvider);
    final wallets = walletsAsync.valueOrNull ?? [];
    final selectedTechnician = ref.watch(adminSelectedTechnicianProvider) ??
        (wallets.isNotEmpty ? wallets.first : null);

    final transactionsAsync = selectedTechnician != null
        ? ref.watch(
            adminTechnicianTransactionsProvider((
              employeeId: selectedTechnician.employeeId,
              page: _currentPage,
            )),
          )
        : null;

    return Scaffold(
      appBar: const WorkforceAppBar(
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(adminWalletsProvider);
          if (selectedTechnician != null) {
            ref.invalidate(
              adminTechnicianTransactionsProvider((
                employeeId: selectedTechnician.employeeId,
                page: _currentPage,
              )),
            );
          }
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
              'Transaction Ledger',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                color: Color(0xFF0A2540),
              ),
            ),
            const SizedBox(height: 3),
            Text(
              'Immutable financial audit trail across technician commissions, settlements & disbursements.',
              style: TextStyle(
                fontSize: 12,
                color: AppColors.textMuted,
                height: 1.35,
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 2. Technician Selector ────────────────────────────────────
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  const Icon(Icons.person_rounded, size: 18, color: Color(0xFF004E89)),
                  const SizedBox(width: 8),
                  const Text('Technician: ', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                  Expanded(
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<int>(
                        isExpanded: true,
                        value: selectedTechnician?.employeeId,
                        hint: const Text('Select Technician'),
                        items: wallets.map((w) {
                          return DropdownMenuItem<int>(
                            value: w.employeeId,
                            child: Text(
                              '${w.employeeName} (EMP-${w.employeeId})',
                              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                              overflow: TextOverflow.ellipsis,
                            ),
                          );
                        }).toList(),
                        onChanged: (newId) {
                          if (newId != null) {
                            final matched = wallets.firstWhere((w) => w.employeeId == newId);
                            ref.read(adminSelectedTechnicianProvider.notifier).state = matched;
                            setState(() => _currentPage = 1);
                          }
                        },
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 3. Filters: Type, Direction, Status ────────────────────────
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  // Type Filter Dropdown
                  _DropdownFilterChip<String>(
                    label: _selectedType != null
                        ? _selectedType!.replaceAll('_', ' ')
                        : 'All Types',
                    isSelected: _selectedType != null,
                    items: const [
                      DropdownMenuItem(value: null, child: Text('All Types')),
                      DropdownMenuItem(value: 'SERVICE_EARNING', child: Text('Service Earning')),
                      DropdownMenuItem(value: 'PLATFORM_COMMISSION', child: Text('Platform Commission')),
                      DropdownMenuItem(value: 'SETTLEMENT_RELEASE', child: Text('Settlement Release')),
                      DropdownMenuItem(value: 'WITHDRAWAL', child: Text('Withdrawal')),
                      DropdownMenuItem(value: 'ADJUSTMENT_CREDIT', child: Text('Adjustment Credit')),
                      DropdownMenuItem(value: 'ADJUSTMENT_DEBIT', child: Text('Adjustment Debit')),
                      DropdownMenuItem(value: 'RECOVERY_DEBIT', child: Text('Recovery Debit')),
                      DropdownMenuItem(value: 'REFUND', child: Text('Refund')),
                    ],
                    onChanged: (val) => setState(() => _selectedType = val),
                  ),
                  const SizedBox(width: 8),

                  // Direction Filter
                  _DropdownFilterChip<String>(
                    label: _selectedDirection ?? 'All Directions',
                    isSelected: _selectedDirection != null,
                    items: const [
                      DropdownMenuItem(value: null, child: Text('All Directions')),
                      DropdownMenuItem(value: 'CREDIT', child: Text('Credits (+)')),
                      DropdownMenuItem(value: 'DEBIT', child: Text('Debits (-)')),
                    ],
                    onChanged: (val) => setState(() => _selectedDirection = val),
                  ),
                  const SizedBox(width: 8),

                  // Status Filter
                  _DropdownFilterChip<String>(
                    label: _selectedStatus != null
                        ? _selectedStatus!.replaceAll('_', ' ')
                        : 'All Statuses',
                    isSelected: _selectedStatus != null,
                    items: const [
                      DropdownMenuItem(value: null, child: Text('All Statuses')),
                      DropdownMenuItem(value: 'COMPLETED', child: Text('Completed')),
                      DropdownMenuItem(value: 'PENDING_SETTLEMENT', child: Text('Pending Settlement')),
                      DropdownMenuItem(value: 'REVERSED', child: Text('Reversed')),
                      DropdownMenuItem(value: 'FAILED', child: Text('Failed')),
                    ],
                    onChanged: (val) => setState(() => _selectedStatus = val),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 4. Transaction List & Pagination ─────────────────────────
            if (transactionsAsync != null) ...[
              AsyncValueView<WalletTransactionListResponse>(
                value: transactionsAsync,
                onRetry: () => ref.invalidate(
                  adminTechnicianTransactionsProvider((
                    employeeId: selectedTechnician!.employeeId,
                    page: _currentPage,
                  )),
                ),
                builder: (context, data) {
                  // Apply client-side filters
                  final filteredResults = data.results.where((txn) {
                    if (_selectedType != null && txn.transactionType != _selectedType) {
                      return false;
                    }
                    if (_selectedDirection != null && txn.direction != _selectedDirection) {
                      return false;
                    }
                    if (_selectedStatus != null && txn.status != _selectedStatus) {
                      return false;
                    }
                    return true;
                  }).toList();

                  if (filteredResults.isEmpty) {
                    return Container(
                      padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 20),
                      alignment: Alignment.center,
                      child: Column(
                        children: [
                          Icon(Icons.receipt_long_outlined, size: 48, color: AppColors.textMuted),
                          const SizedBox(height: 12),
                          const Text(
                            'No transactions found.',
                            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'No financial transactions recorded matching this criteria.',
                            style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                          ),
                        ],
                      ),
                    );
                  }

                  return Card(
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: BorderSide(color: AppColors.border),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Card Header with record count
                        Padding(
                          padding: const EdgeInsets.all(AppSpacing.md),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                '${data.count} Total Records',
                                style: const TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF0F172A),
                                ),
                              ),
                              Text(
                                'Page $_currentPage of ${data.totalPages}',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Divider(color: AppColors.border, height: 1),

                        // List Rows
                        ...filteredResults.map((txn) {
                          return AdminTransactionTile(
                            transaction: txn,
                            technicianName: selectedTechnician?.employeeName,
                          );
                        }),

                        // Pagination Navigation Footer
                        if (data.totalPages > 1) ...[
                          Padding(
                            padding: const EdgeInsets.all(AppSpacing.sm),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                TextButton.icon(
                                  onPressed: _currentPage > 1
                                      ? () => setState(() => _currentPage--)
                                      : null,
                                  icon: const Icon(Icons.arrow_back_rounded, size: 16),
                                  label: const Text('Previous'),
                                ),
                                Text(
                                  'Page $_currentPage / ${data.totalPages}',
                                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                                ),
                                TextButton.icon(
                                  onPressed: _currentPage < data.totalPages
                                      ? () => setState(() => _currentPage++)
                                      : null,
                                  icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                                  label: const Text('Next'),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                  );
                },
              ),
            ] else ...[
              Container(
                padding: const EdgeInsets.all(32),
                alignment: Alignment.center,
                child: Text(
                  'Please select a technician to view ledger transactions.',
                  style: TextStyle(color: AppColors.textMuted),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DropdownFilterChip<T> extends StatelessWidget {
  const _DropdownFilterChip({
    required this.label,
    required this.isSelected,
    required this.items,
    required this.onChanged,
  });

  final String label;
  final bool isSelected;
  final List<DropdownMenuItem<T?>> items;
  final ValueChanged<T?> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 0),
      decoration: BoxDecoration(
        color: isSelected ? const Color(0xFFEFF6FF) : AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isSelected ? const Color(0xFF2563EB) : AppColors.border,
        ),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<T?>(
          isDense: true,
          value: null,
          hint: Text(
            label,
            style: TextStyle(
              fontSize: 11.5,
              fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
              color: isSelected ? const Color(0xFF1E40AF) : const Color(0xFF475569),
            ),
          ),
          items: items,
          onChanged: onChanged,
        ),
      ),
    );
  }
}
