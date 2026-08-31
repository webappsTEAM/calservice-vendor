import 'package:flutter/material.dart';

import '../../../core/utils/json_parsing.dart';

/// Embedded payout account details attached to a withdrawal record.
class PayoutAccountSummary {
  const PayoutAccountSummary({
    required this.id,
    this.bankName,
    this.accountNumberLast4,
    this.accountHolderName,
  });

  factory PayoutAccountSummary.fromJson(Map<String, dynamic> json) {
    return PayoutAccountSummary(
      id: parseInt(json['id']) ?? 0,
      bankName: parseString(json['bank_name']),
      accountNumberLast4: parseString(json['account_number_last4']),
      accountHolderName: parseString(json['account_holder_name']),
    );
  }

  final int id;
  final String? bankName;
  final String? accountNumberLast4;
  final String? accountHolderName;

  String get maskedAccountDisplay {
    if (accountNumberLast4 == null || accountNumberLast4!.isEmpty) return 'Bank Account';
    return '•••• $accountNumberLast4';
  }
}

/// Represents a technician's withdrawal / payout request.
///
/// Corresponds to backend's `GET /api/workforce/wallet/withdrawals/` (EmployeeWalletWithdrawalSerializer).
class WalletWithdrawal {
  const WalletWithdrawal({
    required this.id,
    required this.amount,
    required this.currency,
    required this.status,
    this.paymentMethod,
    this.payoutAccountId,
    this.payoutAccountDisplay,
    this.requestedAt,
    this.processingStartedAt,
    this.completedAt,
    this.failedAt,
    this.cancelledAt,
    this.bankTransactionId,
    this.failureReason,
    this.remarks,
    this.createdAt,
    this.updatedAt,
  });

  factory WalletWithdrawal.fromJson(Map<String, dynamic> json) {
    final accountJson = json['payout_account_display'];
    return WalletWithdrawal(
      id: parseInt(json['id']) ?? 0,
      amount: parseDouble(json['amount']) ?? 0.0,
      currency: parseString(json['currency']) ?? 'INR',
      status: parseString(json['status']) ?? 'REQUESTED',
      paymentMethod: parseString(json['payment_method']) ?? 'BANK_TRANSFER',
      payoutAccountId: parseInt(json['payout_account_id']),
      payoutAccountDisplay: accountJson is Map<String, dynamic>
          ? PayoutAccountSummary.fromJson(accountJson)
          : null,
      requestedAt: parseDateTime(json['requested_at']),
      processingStartedAt: parseDateTime(json['processing_started_at']),
      completedAt: parseDateTime(json['completed_at']),
      failedAt: parseDateTime(json['failed_at']),
      cancelledAt: parseDateTime(json['cancelled_at']),
      bankTransactionId: parseString(json['bank_transaction_id']),
      failureReason: parseString(json['failure_reason']),
      remarks: parseString(json['remarks']),
      createdAt: parseDateTime(json['created_at']),
      updatedAt: parseDateTime(json['updated_at']),
    );
  }

  final int id;
  final double amount;
  final String currency;
  final String status;
  final String? paymentMethod;
  final int? payoutAccountId;
  final PayoutAccountSummary? payoutAccountDisplay;
  final DateTime? requestedAt;
  final DateTime? processingStartedAt;
  final DateTime? completedAt;
  final DateTime? failedAt;
  final DateTime? cancelledAt;
  final String? bankTransactionId;
  final String? failureReason;
  final String? remarks;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  bool get isRequested => status.toUpperCase() == 'REQUESTED';
  bool get isProcessing => status.toUpperCase() == 'PROCESSING';
  bool get isCompleted => status.toUpperCase() == 'COMPLETED';
  bool get isFailed => status.toUpperCase() == 'FAILED';
  bool get isCancelled => status.toUpperCase() == 'CANCELLED';

  /// Technician is allowed to cancel withdrawal only when in REQUESTED status.
  bool get isCancellable => isRequested;

  /// Display text for withdrawal status badge.
  String get statusDisplay {
    switch (status.toUpperCase()) {
      case 'REQUESTED':
        return 'Requested';
      case 'PROCESSING':
        return 'Processing';
      case 'COMPLETED':
        return 'Completed';
      case 'FAILED':
        return 'Failed';
      case 'CANCELLED':
        return 'Cancelled';
      default:
        return status;
    }
  }

  /// Badge color for status.
  Color get statusColor {
    switch (status.toUpperCase()) {
      case 'REQUESTED':
        return const Color(0xFFD97706); // Amber
      case 'PROCESSING':
        return const Color(0xFF2563EB); // Blue
      case 'COMPLETED':
        return const Color(0xFF059669); // Emerald
      case 'FAILED':
        return const Color(0xFFE11D48); // Rose
      case 'CANCELLED':
        return const Color(0xFF64748B); // Slate
      default:
        return const Color(0xFF64748B);
    }
  }
}
