import 'package:flutter/material.dart';

import '../../../core/utils/json_parsing.dart';

/// Single transaction record in the technician's wallet ledger.
///
/// Corresponds to backend's `GET /api/workforce/wallet/transactions/` (EmployeeWalletTransactionSerializer).
class WalletTransaction {
  const WalletTransaction({
    required this.id,
    this.referenceType,
    this.referenceId,
    required this.transactionType,
    required this.direction,
    required this.status,
    required this.amount,
    this.grossAmount,
    this.earnRateSnapshot,
    this.platformDeductionAmount,
    this.balanceBefore,
    this.balanceAfter,
    this.balanceType,
    this.settlementReleaseAt,
    this.releasedAt,
    this.description,
    this.serviceRequestId,
    this.jobPaymentId,
    this.withdrawalId,
    this.metadata,
    this.createdAt,
  });

  factory WalletTransaction.fromJson(Map<String, dynamic> json) {
    return WalletTransaction(
      id: parseInt(json['id']) ?? 0,
      referenceType: parseString(json['reference_type']),
      referenceId: parseString(json['reference_id']),
      transactionType: parseString(json['transaction_type']) ?? 'SERVICE_EARNING',
      direction: parseString(json['direction']) ?? 'CREDIT',
      status: parseString(json['status']) ?? 'COMPLETED',
      amount: parseDouble(json['amount']) ?? 0.0,
      grossAmount: parseDouble(json['gross_amount']),
      earnRateSnapshot: parseDouble(json['earn_rate_snapshot']),
      platformDeductionAmount: parseDouble(json['platform_deduction_amount']),
      balanceBefore: parseDouble(json['balance_before']),
      balanceAfter: parseDouble(json['balance_after']),
      balanceType: parseString(json['balance_type']),
      settlementReleaseAt: parseDateTime(json['settlement_release_at']),
      releasedAt: parseDateTime(json['released_at']),
      description: parseString(json['description']),
      serviceRequestId: parseInt(json['service_request_id']),
      jobPaymentId: parseInt(json['job_payment_id']),
      withdrawalId: parseInt(json['withdrawal_id']),
      metadata: json['metadata'] is Map<String, dynamic>
          ? json['metadata'] as Map<String, dynamic>
          : null,
      createdAt: parseDateTime(json['created_at']),
    );
  }

  final int id;
  final String? referenceType;
  final String? referenceId;
  final String transactionType;
  final String direction;
  final String status;
  final double amount;
  final double? grossAmount;
  final double? earnRateSnapshot;
  final double? platformDeductionAmount;
  final double? balanceBefore;
  final double? balanceAfter;
  final String? balanceType;
  final DateTime? settlementReleaseAt;
  final DateTime? releasedAt;
  final String? description;
  final int? serviceRequestId;
  final int? jobPaymentId;
  final int? withdrawalId;
  final Map<String, dynamic>? metadata;
  final DateTime? createdAt;

  bool get isCredit => direction.toUpperCase() == 'CREDIT';
  bool get isDebit => direction.toUpperCase() == 'DEBIT';

  bool get isCompleted => status.toUpperCase() == 'COMPLETED';
  bool get isPendingSettlement => status.toUpperCase() == 'PENDING_SETTLEMENT';
  bool get isReversed => status.toUpperCase() == 'REVERSED';
  bool get isFailed => status.toUpperCase() == 'FAILED';

  /// Human-friendly display title for transaction type.
  String get displayTitle {
    switch (transactionType.toUpperCase()) {
      case 'SERVICE_EARNING':
        return 'Service Earning';
      case 'PLATFORM_DEDUCTION':
        return 'Platform Commission';
      case 'REFUND':
        return 'Customer Refund';
      case 'RECOVERY_DEBIT':
        return 'Recovery Debit';
      case 'RECOVERY_CREDIT':
        return 'Recovery Credit';
      case 'WITHDRAWAL':
        return 'Payout Withdrawal';
      case 'WITHDRAWAL_REVERSAL':
        return 'Withdrawal Reversal';
      case 'ADJUSTMENT_CREDIT':
        return 'Manual Credit Adjustment';
      case 'ADJUSTMENT_DEBIT':
        return 'Manual Debit Adjustment';
      case 'SETTLEMENT_RELEASE':
        return 'T+7 Settlement Released';
      case 'REVERSAL':
        return 'Transaction Reversal';
      default:
        return transactionType.replaceAll('_', ' ');
    }
  }

  /// Icon corresponding to transaction type.
  IconData get iconData {
    switch (transactionType.toUpperCase()) {
      case 'SERVICE_EARNING':
        return Icons.handyman_rounded;
      case 'PLATFORM_DEDUCTION':
        return Icons.pie_chart_outline_rounded;
      case 'REFUND':
        return Icons.replay_rounded;
      case 'RECOVERY_DEBIT':
      case 'RECOVERY_CREDIT':
        return Icons.sync_problem_rounded;
      case 'WITHDRAWAL':
        return Icons.account_balance_wallet_outlined;
      case 'WITHDRAWAL_REVERSAL':
        return Icons.undo_rounded;
      case 'ADJUSTMENT_CREDIT':
      case 'ADJUSTMENT_DEBIT':
        return Icons.tune_rounded;
      case 'SETTLEMENT_RELEASE':
        return Icons.verified_outlined;
      default:
        return isCredit ? Icons.arrow_downward_rounded : Icons.arrow_upward_rounded;
    }
  }

  /// Color accent for icon/badge.
  Color get statusColor {
    if (isFailed) return const Color(0xFFE11D48);
    if (isReversed) return const Color(0xFF64748B);
    if (isPendingSettlement) return const Color(0xFFD97706);
    return isCredit ? const Color(0xFF059669) : const Color(0xFF2563EB);
  }
}

/// Paginated response from GET /wallet/transactions/
class WalletTransactionListResponse {
  const WalletTransactionListResponse({
    required this.count,
    required this.page,
    required this.pageSize,
    required this.totalPages,
    required this.results,
  });

  factory WalletTransactionListResponse.fromJson(Map<String, dynamic> json) {
    final resultsJson = json['results'];
    final items = resultsJson is List
        ? resultsJson
            .whereType<Map<String, dynamic>>()
            .map(WalletTransaction.fromJson)
            .toList()
        : <WalletTransaction>[];

    return WalletTransactionListResponse(
      count: parseInt(json['count']) ?? 0,
      page: parseInt(json['page']) ?? 1,
      pageSize: parseInt(json['page_size']) ?? 25,
      totalPages: parseInt(json['total_pages']) ?? 1,
      results: items,
    );
  }

  final int count;
  final int page;
  final int pageSize;
  final int totalPages;
  final List<WalletTransaction> results;
}
