import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile/core/utils/json_parsing.dart';

import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';
import 'package:mobile/features/admin/data/admin_finance_api.dart';

/// Repository handling data mapping, business parsing, and errors for Admin Finance.
class AdminFinanceRepository {
  AdminFinanceRepository(this._api);

  final AdminFinanceApi _api;

  /// Fetches all technician wallets for the company.
  Future<List<AdminWallet>> fetchWallets() async {
    final rawList = await _api.fetchWallets();
    return rawList
        .whereType<Map<String, dynamic>>()
        .map(AdminWallet.fromJson)
        .toList();
  }

  /// Fetches summary for a single technician's wallet.
  Future<AdminWallet> fetchWalletSummary(int employeeId) async {
    final raw = await _api.fetchWalletSummary(employeeId);
    return AdminWallet.fromJson(raw);
  }

  /// Updates status of a technician wallet (ACTIVE, LOCKED, SUSPENDED, CLOSED).
  Future<AdminWallet> updateWalletStatus({
    required int employeeId,
    required String status,
    String reason = '',
  }) async {
    final raw = await _api.updateWalletStatus(
      employeeId: employeeId,
      status: status,
      reason: reason,
    );
    return AdminWallet.fromJson(raw);
  }

  /// Posts manual credit/debit adjustment.
  Future<AdminWallet> postAdjustment({
    required int employeeId,
    required String direction,
    required double amount,
    required String reason,
  }) async {
    final raw = await _api.postAdjustment(
      employeeId: employeeId,
      direction: direction,
      amount: amount,
      reason: reason,
    );
    return AdminWallet.fromJson(raw);
  }

  /// Fetches paginated transaction ledger for a technician.
  Future<WalletTransactionListResponse> fetchEmployeeTransactions({
    required int employeeId,
    int page = 1,
  }) async {
    final raw = await _api.fetchEmployeeTransactions(
      employeeId: employeeId,
      page: page,
    );
    return WalletTransactionListResponse.fromJson(raw);
  }

  /// Fetches all company payout requests.
  Future<List<AdminWithdrawal>> fetchWithdrawals({String? status}) async {
    final rawList = await _api.fetchWithdrawals(status: status);
    return rawList
        .whereType<Map<String, dynamic>>()
        .map(AdminWithdrawal.fromJson)
        .toList();
  }

  /// Starts processing a withdrawal request.
  Future<AdminWithdrawal> startProcessingWithdrawal(int withdrawalId) async {
    final raw = await _api.startProcessingWithdrawal(withdrawalId);
    return AdminWithdrawal.fromJson(raw);
  }

  /// Marks a payout request completed with bank UTR.
  Future<AdminWithdrawal> completeWithdrawal({
    required int withdrawalId,
    required String bankTransactionId,
  }) async {
    final raw = await _api.completeWithdrawal(
      withdrawalId: withdrawalId,
      bankTransactionId: bankTransactionId,
    );
    return AdminWithdrawal.fromJson(raw);
  }

  /// Marks a payout request failed with reason.
  Future<AdminWithdrawal> failWithdrawal({
    required int withdrawalId,
    required String failureReason,
  }) async {
    final raw = await _api.failWithdrawal(
      withdrawalId: withdrawalId,
      failureReason: failureReason,
    );
    return AdminWithdrawal.fromJson(raw);
  }

  /// Verifies or rejects a technician payout account.
  Future<Map<String, dynamic>> verifyPayoutAccount({
    required int accountId,
    required String verificationStatus,
  }) async {
    return _api.verifyPayoutAccount(
      accountId: accountId,
      verificationStatus: verificationStatus,
    );
  }

  final List<AdminBankAccount> _manuallyAddedAccounts = [];

  /// Adds a payout bank account.
  Future<AdminBankAccount> addPayoutAccount({
    required String accountHolderName,
    required String bankName,
    required String accountNumber,
    required String ifscCode,
    required String accountType,
    bool isPrimary = true,
  }) async {
    final raw = await _api.addPayoutAccount(
      accountHolderName: accountHolderName,
      bankName: bankName,
      accountNumber: accountNumber,
      ifscCode: ifscCode,
      accountType: accountType,
      isPrimary: isPrimary,
    );

    final last4 = accountNumber.length >= 4
        ? accountNumber.substring(accountNumber.length - 4)
        : '••••';

    final account = AdminBankAccount(
      id: parseInt(raw['id']) ?? DateTime.now().millisecondsSinceEpoch,
      employeeId: parseInt(raw['employee']) ??
          parseInt(raw['employee_id']) ?? 0,
      employeeName: parseString(raw['employee_name']) ??
          parseString(raw['employee_display']) ??
          accountHolderName,
      bankName: parseString(raw['bank_name']) ?? bankName,
      accountHolderName: parseString(raw['account_holder_name']) ?? accountHolderName,
      accountNumberLast4: parseString(raw['account_number_last4']) ?? last4,
      ifscCode: parseString(raw['ifsc_code']) ?? ifscCode,
      accountType: (parseString(raw['account_type']) ?? accountType).toUpperCase(),
      verificationStatus: (parseString(raw['verification_status']) ?? 'PENDING_REVIEW').toUpperCase(),
      isPrimary: parseBool(raw['is_primary'], fallback: isPrimary),
      isActive: parseBool(raw['is_active'], fallback: true),
      createdAt: DateTime.now(),
    );

    _manuallyAddedAccounts.removeWhere((a) =>
        a.id == account.id ||
        (a.accountNumberLast4 == account.accountNumberLast4 && a.bankName == account.bankName));
    _manuallyAddedAccounts.insert(0, account);
    return account;
  }

  /// Extracts and aggregates all bank accounts attached to company payout requests and direct records.
  Future<List<AdminBankAccount>> fetchBankAccounts() async {
    final Map<int, AdminBankAccount> accountMap = {};

    // 1. Fetch direct payout accounts if available
    try {
      final directAccountsRaw = await _api.fetchPayoutAccounts();
      for (final raw in directAccountsRaw) {
        if (raw is Map<String, dynamic>) {
          final acct = AdminBankAccount.fromJson(raw);
          accountMap[acct.id] = acct;
        }
      }
    } catch (_) {
      // Direct accounts might be scoped to employee profile
    }

    // 2. Fetch payout accounts attached to company withdrawals
    try {
      final withdrawals = await fetchWithdrawals();
      for (final w in withdrawals) {
        if (w.payoutAccountId != null && w.payoutAccountDisplay != null) {
          final display = w.payoutAccountDisplay!;
          if (!accountMap.containsKey(w.payoutAccountId!)) {
            accountMap[w.payoutAccountId!] = AdminBankAccount(
              id: w.payoutAccountId!,
              employeeId: w.employeeId ?? 0,
              employeeName: w.employeeName,
              bankName: display.bankName ?? 'Bank Account',
              accountHolderName: display.accountHolderName ?? w.employeeName,
              accountNumberLast4: display.accountNumberLast4 ?? '••••',
              ifscCode: '',
              accountType: 'SAVINGS',
              verificationStatus: w.isCompleted ? 'VERIFIED' : 'PENDING_REVIEW',
              isPrimary: true,
              isActive: true,
              createdAt: w.createdAt,
            );
          }
        }
      }
    } catch (_) {}

    // 3. Include any manually added accounts
    for (final acct in _manuallyAddedAccounts) {
      accountMap[acct.id] = acct;
    }

    return accountMap.values.toList();
  }
}

final adminFinanceRepositoryProvider = Provider<AdminFinanceRepository>((ref) {
  return AdminFinanceRepository(ref.watch(adminFinanceApiProvider));
});
