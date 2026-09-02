import 'package:flutter/material.dart';

import '../../../core/utils/json_parsing.dart';

/// Represents a technician's registered bank payout account.
///
/// Security: Full bank account numbers are NEVER exposed or stored locally.
/// Only the masked `account_number_last4` (`•••• 1234`) is returned by the server.
///
/// Corresponds to backend's `GET /api/workforce/wallet/payout-accounts/` (EmployeePayoutAccountSerializer).
class PayoutAccount {
  const PayoutAccount({
    required this.id,
    required this.accountHolderName,
    required this.bankName,
    required this.accountNumberLast4,
    required this.ifscCode,
    required this.accountType,
    required this.verificationStatus,
    required this.isPrimary,
    required this.isActive,
    this.createdAt,
  });

  factory PayoutAccount.fromJson(Map<String, dynamic> json) {
    return PayoutAccount(
      id: parseInt(json['id']) ?? 0,
      accountHolderName: parseString(json['account_holder_name']) ?? '',
      bankName: parseString(json['bank_name']) ?? '',
      accountNumberLast4: parseString(json['account_number_last4']) ?? '••••',
      ifscCode: parseString(json['ifsc_code']) ?? '',
      accountType: parseString(json['account_type']) ?? 'SAVINGS',
      verificationStatus: parseString(json['verification_status']) ?? 'PENDING',
      isPrimary: parseBool(json['is_primary']),
      isActive: parseBool(json['is_active'], fallback: true),
      createdAt: parseDateTime(json['created_at']),
    );
  }

  final int id;
  final String accountHolderName;
  final String bankName;
  final String accountNumberLast4;
  final String ifscCode;
  final String accountType;
  final String verificationStatus;
  final bool isPrimary;
  final bool isActive;
  final DateTime? createdAt;

  bool get isVerified => verificationStatus.toUpperCase() == 'VERIFIED';
  bool get isPending => verificationStatus.toUpperCase() == 'PENDING';
  bool get isRejected => verificationStatus.toUpperCase() == 'REJECTED';

  /// Masked account representation `•••• 1234`
  String get maskedAccountNumber {
    if (accountNumberLast4.isEmpty) return '••••';
    return '•••• $accountNumberLast4';
  }

  /// Display text for account type.
  String get accountTypeDisplay {
    if (accountType.toUpperCase() == 'CURRENT') return 'Current Account';
    return 'Savings Account';
  }

  /// Status badge color.
  Color get statusColor {
    if (isVerified) return const Color(0xFF059669); // Emerald
    if (isPending) return const Color(0xFFD97706); // Amber
    if (isRejected) return const Color(0xFFE11D48); // Rose
    return const Color(0xFF64748B);
  }

  /// Status badge text.
  String get statusDisplay {
    switch (verificationStatus.toUpperCase()) {
      case 'VERIFIED':
        return 'Verified';
      case 'PENDING':
        return 'Pending Verification';
      case 'REJECTED':
        return 'Rejected';
      default:
        return verificationStatus;
    }
  }
}
