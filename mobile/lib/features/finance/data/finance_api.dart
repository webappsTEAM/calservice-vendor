import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

/// Low-level network calls for the Finance / Employee Wallet module.
///
/// Endpoints in backend `vendor_wallet/urls.py` mounted at `/api/workforce/wallet/`:
/// - `GET /workforce/wallet/`
/// - `GET /workforce/wallet/transactions/`
/// - `GET /workforce/wallet/transactions/<id>/`
/// - `GET /workforce/wallet/withdrawals/`
/// - `POST /workforce/wallet/withdrawals/`
/// - `POST /workforce/wallet/withdrawals/<id>/cancel/`
/// - `GET /workforce/wallet/payout-accounts/`
/// - `POST /workforce/wallet/payout-accounts/`
/// - `DELETE /workforce/wallet/payout-accounts/<id>/`
class FinanceApi {
  FinanceApi(this._dio);

  final Dio _dio;

  /// Fetches technician's wallet summary (available balance, pending hold, earnings, etc.).
  Future<Map<String, dynamic>> getWalletSummary() async {
    final response = await _dio.get('/workforce/wallet/');
    return response.data as Map<String, dynamic>;
  }

  /// Fetches paginated transaction ledger entries with optional filters.
  Future<Map<String, dynamic>> getTransactions({
    int page = 1,
    String? type,
    String? status,
  }) async {
    final queryParams = <String, dynamic>{'page': page};
    if (type != null && type.isNotEmpty && type != 'ALL') {
      queryParams['type'] = type;
    }
    if (status != null && status.isNotEmpty && status != 'ALL') {
      queryParams['status'] = status;
    }

    final response = await _dio.get(
      '/workforce/wallet/transactions/',
      queryParameters: queryParams,
    );
    return response.data as Map<String, dynamic>;
  }

  /// Fetches single transaction details by ID.
  Future<Map<String, dynamic>> getTransactionDetail(int id) async {
    final response = await _dio.get('/workforce/wallet/transactions/$id/');
    return response.data as Map<String, dynamic>;
  }

  /// Fetches all withdrawal / payout requests for the logged-in technician.
  Future<List<dynamic>> getWithdrawals() async {
    final response = await _dio.get('/workforce/wallet/withdrawals/');
    return response.data as List<dynamic>;
  }

  /// Requests a self-service withdrawal.
  Future<Map<String, dynamic>> requestWithdrawal({
    required double amount,
    int? payoutAccountId,
  }) async {
    final payload = <String, dynamic>{
      'amount': amount.toStringAsFixed(2),
    };
    if (payoutAccountId != null) {
      payload['payout_account_id'] = payoutAccountId;
    }

    final response = await _dio.post(
      '/workforce/wallet/withdrawals/',
      data: payload,
    );
    return response.data as Map<String, dynamic>;
  }

  /// Cancels a pending withdrawal request in REQUESTED status.
  Future<Map<String, dynamic>> cancelWithdrawal(int id) async {
    final response = await _dio.post('/workforce/wallet/withdrawals/$id/cancel/');
    return response.data as Map<String, dynamic>;
  }

  /// Lists technician's active payout bank accounts.
  Future<List<dynamic>> getPayoutAccounts() async {
    final response = await _dio.get('/workforce/wallet/payout-accounts/');
    return response.data as List<dynamic>;
  }

  /// Adds a new payout bank account.
  ///
  /// Security: `account_number` is write-only transmitted over TLS to backend;
  /// backend stores only last 4 digits.
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
    );
    return response.data as Map<String, dynamic>;
  }

  /// Deactivates / removes a payout bank account.
  Future<void> deactivatePayoutAccount(int id) async {
    await _dio.delete('/workforce/wallet/payout-accounts/$id/');
  }
}

final financeApiProvider = Provider<FinanceApi>((ref) {
  return FinanceApi(ref.watch(apiClientProvider));
});
