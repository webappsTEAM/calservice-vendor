import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/widgets/admin_drawer.dart';
import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/finance/presentation/widgets/transaction_detail_sheet.dart';
import 'package:mobile/shared/widgets/empty_state.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';

/// Super Admin / Platform Treasury: Transaction Ledger Screen.
///
/// Implements an immutable financial audit trail across technician earnings,
/// platform commissions, T+7 settlements, payout disbursements, and balance adjustments.
class AdminTransactionsScreen extends ConsumerStatefulWidget {
  const AdminTransactionsScreen({super.key});

  @override
  ConsumerState<AdminTransactionsScreen> createState() =>
      _AdminTransactionsScreenState();
}

class _AdminTransactionsScreenState
    extends ConsumerState<AdminTransactionsScreen> {
  final _searchController = TextEditingController();
  int _currentPage = 1;

  // Active (applied) filter states
  String? _appliedType;
  String? _appliedDirection;
  String? _appliedStatus;
  String _appliedSearchQuery = '';

  // Pending (draft) filter states in UI
  String? _selectedType;
  String? _selectedDirection;
  String? _selectedStatus;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _applyFilters() {
    setState(() {
      _appliedType = _selectedType;
      _appliedDirection = _selectedDirection;
      _appliedStatus = _selectedStatus;
      _appliedSearchQuery = _searchController.text.trim().toLowerCase();
      _currentPage = 1;
    });
  }

  Future<void> _refresh() async {
    ref.invalidate(adminWalletsProvider);
    final selectedTechnician = ref.read(adminSelectedTechnicianProvider);
    if (selectedTechnician != null) {
      ref.invalidate(
        adminTechnicianTransactionsProvider((
          employeeId: selectedTechnician.employeeId,
          page: _currentPage,
        )),
      );
    }
  }

  String _statusDisplay(String status) {
    switch (status.toUpperCase()) {
      case 'COMPLETED':
        return 'Completed';
      case 'PENDING_SETTLEMENT':
      case 'PENDING SETTLEMENT':
        return 'Pending Settlement';
      case 'REVERSED':
        return 'Reversed';
      case 'FAILED':
        return 'Failed';
      default:
        return status.replaceAll('_', ' ');
    }
  }

  String _typeDisplay(String type) {
    switch (type.toUpperCase()) {
      case 'SERVICE_EARNING':
        return 'Service Earning';
      case 'PLATFORM_COMMISSION':
      case 'PLATFORM_DEDUCTION':
        return 'Platform Commission';
      case 'REFUND':
        return 'Refund';
      case 'RECOVERY_DEBIT':
        return 'Recovery Debit';
      case 'WITHDRAWAL':
        return 'Withdrawal';
      case 'ADJUSTMENT_CREDIT':
        return 'Adjustment Credit';
      case 'ADJUSTMENT_DEBIT':
        return 'Adjustment Debit';
      case 'SETTLEMENT_RELEASE':
        return 'Settlement Release';
      default:
        return type.replaceAll('_', ' ');
    }
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

    final totalCount = transactionsAsync?.valueOrNull?.count ?? 0;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: const WorkforceAppBar(
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _refresh,
          color: const Color(0xFF0F172A),
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(AppSpacing.md),
            children: [
              // ── 1. Page Header ───────────────────────────────────────────
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x040F172A),
                      blurRadius: 8,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Navigation Context Badge
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF1F5F9),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Text(
                        'Workforce → Home → Wallets → Ledger',
                        style: TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF475569),
                          letterSpacing: 0.3,
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),

                    // Title & Refresh Row
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 42,
                          height: 42,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [Color(0xFF004E89), Color(0xFF0284C7)],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(
                            Icons.receipt_long_rounded,
                            color: Colors.white,
                            size: 22,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Transaction Ledger',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w900,
                                  color: Color(0xFF0F172A),
                                  letterSpacing: -0.2,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                '$totalCount total records · immutable financial audit trail',
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF64748B),
                                  height: 1.35,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        OutlinedButton.icon(
                          onPressed: _refresh,
                          icon: const Icon(Icons.refresh_rounded, size: 15),
                          label: const Text('Refresh'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF475569),
                            side: const BorderSide(color: Color(0xFFCBD5E1)),
                            visualDensity: VisualDensity.compact,
                            textStyle: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // ── 2. Technician Selector ────────────────────────────────────
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.person_outline_rounded,
                        size: 18, color: Color(0xFF004E89)),
                    const SizedBox(width: 8),
                    const Text(
                      'Technician: ',
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 12.5,
                        color: Color(0xFF334155),
                      ),
                    ),
                    Expanded(
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<int>(
                          isExpanded: true,
                          value: selectedTechnician?.employeeId,
                          hint: const Text('Select Technician',
                              style: TextStyle(fontSize: 12.5)),
                          items: wallets.map((w) {
                            return DropdownMenuItem<int>(
                              value: w.employeeId,
                              child: Text(
                                '${w.employeeName} (EMP-${w.employeeId})',
                                style: const TextStyle(
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF0F172A),
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            );
                          }).toList(),
                          onChanged: (newId) {
                            if (newId != null) {
                              final matched = wallets
                                  .firstWhere((w) => w.employeeId == newId);
                              ref
                                  .read(
                                      adminSelectedTechnicianProvider.notifier)
                                  .state = matched;
                              setState(() => _currentPage = 1);
                            }
                          },
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.sm),

              // ── 3. Search Bar ─────────────────────────────────────────────
              Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: TextField(
                  controller: _searchController,
                  onChanged: (val) {
                    setState(() {
                      _appliedSearchQuery = val.trim().toLowerCase();
                    });
                  },
                  style: const TextStyle(fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Search transaction, employee, reference...',
                    hintStyle: const TextStyle(
                      fontSize: 12.5,
                      color: Color(0xFF94A3B8),
                    ),
                    prefixIcon: const Icon(
                      Icons.search_rounded,
                      size: 18,
                      color: Color(0xFF94A3B8),
                    ),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear_rounded, size: 16),
                            onPressed: () {
                              _searchController.clear();
                              setState(() {
                                _appliedSearchQuery = '';
                              });
                            },
                          )
                        : null,
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 11,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.sm),

              // ── 4. Transaction Filters (Type, Direction, Status, Apply) ──
              Row(
                children: [
                  Expanded(
                    child: SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          // A. Transaction Type Dropdown
                          _DropdownFilterChip<String>(
                            label: _selectedType != null
                                ? _typeDisplay(_selectedType!)
                                : 'All Types',
                            isSelected: _selectedType != null,
                            items: const [
                              DropdownMenuItem(
                                  value: null, child: Text('All Types')),
                              DropdownMenuItem(
                                  value: 'SERVICE_EARNING',
                                  child: Text('Service Earning')),
                              DropdownMenuItem(
                                  value: 'PLATFORM_COMMISSION',
                                  child: Text('Platform Commission')),
                              DropdownMenuItem(
                                  value: 'REFUND', child: Text('Refund')),
                              DropdownMenuItem(
                                  value: 'RECOVERY_DEBIT',
                                  child: Text('Recovery Debit')),
                              DropdownMenuItem(
                                  value: 'WITHDRAWAL',
                                  child: Text('Withdrawal')),
                              DropdownMenuItem(
                                  value: 'ADJUSTMENT_CREDIT',
                                  child: Text('Adjustment Credit')),
                              DropdownMenuItem(
                                  value: 'ADJUSTMENT_DEBIT',
                                  child: Text('Adjustment Debit')),
                              DropdownMenuItem(
                                  value: 'SETTLEMENT_RELEASE',
                                  child: Text('Settlement Release')),
                            ],
                            onChanged: (val) {
                              setState(() => _selectedType = val);
                            },
                          ),
                          const SizedBox(width: 6),

                          // B. Transaction Direction Dropdown
                          _DropdownFilterChip<String>(
                            label: _selectedDirection != null
                                ? (_selectedDirection == 'CREDIT'
                                    ? 'Credit'
                                    : 'Debit')
                                : 'All Directions',
                            isSelected: _selectedDirection != null,
                            items: const [
                              DropdownMenuItem(
                                  value: null, child: Text('All Directions')),
                              DropdownMenuItem(
                                  value: 'CREDIT', child: Text('Credit')),
                              DropdownMenuItem(
                                  value: 'DEBIT', child: Text('Debit')),
                            ],
                            onChanged: (val) {
                              setState(() => _selectedDirection = val);
                            },
                          ),
                          const SizedBox(width: 6),

                          // C. Transaction Status Dropdown
                          _DropdownFilterChip<String>(
                            label: _selectedStatus != null
                                ? _statusDisplay(_selectedStatus!)
                                : 'All Statuses',
                            isSelected: _selectedStatus != null,
                            items: const [
                              DropdownMenuItem(
                                  value: null, child: Text('All Statuses')),
                              DropdownMenuItem(
                                  value: 'COMPLETED',
                                  child: Text('Completed')),
                              DropdownMenuItem(
                                  value: 'PENDING_SETTLEMENT',
                                  child: Text('Pending Settlement')),
                              DropdownMenuItem(
                                  value: 'REVERSED',
                                  child: Text('Reversed')),
                              DropdownMenuItem(
                                  value: 'FAILED', child: Text('Failed')),
                            ],
                            onChanged: (val) {
                              setState(() => _selectedStatus = val);
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),

                  // D. Apply Button (Always immediately visible)
                  FilledButton(
                    onPressed: _applyFilters,
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF0F172A),
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 8),
                      textStyle: const TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    child: const Text('Apply'),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),

              // ── 5. Transaction Ledger List ────────────────────────────────
              if (transactionsAsync != null) ...[
                transactionsAsync.when(
                  loading: () => const Center(
                    child: Padding(
                      padding: EdgeInsets.all(AppSpacing.xxl),
                      child:
                          CircularProgressIndicator(color: Color(0xFF0F172A)),
                    ),
                  ),
                  error: (error, stack) {
                    return Container(
                      padding: const EdgeInsets.all(AppSpacing.xl),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFFECDD3)),
                      ),
                      child: Column(
                        children: [
                          const Icon(Icons.error_outline_rounded,
                              size: 36, color: Color(0xFFDC2626)),
                          const SizedBox(height: 12),
                          const Text(
                            'Failed to load transactions.',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF0F172A),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            error.toString(),
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontSize: 12,
                              color: Color(0xFF64748B),
                            ),
                          ),
                          const SizedBox(height: 16),
                          FilledButton.icon(
                            onPressed: _refresh,
                            icon: const Icon(Icons.refresh_rounded, size: 16),
                            label: const Text('Retry'),
                            style: FilledButton.styleFrom(
                              backgroundColor: const Color(0xFF0F172A),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                  data: (data) {
                    // Filter transaction results based on applied filters & search query
                    final filteredResults = data.results.where((txn) {
                      if (_appliedType != null &&
                          txn.transactionType.toUpperCase() !=
                              _appliedType!.toUpperCase()) {
                        return false;
                      }
                      if (_appliedDirection != null &&
                          txn.direction.toUpperCase() !=
                              _appliedDirection!.toUpperCase()) {
                        return false;
                      }
                      if (_appliedStatus != null) {
                        final txnStatusNorm = txn.status
                            .toUpperCase()
                            .replaceAll(' ', '_');
                        final filterStatusNorm = _appliedStatus!
                            .toUpperCase()
                            .replaceAll(' ', '_');
                        if (txnStatusNorm != filterStatusNorm) {
                          return false;
                        }
                      }
                      if (_appliedSearchQuery.isNotEmpty) {
                        final query = _appliedSearchQuery;
                        final matchesId = txn.id.toString().contains(query) ||
                            'txn#${txn.id}'.contains(query);
                        final matchesRef = txn.referenceId
                                ?.toLowerCase()
                                .contains(query) ??
                            false;
                        final matchesDesc = txn.description
                                ?.toLowerCase()
                                .contains(query) ??
                            false;
                        final matchesTech = selectedTechnician?.employeeName
                                .toLowerCase()
                                .contains(query) ??
                            false;
                        final matchesEmpId = selectedTechnician?.employeeId
                                .toString()
                                .contains(query) ??
                            false;

                        if (!matchesId &&
                            !matchesRef &&
                            !matchesDesc &&
                            !matchesTech &&
                            !matchesEmpId) {
                          return false;
                        }
                      }
                      return true;
                    }).toList();

                    if (filteredResults.isEmpty) {
                      return Container(
                        padding: const EdgeInsets.symmetric(
                            vertical: 40, horizontal: 16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: const EmptyState(
                          icon: Icons.receipt_long_outlined,
                          title: 'No transactions found',
                          message:
                              'No financial transactions match the current filter criteria.',
                        ),
                      );
                    }

                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Card Header with record count
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                '${filteredResults.length} Filtered (${data.count} Total)',
                                style: const TextStyle(
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF0F172A),
                                ),
                              ),
                              if (data.totalPages > 1)
                                Text(
                                  'Page $_currentPage of ${data.totalPages}',
                                  style: const TextStyle(
                                    fontSize: 11.5,
                                    fontWeight: FontWeight.w600,
                                    color: Color(0xFF64748B),
                                  ),
                                ),
                            ],
                          ),
                        ),

                        // Transaction Cards
                        ...filteredResults.map((txn) {
                          return _TransactionCard(
                            key: ValueKey(txn.id),
                            transaction: txn,
                            technicianName: selectedTechnician?.employeeName,
                            employeeId: selectedTechnician?.employeeId,
                            onTap: () =>
                                TransactionDetailSheet.show(context, txn),
                          );
                        }),

                        // Pagination Navigation Footer
                        if (data.totalPages > 1) ...[
                          const SizedBox(height: AppSpacing.sm),
                          Container(
                            padding: const EdgeInsets.all(AppSpacing.sm),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(10),
                              border:
                                  Border.all(color: const Color(0xFFE2E8F0)),
                            ),
                            child: Row(
                              mainAxisAlignment:
                                  MainAxisAlignment.spaceBetween,
                              children: [
                                OutlinedButton.icon(
                                  onPressed: _currentPage > 1
                                      ? () => setState(() => _currentPage--)
                                      : null,
                                  icon: const Icon(Icons.arrow_back_rounded,
                                      size: 15),
                                  label: const Text('Previous'),
                                  style: OutlinedButton.styleFrom(
                                    visualDensity: VisualDensity.compact,
                                  ),
                                ),
                                Text(
                                  'Page $_currentPage / ${data.totalPages}',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                OutlinedButton.icon(
                                  onPressed: _currentPage < data.totalPages
                                      ? () => setState(() => _currentPage++)
                                      : null,
                                  icon: const Icon(
                                      Icons.arrow_forward_rounded,
                                      size: 15),
                                  label: const Text('Next'),
                                  style: OutlinedButton.styleFrom(
                                    visualDensity: VisualDensity.compact,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    );
                  },
                ),
              ] else ...[
                Container(
                  padding: const EdgeInsets.all(32),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: const Center(
                    child: Text(
                      'Please select a technician to view ledger transactions.',
                      style: TextStyle(color: Color(0xFF64748B)),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Dropdown Filter Chip for Types, Directions, and Statuses
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
        color: isSelected ? const Color(0xFFEFF6FF) : Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isSelected
              ? const Color(0xFF004E89)
              : const Color(0xFFE2E8F0),
          width: isSelected ? 1.2 : 1.0,
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
              color: isSelected
                  ? const Color(0xFF004E89)
                  : const Color(0xFF475569),
            ),
          ),
          items: items,
          onChanged: onChanged,
        ),
      ),
    );
  }
}

/// Responsive Transaction Card
class _TransactionCard extends StatelessWidget {
  const _TransactionCard({
    super.key,
    required this.transaction,
    this.technicianName,
    this.employeeId,
    required this.onTap,
  });

  final WalletTransaction transaction;
  final String? technicianName;
  final int? employeeId;
  final VoidCallback onTap;

  IconData _iconForType(String type) {
    switch (type.toUpperCase()) {
      case 'SERVICE_EARNING':
        return Icons.handyman_rounded;
      case 'PLATFORM_COMMISSION':
      case 'PLATFORM_DEDUCTION':
        return Icons.percent_rounded;
      case 'SETTLEMENT_RELEASE':
        return Icons.lock_open_rounded;
      case 'WITHDRAWAL':
        return Icons.payments_rounded;
      case 'ADJUSTMENT_CREDIT':
      case 'ADJUSTMENT_DEBIT':
        return Icons.tune_rounded;
      case 'RECOVERY_DEBIT':
      case 'REFUND':
        return Icons.undo_rounded;
      default:
        return Icons.receipt_long_rounded;
    }
  }

  Color _statusColor(String status) {
    switch (status.toUpperCase()) {
      case 'COMPLETED':
        return const Color(0xFF059669);
      case 'PENDING_SETTLEMENT':
      case 'PENDING SETTLEMENT':
        return const Color(0xFFD97706);
      case 'REVERSED':
        return const Color(0xFF64748B);
      case 'FAILED':
        return const Color(0xFFDC2626);
      default:
        return const Color(0xFF475569);
    }
  }

  String _statusDisplay(String status) {
    switch (status.toUpperCase()) {
      case 'COMPLETED':
        return 'Completed';
      case 'PENDING_SETTLEMENT':
      case 'PENDING SETTLEMENT':
        return 'Pending Settlement';
      case 'REVERSED':
        return 'Reversed';
      case 'FAILED':
        return 'Failed';
      default:
        return status.replaceAll('_', ' ');
    }
  }

  @override
  Widget build(BuildContext context) {
    final isCredit = transaction.direction.toUpperCase() == 'CREDIT';
    final sign = isCredit ? '+' : '−';
    final amountColor =
        isCredit ? const Color(0xFF059669) : const Color(0xFFDC2626);
    final statusColor = _statusColor(transaction.status);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x030F172A),
            blurRadius: 4,
            offset: Offset(0, 1),
          ),
        ],
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Row 1: Type Icon, Type Title & Description, Amount
              Row(
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      color: isCredit
                          ? const Color(0xFFECFDF5)
                          : const Color(0xFFFFF1F2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(
                      _iconForType(transaction.transactionType),
                      size: 16,
                      color: amountColor,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          transaction.displayTitle,
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF0F172A),
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (transaction.description != null &&
                            transaction.description!.isNotEmpty)
                          Text(
                            transaction.description!,
                            style: const TextStyle(
                              fontSize: 11.5,
                              color: Color(0xFF475569),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        if (transaction.referenceId != null &&
                            transaction.referenceId!.isNotEmpty)
                          Text(
                            'Ref: ${transaction.referenceId}',
                            style: const TextStyle(
                              fontSize: 11,
                              fontFamily: 'monospace',
                              color: Color(0xFF64748B),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Amount
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          '$sign₹${transaction.amount.toStringAsFixed(2)}',
                          style: TextStyle(
                            fontSize: 14.5,
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w900,
                            color: amountColor,
                          ),
                        ),
                      ),
                      if (transaction.createdAt != null)
                        Text(
                          '${transaction.createdAt!.day.toString().padLeft(2, '0')}/${transaction.createdAt!.month.toString().padLeft(2, '0')}/${transaction.createdAt!.year}',
                          style: const TextStyle(
                            fontSize: 10.5,
                            color: Color(0xFF94A3B8),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 8),
              const Divider(height: 1, color: Color(0xFFF1F5F9)),
              const SizedBox(height: 8),

              // Row 2: Badges (Direction & Status) + Technician Name & Details Hint
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      // Direction Badge
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: isCredit
                              ? const Color(0xFFECFDF5)
                              : const Color(0xFFFFF1F2),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(
                            color: isCredit
                                ? const Color(0xFFA7F3D0)
                                : const Color(0xFFFECDD3),
                            width: 0.8,
                          ),
                        ),
                        child: Text(
                          transaction.direction.toUpperCase(),
                          style: TextStyle(
                            fontSize: 9.5,
                            fontWeight: FontWeight.w800,
                            color: isCredit
                                ? const Color(0xFF059669)
                                : const Color(0xFFDC2626),
                          ),
                        ),
                      ),

                      // Status Badge
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: statusColor.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(
                            color: statusColor.withValues(alpha: 0.35),
                            width: 0.8,
                          ),
                        ),
                        child: Text(
                          _statusDisplay(transaction.status),
                          style: TextStyle(
                            fontSize: 9.5,
                            fontWeight: FontWeight.w800,
                            color: statusColor,
                          ),
                        ),
                      ),
                    ],
                  ),

                  // Technician name or TXN ID
                  Flexible(
                    child: Text(
                      technicianName != null
                          ? '$technicianName (EMP-$employeeId)'
                          : 'TXN #${transaction.id}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: Color(0xFF64748B),
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
