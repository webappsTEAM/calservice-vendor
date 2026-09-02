import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/employee_wallet.dart';
import '../domain/payout_account.dart';
import '../domain/wallet_transaction.dart';
import '../domain/wallet_withdrawal.dart';
import 'finance_api.dart';

/// Repository interface and business logic layer for Finance operations.
class FinanceRepository {
  FinanceRepository(this._api);

  final FinanceApi _api;

  /// Retrieves current employee wallet balance and metrics.
  Future<EmployeeWallet> getWalletSummary() async {
    final json = await _api.getWalletSummary();
    return EmployeeWallet.fromJson(json);
  }

  /// Retrieves paginated transactions with optional filters.
  Future<WalletTransactionListResponse> getTransactions({
    int page = 1,
    String? type,
    String? status,
  }) async {
    final json = await _api.getTransactions(page: page, type: type, status: status);
    return WalletTransactionListResponse.fromJson(json);
  }

  /// Retrieves a specific transaction's full details.
  Future<WalletTransaction> getTransactionDetail(int id) async {
    final json = await _api.getTransactionDetail(id);
    return WalletTransaction.fromJson(json);
  }

  /// Retrieves list of all payout / withdrawal requests.
  Future<List<WalletWithdrawal>> getWithdrawals() async {
    final list = await _api.getWithdrawals();
    return list
        .whereType<Map<String, dynamic>>()
        .map(WalletWithdrawal.fromJson)
        .toList();
  }

  /// Submits a new withdrawal request.
  Future<WalletWithdrawal> requestWithdrawal({
    required double amount,
    int? payoutAccountId,
  }) async {
    final json = await _api.requestWithdrawal(
      amount: amount,
      payoutAccountId: payoutAccountId,
    );
    return WalletWithdrawal.fromJson(json);
  }

  /// Cancels an existing pending withdrawal request.
  Future<WalletWithdrawal> cancelWithdrawal(int id) async {
    final json = await _api.cancelWithdrawal(id);
    return WalletWithdrawal.fromJson(json);
  }

  /// Retrieves registered payout bank accounts.
  Future<List<PayoutAccount>> getPayoutAccounts() async {
    final list = await _api.getPayoutAccounts();
    return list
        .whereType<Map<String, dynamic>>()
        .map(PayoutAccount.fromJson)
        .toList();
  }

  /// Registers a new payout bank account.
  Future<PayoutAccount> addPayoutAccount({
    required String accountHolderName,
    required String bankName,
    required String accountNumber,
    required String ifscCode,
    required String accountType,
    bool isPrimary = true,
  }) async {
    final json = await _api.addPayoutAccount(
      accountHolderName: accountHolderName,
      bankName: bankName,
      accountNumber: accountNumber,
      ifscCode: ifscCode,
      accountType: accountType,
      isPrimary: isPrimary,
    );
    return PayoutAccount.fromJson(json);
  }

  /// Deactivates a payout bank account.
  Future<void> deactivatePayoutAccount(int id) async {
    await _api.deactivatePayoutAccount(id);
  }
}

final financeRepositoryProvider = Provider<FinanceRepository>((ref) {
  return FinanceRepository(ref.watch(financeApiProvider));
});
