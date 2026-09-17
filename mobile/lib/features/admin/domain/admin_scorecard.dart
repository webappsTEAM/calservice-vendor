import '../../../core/utils/json_parsing.dart';

/// Represents a technician / worker's scorecard in the SEVO back office.
///
/// Backed by `/api/workforce/admin/scorecards/`.
class AdminScorecardItem {
  const AdminScorecardItem({
    required this.employeeId,
    required this.employeeName,
    this.tier = 'UNRATED',
    this.averageRating = 0.0,
    this.csatAverage = 0.0,
    this.slaScore = 0.0,
    this.ratingCount = 0,
    this.slaMetCount = 0,
    this.slaBreachCount = 0,
    this.lastRecalculatedAt,
  });

  factory AdminScorecardItem.fromJson(Map<String, dynamic> json) {
    return AdminScorecardItem(
      employeeId: parseInt(json['employee_id']) ?? 0,
      employeeName: parseString(json['employee_name']) ?? 'Worker',
      tier: parseString(json['tier'])?.toUpperCase() ?? 'UNRATED',
      averageRating: parseDouble(json['average_rating']) ?? 0.0,
      csatAverage: parseDouble(json['csat_average']) ?? 0.0,
      slaScore: parseDouble(json['sla_score']) ?? 0.0,
      ratingCount: parseInt(json['rating_count']) ?? 0,
      slaMetCount: parseInt(json['sla_met_count']) ?? 0,
      slaBreachCount: parseInt(json['sla_breach_count']) ?? 0,
      lastRecalculatedAt: parseDateTime(json['last_recalculated_at']),
    );
  }

  final int employeeId;
  final String employeeName;
  final String tier;
  final double averageRating;
  final double csatAverage;
  final double slaScore;
  final int ratingCount;
  final int slaMetCount;
  final int slaBreachCount;
  final DateTime? lastRecalculatedAt;
}
