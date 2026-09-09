import '../../../core/utils/json_parsing.dart';

/// Represents an individual worker's registration record under the
/// Code on Social Security 2020 / 2026 Central Rules.
///
/// Backed by `/api/workforce/admin/social-security/`.
class AdminSocialSecurityRegistration {
  const AdminSocialSecurityRegistration({
    required this.registrationId,
    required this.employeeId,
    required this.employeeName,
    this.daysWorkedCurrentFy = 0,
    this.financialYearStart,
    this.status = 'NOT_YET_ELIGIBLE',
    this.registeredAt,
    this.registeredBy = '',
    this.portalReferenceId = '',
  });

  factory AdminSocialSecurityRegistration.fromJson(Map<String, dynamic> json) {
    return AdminSocialSecurityRegistration(
      registrationId: parseInt(json['registration_id']) ?? 0,
      employeeId: parseInt(json['employee_id']) ?? 0,
      employeeName: parseString(json['employee_name']) ?? 'Worker',
      daysWorkedCurrentFy: parseInt(json['days_worked_current_fy']) ?? 0,
      financialYearStart: parseDateTime(json['financial_year_start']),
      status: parseString(json['status'])?.toUpperCase() ?? 'NOT_YET_ELIGIBLE',
      registeredAt: parseDateTime(json['registered_at']),
      registeredBy: parseString(json['registered_by']) ?? '',
      portalReferenceId: parseString(json['portal_reference_id']) ?? '',
    );
  }

  final int registrationId;
  final int employeeId;
  final String employeeName;
  final int daysWorkedCurrentFy;
  final DateTime? financialYearStart;
  final String status;
  final DateTime? registeredAt;
  final String registeredBy;
  final String portalReferenceId;

  bool get isRegistered => status == 'REGISTERED';
  bool get isEligiblePending => status == 'ELIGIBLE_PENDING';
  bool get isNotYetEligible => status == 'NOT_YET_ELIGIBLE';

  /// Standard statutory threshold is 90 days worked in the financial year.
  double get progressToThreshold => (daysWorkedCurrentFy / 90.0).clamp(0.0, 1.0);

  String get statusDisplay {
    switch (status) {
      case 'REGISTERED':
        return 'Registered';
      case 'ELIGIBLE_PENDING':
        return 'Eligible — Pending';
      case 'NOT_YET_ELIGIBLE':
      default:
        return 'Not Yet Eligible';
    }
  }
}
