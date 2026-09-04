import 'package:mobile/core/config/app_config.dart';
import 'package:mobile/core/utils/json_parsing.dart';
import 'package:mobile/features/finance/domain/wallet_withdrawal.dart';

/// Represents a technician wallet from the administrator's perspective.
class AdminWallet {
  const AdminWallet({
    required this.id,
    required this.employeeId,
    required this.employeeName,
    this.employeeAvatar,
    required this.currency,
    required this.status,
    required this.availableBalance,
    required this.pendingBalance,
    required this.lifetimeEarnings,
    required this.totalWithdrawn,
    required this.outstandingRecovery,
    this.nextSettlementDate,
    this.createdAt,
    this.updatedAt,
  });

  factory AdminWallet.fromJson(Map<String, dynamic> json) {
    final empId = parseInt(json['employee_id']) ?? parseInt(json['employee']) ?? 0;
    return AdminWallet(
      id: parseInt(json['id']) ?? 0,
      employeeId: empId,
      employeeName: parseString(json['employee_name']) ??
          parseString(json['employee_display']) ??
          'Technician #$empId',
      employeeAvatar: AppConfig.resolveMediaUrl(
        parseString(json['employee_avatar']) ??
            parseString(json['avatar']) ??
            parseString(json['avatar_url']),
      ),
      currency: parseString(json['currency']) ?? 'INR',
      status: (parseString(json['status']) ?? 'ACTIVE').toUpperCase(),
      availableBalance: parseDouble(json['available_balance']) ?? 0.0,
      pendingBalance: parseDouble(json['pending_balance']) ?? 0.0,
      lifetimeEarnings: parseDouble(json['lifetime_earnings']) ?? 0.0,
      totalWithdrawn: parseDouble(json['total_withdrawn']) ?? 0.0,
      outstandingRecovery: parseDouble(json['outstanding_recovery']) ?? 0.0,
      nextSettlementDate: parseDateTime(json['next_settlement_date']),
      createdAt: parseDateTime(json['created_at']),
      updatedAt: parseDateTime(json['updated_at']),
    );
  }

  final int id;
  final int employeeId;
  final String employeeName;
  final String? employeeAvatar;
  final String currency;
  final String status;
  final double availableBalance;
  final double pendingBalance;
  final double lifetimeEarnings;
  final double totalWithdrawn;
  final double outstandingRecovery;
  final DateTime? nextSettlementDate;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  bool get isActive => status == 'ACTIVE';
  bool get isLocked => status == 'LOCKED';
  bool get isSuspended => status == 'SUSPENDED';
  bool get isClosed => status == 'CLOSED';

  String get statusDisplay {
    switch (status) {
      case 'ACTIVE':
        return 'Active';
      case 'LOCKED':
        return 'Locked';
      case 'SUSPENDED':
        return 'Suspended';
      case 'CLOSED':
        return 'Closed';
      default:
        return status;
    }
  }
}

/// Represents an aggregated summary of all technician wallets for the company.
class AdminWalletSummary {
  const AdminWalletSummary({
    required this.totalWallets,
    required this.totalAvailableBalance,
    required this.totalPendingBalance,
    required this.totalDisbursed,
    required this.activeWalletsCount,
    required this.lockedWalletsCount,
  });

  factory AdminWalletSummary.fromWallets(List<AdminWallet> wallets) {
    double totalAvailable = 0.0;
    double totalPending = 0.0;
    double totalDisbursed = 0.0;
    int activeCount = 0;
    int lockedCount = 0;

    for (final w in wallets) {
      totalAvailable += w.availableBalance;
      totalPending += w.pendingBalance;
      totalDisbursed += w.totalWithdrawn;
      if (w.isActive) activeCount++;
      if (w.isLocked || w.isSuspended) lockedCount++;
    }

    return AdminWalletSummary(
      totalWallets: wallets.length,
      totalAvailableBalance: totalAvailable,
      totalPendingBalance: totalPending,
      totalDisbursed: totalDisbursed,
      activeWalletsCount: activeCount,
      lockedWalletsCount: lockedCount,
    );
  }

  final int totalWallets;
  final double totalAvailableBalance;
  final double totalPendingBalance;
  final double totalDisbursed;
  final int activeWalletsCount;
  final int lockedWalletsCount;
}

/// Represents a withdrawal request from the admin's operational perspective.
class AdminWithdrawal {
  const AdminWithdrawal({
    required this.id,
    required this.amount,
    required this.currency,
    required this.status,
    this.employeeId,
    this.employeeName = 'Technician',
    this.paymentMethod,
    this.payoutAccountId,
    this.payoutAccountDisplay,
    this.bankTransactionId,
    this.failureReason,
    this.remarks,
    this.requestedAt,
    this.processingStartedAt,
    this.completedAt,
    this.failedAt,
    this.cancelledAt,
    this.createdAt,
  });

