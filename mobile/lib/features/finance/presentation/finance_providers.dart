import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/finance_repository.dart';
import '../domain/employee_wallet.dart';
import '../domain/payout_account.dart';
import '../domain/wallet_transaction.dart';
import '../domain/wallet_withdrawal.dart';

/// Transaction filter state holder.
class TransactionFilterState {
  const TransactionFilterState({
    this.type = 'ALL',
    this.status = 'ALL',
    this.direction = 'ALL',
    this.page = 1,
  });

  final String type;
  final String status;
  final String direction;
  final int page;

  TransactionFilterState copyWith({
    String? type,
    String? status,
    String? direction,
    int? page,
  }) {
    return TransactionFilterState(
      type: type ?? this.type,
      status: status ?? this.status,
      direction: direction ?? this.direction,
      page: page ?? this.page,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is TransactionFilterState &&
          runtimeType == other.runtimeType &&
          type == other.type &&
          status == other.status &&
          direction == other.direction &&
          page == other.page;

  @override
  int get hashCode => Object.hash(type, status, direction, page);
}

/// Filter state provider for transaction history.
final transactionFilterProvider = StateProvider<TransactionFilterState>((ref) {
  return const TransactionFilterState();
});

/// Fetches technician's wallet summary (balance, hold, earnings, etc.).
final employeeWalletProvider = FutureProvider.autoDispose<EmployeeWallet>((ref) async {
  final repo = ref.watch(financeRepositoryProvider);
  return repo.getWalletSummary();
});

/// Fetches paginated transaction records based on active filters.
final walletTransactionsProvider =
    FutureProvider.autoDispose<WalletTransactionListResponse>((ref) async {
  final repo = ref.watch(financeRepositoryProvider);
  final filter = ref.watch(transactionFilterProvider);

  final response = await repo.getTransactions(
    page: filter.page,
    type: filter.type != 'ALL' ? filter.type : null,
    status: filter.status != 'ALL' ? filter.status : null,
  );

  // If client-side direction filter is set to CREDIT or DEBIT
  if (filter.direction != 'ALL') {
    final filteredResults = response.results.where((txn) {
      if (filter.direction == 'CREDIT') return txn.isCredit;
      if (filter.direction == 'DEBIT') return txn.isDebit;
      return true;
    }).toList();

    return WalletTransactionListResponse(
      count: filteredResults.length,
      page: response.page,
      pageSize: response.pageSize,
      totalPages: response.totalPages,
      results: filteredResults,
    );
  }

  return response;
});

/// Fetches all withdrawal / payout requests for the technician.
final walletWithdrawalsProvider =
    FutureProvider.autoDispose<List<WalletWithdrawal>>((ref) async {
  final repo = ref.watch(financeRepositoryProvider);
  return repo.getWithdrawals();
});

/// Fetches active registered bank payout accounts.
final payoutAccountsProvider =
    FutureProvider.autoDispose<List<PayoutAccount>>((ref) async {
  final repo = ref.watch(financeRepositoryProvider);
  return repo.getPayoutAccounts();
});

/// Returns primary or first verified bank payout account.
final primaryPayoutAccountProvider = Provider.autoDispose<PayoutAccount?>((ref) {
  final accountsAsync = ref.watch(payoutAccountsProvider);
  final accounts = accountsAsync.valueOrNull;
  if (accounts == null || accounts.isEmpty) return null;

  // Prefer primary active account
  final primary = accounts.where((a) => a.isPrimary && a.isActive).firstOrNull;
  if (primary != null) return primary;

  // Otherwise return first verified or active
  final verified = accounts.where((a) => a.isVerified && a.isActive).firstOrNull;
  if (verified != null) return verified;

  return accounts.firstOrNull;
});

/// Result model representing withdrawal eligibility calculation.
class WithdrawalEligibility {
  const WithdrawalEligibility({
    required this.isEligible,
    required this.availableBalance,
    required this.minThreshold,
    required this.shortfall,
    required this.progressRatio,
    required this.hasPayoutAccount,
    required this.reason,
  });

  final bool isEligible;
  final double availableBalance;
  final double minThreshold;
  final double shortfall;
  final double progressRatio;
  final bool hasPayoutAccount;
  final String? reason;
}

/// Authoritative withdrawal eligibility calculator combining wallet balance and bank accounts.
final withdrawalEligibilityProvider = Provider.autoDispose<WithdrawalEligibility>((ref) {
  final walletAsync = ref.watch(employeeWalletProvider);
  final accountsAsync = ref.watch(payoutAccountsProvider);

  final wallet = walletAsync.valueOrNull;
  final accounts = accountsAsync.valueOrNull ?? [];

  final availableBalance = wallet?.availableBalance ?? 0.0;
  const minThreshold = EmployeeWallet.minWithdrawalThreshold;
  final shortfall = (minThreshold - availableBalance).clamp(0.0, double.infinity);
  final progressRatio = (availableBalance / minThreshold).clamp(0.0, 1.0);
  final hasPayoutAccount = accounts.any((a) => a.isActive);

  if (wallet == null) {
    return const WithdrawalEligibility(
      isEligible: false,
      availableBalance: 0.0,
      minThreshold: minThreshold,
      shortfall: minThreshold,
      progressRatio: 0.0,
      hasPayoutAccount: false,
      reason: 'Loading wallet data...',
    );
  }

  if (!wallet.isActive) {
    return WithdrawalEligibility(
      isEligible: false,
      availableBalance: availableBalance,
      minThreshold: minThreshold,
      shortfall: shortfall,
      progressRatio: progressRatio,
      hasPayoutAccount: hasPayoutAccount,
      reason: 'Wallet status is ${wallet.status}. Withdrawals are temporarily unavailable.',
    );
  }

  if (availableBalance < minThreshold) {
    return WithdrawalEligibility(
      isEligible: false,
      availableBalance: availableBalance,
      minThreshold: minThreshold,
      shortfall: shortfall,
      progressRatio: progressRatio,
      hasPayoutAccount: hasPayoutAccount,
      reason: 'Minimum withdrawal amount is ₹5,000. You need ₹${shortfall.toStringAsFixed(2)} more.',
    );
  }

  if (!hasPayoutAccount) {
    return WithdrawalEligibility(
      isEligible: false,
      availableBalance: availableBalance,
      minThreshold: minThreshold,
      shortfall: 0.0,
      progressRatio: 1.0,
      hasPayoutAccount: false,
      reason: 'Add a bank account to enable withdrawal requests.',
    );
  }

  return WithdrawalEligibility(
    isEligible: true,
    availableBalance: availableBalance,
    minThreshold: minThreshold,
    shortfall: 0.0,
    progressRatio: 1.0,
    hasPayoutAccount: true,
    reason: null,
  );
});
