/// Domain model representing a technician tied to the authenticated vendor business.
class TiedTechnician {
  const TiedTechnician({
    required this.relationshipId,
    required this.technicianId,
    required this.userId,
    required this.name,
    required this.email,
    required this.phone,
    required this.title,
    required this.state,
    required this.status,
    required this.scopeSkills,
    required this.engagementType,
    required this.paymentModel,
    this.startedAt,
    this.endedAt,
    required this.averageRating,
    required this.ratingCount,
    required this.tier,
    required this.isOnline,
    required this.currentAvailability,
  });

  final int relationshipId;
  final int technicianId;
  final int userId;
  final String name;
  final String email;
  final String phone;
  final String title;
  final String state;
  final String status;
  final List<String> scopeSkills;
  final String engagementType;
  final String paymentModel;
  final String? startedAt;
  final String? endedAt;
  final double averageRating;
  final int ratingCount;
  final String tier;
  final bool isOnline;
  final String currentAvailability;

  bool get isActive => status.toUpperCase() == 'ACTIVE';
  bool get isSuspended => status.toUpperCase() == 'SUSPENDED';
  bool get isTerminated => status.toUpperCase() == 'TERMINATED';
  bool get isResigned => status.toUpperCase() == 'RESIGNED';
  bool get isResignationRequested =>
      status.toUpperCase() == 'RESIGNATION_REQUESTED';

  factory TiedTechnician.fromJson(Map<String, dynamic> json) {
    final rawSkills = json['scope_skills'];
    final skillsList = <String>[];
    if (rawSkills is List) {
      for (final s in rawSkills) {
        if (s is String) {
          skillsList.add(s);
        } else if (s is Map && s['name'] != null) {
          skillsList.add(s['name'].toString());
        }
      }
    }

    return TiedTechnician(
      relationshipId: json['relationship_id'] as int? ?? json['id'] as int? ?? 0,
      technicianId: json['technician_id'] as int? ?? 0,
      userId: json['user_id'] as int? ?? 0,
      name: json['name'] as String? ?? 'Technician',
      email: json['email'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      title: json['title'] as String? ?? 'Technician',
      state: json['state'] as String? ?? '',
      status: json['status'] as String? ?? 'ACTIVE',
      scopeSkills: skillsList,
      engagementType: json['engagement_type'] as String? ?? 'DIRECT',
      paymentModel: json['payment_model'] as String? ?? 'REVENUE_SHARE',
      startedAt: json['started_at'] as String?,
      endedAt: json['ended_at'] as String?,
      averageRating: (json['average_rating'] as num?)?.toDouble() ?? 0.0,
      ratingCount: json['rating_count'] as int? ?? 0,
      tier: json['tier'] as String? ?? 'UNRATED',
      isOnline: json['is_online'] as bool? ?? false,
      currentAvailability: json['current_availability'] as String? ?? 'OFFLINE',
    );
  }
}

class VendorNetworkResponse {
  const VendorNetworkResponse({
    required this.technicians,
    required this.counts,
  });

  final List<TiedTechnician> technicians;
  final Map<String, int> counts;

  factory VendorNetworkResponse.fromJson(Map<String, dynamic> json) {
    final list = (json['technicians'] as List<dynamic>?)
            ?.whereType<Map<String, dynamic>>()
            .map(TiedTechnician.fromJson)
            .toList() ??
        const [];

    final rawCounts = json['counts'] as Map<String, dynamic>? ?? {};
    final countsMap = <String, int>{};
    for (final entry in rawCounts.entries) {
      if (entry.value is int) {
        countsMap[entry.key] = entry.value as int;
      }
    }

    return VendorNetworkResponse(
      technicians: list,
      counts: countsMap,
    );
  }
}