  factory AdminWithdrawal.fromJson(Map<String, dynamic> json) {
    return AdminWithdrawal(
      id: parseInt(json['id']) ?? 0,
      amount: parseDouble(json['amount']) ?? 0.0,
      currency: parseString(json['currency']) ?? 'INR',
      status: (parseString(json['status']) ?? 'REQUESTED').toUpperCase(),
      employeeId: parseInt(json['employee']) ?? parseInt(json['employee_id']),
      employeeName: parseString(json['employee_name']) ??
          parseString(json['employee_display']) ??
          'Technician',
      paymentMethod: parseString(json['payment_method']) ?? 'BANK_TRANSFER',
      payoutAccountId: parseInt(json['payout_account_id']),
      payoutAccountDisplay: json['payout_account_display'] is Map<String, dynamic>
          ? PayoutAccountSummary.fromJson(json['payout_account_display'] as Map<String, dynamic>)
          : null,
      bankTransactionId: parseString(json['bank_transaction_id']),
      failureReason: parseString(json['failure_reason']),
      remarks: parseString(json['remarks']),
      requestedAt: parseDateTime(json['requested_at']),
      processingStartedAt: parseDateTime(json['processing_started_at']),
      completedAt: parseDateTime(json['completed_at']),
      failedAt: parseDateTime(json['failed_at']),
      cancelledAt: parseDateTime(json['cancelled_at']),
      createdAt: parseDateTime(json['created_at']),
    );
  }

  final int id;
  final double amount;
  final String currency;
  final String status;
  final int? employeeId;
  final String employeeName;
  final String? paymentMethod;
  final int? payoutAccountId;
  final PayoutAccountSummary? payoutAccountDisplay;
  final String? bankTransactionId;
  final String? failureReason;
  final String? remarks;
  final DateTime? requestedAt;
  final DateTime? processingStartedAt;
  final DateTime? completedAt;
  final DateTime? failedAt;
  final DateTime? cancelledAt;
  final DateTime? createdAt;

  bool get isRequested => status == 'REQUESTED';
  bool get isProcessing => status == 'PROCESSING';
  bool get isCompleted => status == 'COMPLETED';
  bool get isFailed => status == 'FAILED';
  bool get isCancelled => status == 'CANCELLED';

  String get statusDisplay {
    switch (status) {
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
}

/// Represents a bank account for verification from the admin's perspective.
class AdminBankAccount {
  const AdminBankAccount({
    required this.id,
    required this.employeeId,
    required this.employeeName,
    required this.bankName,
    required this.accountHolderName,
    required this.accountNumberLast4,
    required this.ifscCode,
    required this.accountType,
    required this.verificationStatus,
    required this.isPrimary,
    required this.isActive,
    this.createdAt,
  });

  factory AdminBankAccount.fromJson(Map<String, dynamic> json) {
    return AdminBankAccount(
      id: parseInt(json['id']) ?? 0,
      employeeId: parseInt(json['employee']) ??
          parseInt(json['employee_id']) ?? 0,
      employeeName: parseString(json['employee_name']) ??
          parseString(json['employee_display']) ??
          'Technician',
      bankName: parseString(json['bank_name']) ?? 'Bank Account',
      accountHolderName: parseString(json['account_holder_name']) ?? '',
      accountNumberLast4: parseString(json['account_number_last4']) ?? '••••',
      ifscCode: parseString(json['ifsc_code']) ?? '',
      accountType: (parseString(json['account_type']) ?? 'SAVINGS').toUpperCase(),
      verificationStatus: (parseString(json['verification_status']) ?? 'PENDING_REVIEW').toUpperCase(),
      isPrimary: parseBool(json['is_primary'], fallback: false),
      isActive: parseBool(json['is_active'], fallback: true),
      createdAt: parseDateTime(json['created_at']),
    );
  }

  final int id;
  final int employeeId;
  final String employeeName;
  final String bankName;
  final String accountHolderName;
  final String accountNumberLast4;
  final String ifscCode;
  final String accountType;
  final String verificationStatus;
  final bool isPrimary;
  final bool isActive;
  final DateTime? createdAt;

  String get maskedAccountNumber => '•••• $accountNumberLast4';

  bool get isVerified => verificationStatus == 'VERIFIED';
  bool get isPendingReview => verificationStatus == 'PENDING_REVIEW';
  bool get isRejected => verificationStatus == 'REJECTED';

  String get statusDisplay {
    switch (verificationStatus) {
      case 'VERIFIED':
        return 'Verified';
      case 'PENDING_REVIEW':
        return 'Pending Review';
      case 'REJECTED':
        return 'Rejected';
      default:
        return verificationStatus;
    }
  }

  String get accountTypeDisplay {
    switch (accountType) {
      case 'CURRENT':
        return 'Current Account';
      case 'SAVINGS':
      default:
        return 'Savings Account';
    }
  }
}
