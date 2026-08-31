import '../../../core/utils/json_parsing.dart';

/// Represents the authenticated technician's wallet summary.
///
/// Corresponds to backend's `GET /api/workforce/wallet/` (EmployeeWalletSummarySerializer).
class EmployeeWallet {
  const EmployeeWallet({
    required this.id,
    required this.employeeId,
    this.employeeName,
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

  factory EmployeeWallet.fromJson(Map<String, dynamic> json) {
    return EmployeeWallet(
      id: parseInt(json['id']) ?? 0,
      employeeId: parseInt(json['employee_id']) ?? 0,
      employeeName: parseString(json['employee_name']),
      currency: parseString(json['currency']) ?? 'INR',
      status: parseString(json['status']) ?? 'ACTIVE',
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
  final String? employeeName;
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

  bool get isActive => status.toUpperCase() == 'ACTIVE';
  bool get isSuspended => status.toUpperCase() == 'SUSPENDED';
  bool get isLocked => status.toUpperCase() == 'LOCKED';
  bool get isClosed => status.toUpperCase() == 'CLOSED';

  /// Minimum withdrawal amount threshold per business rule (₹5,000).
  static const double minWithdrawalThreshold = 5000.0;

  /// Whether the technician can withdraw (active wallet & available balance >= min threshold).
  bool get isEligibleForWithdrawal =>
      isActive && availableBalance >= minWithdrawalThreshold;

  /// Shortfall remaining before reaching minimum withdrawal threshold.
  double get withdrawalShortfall {
    if (availableBalance >= minWithdrawalThreshold) return 0.0;
    return minWithdrawalThreshold - availableBalance;
  }

  /// Progress ratio (0.0 to 1.0) towards minimum withdrawal threshold.
  double get withdrawalProgressRatio {
    if (minWithdrawalThreshold <= 0) return 1.0;
    return (availableBalance / minWithdrawalThreshold).clamp(0.0, 1.0);
  }
}
