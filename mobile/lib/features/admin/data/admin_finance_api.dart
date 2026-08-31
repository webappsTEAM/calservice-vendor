import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/network/api_client.dart';

/// Low-level HTTP client for all Admin Finance & Wallet operations.
class AdminFinanceApi {
  AdminFinanceApi(this._dio);

  final Dio _dio;

  static final _options = Options(
    receiveTimeout: const Duration(seconds: 30),
    sendTimeout: const Duration(seconds: 30),
  );

  /// `GET /workforce/admin/wallet/employees/`
  /// Lists all technician wallets in the admin's company.
  Future<List<dynamic>> fetchWallets() async {
    final response = await _dio.get(
      '/workforce/admin/wallet/employees/',
      options: _options,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// `GET /workforce/admin/wallet/employees/{employee_id}/`
  /// Fetches summary for a specific technician's wallet.
  Future<Map<String, dynamic>> fetchWalletSummary(int employeeId) async {
    final response = await _dio.get(
      '/workforce/admin/wallet/employees/$employeeId/',
      options: _options,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// `POST /workforce/admin/wallet/employees/{employee_id}/freeze/`
  /// Updates the status of a technician wallet (ACTIVE, LOCKED, SUSPENDED, CLOSED).
  Future<Map<String, dynamic>> updateWalletStatus({
    required int employeeId,
    required String status,
    String reason = '',
  }) async {
    final response = await _dio.post(
      '/workforce/admin/wallet/employees/$employeeId/freeze/',
      data: {
        'status': status,
        'reason': reason,
      },
      options: _options,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// `POST /workforce/admin/wallet/employees/{employee_id}/adjustment/`
  /// Posts a manual credit/debit adjustment to a technician's wallet.
  Future<Map<String, dynamic>> postAdjustment({
    required int employeeId,
    required String direction, // 'CREDIT' or 'DEBIT'
    required double amount,
    required String reason,
  }) async {
    final response = await _dio.post(
      '/workforce/admin/wallet/employees/$employeeId/adjustment/',
      data: {
        'direction': direction,
        'amount': amount.toStringAsFixed(2),
        'reason': reason,
      },
      options: _options,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// `GET /workforce/admin/wallet/employees/{employee_id}/transactions/`
  /// Fetches the paginated transaction ledger for a technician.
  Future<Map<String, dynamic>> fetchEmployeeTransactions({
    required int employeeId,
    int page = 1,
  }) async {
    final response = await _dio.get(
      '/workforce/admin/wallet/employees/$employeeId/transactions/',
      queryParameters: {'page': page},
      options: _options,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// `GET /workforce/admin/wallet/withdrawals/`
  /// Lists all payout requests in the company, optionally filtered by status.
  Future<List<dynamic>> fetchWithdrawals({String? status}) async {
    final queryParams = <String, dynamic>{};
    if (status != null && status.isNotEmpty && status != 'ALL') {
      queryParams['status'] = status;
    }
    final response = await _dio.get(
      '/workforce/admin/wallet/withdrawals/',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
      options: _options,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// `POST /workforce/admin/wallet/withdrawals/{id}/process/`
  /// Transitions a withdrawal from REQUESTED to PROCESSING.
  Future<Map<String, dynamic>> startProcessingWithdrawal(int withdrawalId) async {
    final response = await _dio.post(
      '/workforce/admin/wallet/withdrawals/$withdrawalId/process/',
      options: _options,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// `POST /workforce/admin/wallet/withdrawals/{id}/complete/`
  /// Marks a withdrawal COMPLETED with bank transaction / UTR reference.
  Future<Map<String, dynamic>> completeWithdrawal({
    required int withdrawalId,
    required String bankTransactionId,
  }) async {
    final response = await _dio.post(
      '/workforce/admin/wallet/withdrawals/$withdrawalId/complete/',
      data: {'bank_transaction_id': bankTransactionId},
      options: _options,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// `POST /workforce/admin/wallet/withdrawals/{id}/fail/`
  /// Marks a withdrawal FAILED with reason and automatically reverses wallet balance.
  Future<Map<String, dynamic>> failWithdrawal({
    required int withdrawalId,
    required String failureReason,
  }) async {
    final response = await _dio.post(
      '/workforce/admin/wallet/withdrawals/$withdrawalId/fail/',
      data: {'failure_reason': failureReason},
      options: _options,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// `POST /workforce/admin/wallet/payout-accounts/{id}/verify/`
  /// Verifies or rejects a technician payout account (VERIFIED or REJECTED).
  Future<Map<String, dynamic>> verifyPayoutAccount({
    required int accountId,
    required String verificationStatus, // 'VERIFIED' or 'REJECTED'
  }) async {
    final response = await _dio.post(
      '/workforce/admin/wallet/payout-accounts/$accountId/verify/',
      data: {'verification_status': verificationStatus},
      options: _options,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// `POST /workforce/wallet/payout-accounts/`
  /// Adds a new bank account.
  Future<Map<String, dynamic>> addPayoutAccount({
    required String accountHolderName,
    required String bankName,
    required String accountNumber,
    required String ifscCode,
    required String accountType,
    bool isPrimary = true,
  }) async {
    final response = await _dio.post(
      '/workforce/wallet/payout-accounts/',
      data: {
        'account_holder_name': accountHolderName,
        'bank_name': bankName,
        'account_number': accountNumber,
        'ifsc_code': ifscCode.toUpperCase().trim(),
        'account_type': accountType.toUpperCase().trim(),
        'is_primary': isPrimary,
      },
      options: _options,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// `GET /workforce/wallet/payout-accounts/`
  /// Fetches payout accounts.
  Future<List<dynamic>> fetchPayoutAccounts() async {
    final response = await _dio.get(
      '/workforce/wallet/payout-accounts/',
      options: _options,
    );
    final data = response.data;
    return data is List ? data : const [];
  }
}

final adminFinanceApiProvider = Provider<AdminFinanceApi>((ref) {
  return AdminFinanceApi(ref.watch(apiClientProvider));
});
