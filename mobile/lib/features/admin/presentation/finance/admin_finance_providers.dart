import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/admin/data/admin_finance_repository.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';

/// Provider for the list of all technician wallets in the company.
final adminWalletsProvider = FutureProvider<List<AdminWallet>>((ref) async {
  final repository = ref.watch(adminFinanceRepositoryProvider);
  return repository.fetchWallets();
});

/// Computes the aggregated financial summary from all technician wallets.
final adminWalletSummaryProvider = Provider<AdminWalletSummary?>((ref) {
  final walletsAsync = ref.watch(adminWalletsProvider);
  return walletsAsync.valueOrNull != null
      ? AdminWalletSummary.fromWallets(walletsAsync.valueOrNull!)
      : null;
});

/// Filter state for technician wallets screen (ALL, ACTIVE, LOCKED, SUSPENDED).
final adminWalletStatusFilterProvider = StateProvider<String>((ref) => 'ALL');

/// Search query state for technician wallets.
final adminWalletSearchQueryProvider = StateProvider<String>((ref) => '');

/// Provides filtered and searched technician wallets list.
final filteredAdminWalletsProvider = Provider<List<AdminWallet>>((ref) {
  final wallets = ref.watch(adminWalletsProvider).valueOrNull ?? [];
  final statusFilter = ref.watch(adminWalletStatusFilterProvider);
  final searchQuery = ref.watch(adminWalletSearchQueryProvider).toLowerCase().trim();

  return wallets.where((w) {
    if (statusFilter != 'ALL' && w.status != statusFilter) {
      return false;
    }
    if (searchQuery.isNotEmpty) {
      final nameMatches = w.employeeName.toLowerCase().contains(searchQuery);
      final idMatches = 'emp-${w.employeeId}'.contains(searchQuery) ||
          w.employeeId.toString().contains(searchQuery);
      return nameMatches || idMatches;
    }
    return true;
  }).toList();
});

/// Selected technician for viewing specific ledger transactions.
final adminSelectedTechnicianProvider = StateProvider<AdminWallet?>((ref) => null);

/// Filter for transactions ledger (all types or specific type).
final adminTransactionTypeFilterProvider = StateProvider<String?>((ref) => null);

/// Direction filter for transactions ledger (all, CREDIT, DEBIT).
final adminTransactionDirectionFilterProvider = StateProvider<String?>((ref) => null);

/// Status filter for transactions ledger (COMPLETED, PENDING_SETTLEMENT, etc.).
final adminTransactionStatusFilterProvider = StateProvider<String?>((ref) => null);

/// Search query in transaction ledger.
final adminTransactionSearchQueryProvider = StateProvider<String>((ref) => '');

/// Fetches paginated transaction ledger for a selected technician.
final adminTechnicianTransactionsProvider =
    FutureProvider.family<WalletTransactionListResponse, ({int employeeId, int page})>(
  (ref, args) async {
    final repository = ref.watch(adminFinanceRepositoryProvider);
    return repository.fetchEmployeeTransactions(
      employeeId: args.employeeId,
      page: args.page,
    );
  },
);

/// Filter for withdrawals list (ALL, REQUESTED, PROCESSING, COMPLETED, FAILED, CANCELLED).
final adminWithdrawalStatusFilterProvider = StateProvider<String>((ref) => 'ALL');

/// Fetches all company payout requests.
final adminWithdrawalsProvider = FutureProvider<List<AdminWithdrawal>>((ref) async {
  final repository = ref.watch(adminFinanceRepositoryProvider);
  final filter = ref.watch(adminWithdrawalStatusFilterProvider);
  return repository.fetchWithdrawals(status: filter);
});

/// Pending payout requests count.
final adminPendingWithdrawalsCountProvider = Provider<int>((ref) {
  final withdrawals = ref.watch(adminWithdrawalsProvider).valueOrNull ?? [];
  return withdrawals.where((w) => w.isRequested || w.isProcessing).length;
});

/// Fetches bank accounts for administration.
final adminBankAccountsProvider = FutureProvider<List<AdminBankAccount>>((ref) async {
  final repository = ref.watch(adminFinanceRepositoryProvider);
  return repository.fetchBankAccounts();
});
