import 'package:flutter/foundation.dart';

/// Information about a vendor company to which a technician is actively tied.
@immutable
class PlatformTiedVendorInfo {
  const PlatformTiedVendorInfo({
    required this.id,
    required this.companyName,
    this.startedAt,
    this.relationshipId,
  });

  final int id;
  final String companyName;
  final String? startedAt;
  final int? relationshipId;

  factory PlatformTiedVendorInfo.fromJson(Map<String, dynamic> json) {
    return PlatformTiedVendorInfo(
      id: json['id'] as int? ?? 0,
      companyName: json['company_name'] as String? ?? 'Vendor',
      startedAt: json['started_at'] as String?,
      relationshipId: json['relationship_id'] as int?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'company_name': companyName,
        'started_at': startedAt,
        'relationship_id': relationshipId,
      };
}

/// Aggregate workforce counts for live metric cards and filter tab badges.
@immutable
class PlatformWorkforceCounts {
  const PlatformWorkforceCounts({
    required this.all,
    required this.solo,
    required this.tied,
  });

  final int all;
  final int solo;
  final int tied;

  factory PlatformWorkforceCounts.fromJson(Map<String, dynamic> json) {
    return PlatformWorkforceCounts(
      all: json['all'] as int? ?? 0,
      solo: json['solo'] as int? ?? 0,
      tied: json['tied'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'all': all,
        'solo': solo,
        'tied': tied,
      };
}

/// Domain model representing a field technician / worker across the platform.
@immutable
class PlatformWorker {
  const PlatformWorker({
    required this.id,
    required this.employeeId,
    required this.name,
    required this.email,
    required this.phone,
    required this.city,
    required this.skills,
    required this.isOnline,
    required this.currentAvailability,
    required this.workforceType,
    this.tiedVendor,
    required this.registrationStatus,
    required this.hourlyRate,
  });

  final int id;
  final String employeeId;
  final String name;
  final String email;
  final String phone;
  final String city;
  final List<String> skills;
  final bool isOnline;
  final String currentAvailability;
  final String workforceType; // 'SOLO' | 'TIED'
  final PlatformTiedVendorInfo? tiedVendor;
  final String registrationStatus;
  final double hourlyRate;

  bool get isTied => workforceType.toUpperCase() == 'TIED' && tiedVendor != null;
  bool get isSolo => !isTied;

  factory PlatformWorker.fromJson(Map<String, dynamic> json) {
    final rawSkills = json['skills'];
    final skillsList = <String>[];
    if (rawSkills is List) {
      for (final item in rawSkills) {
        if (item != null) skillsList.add(item.toString());
      }
    }

    final rawVendor = json['tied_vendor'];
    PlatformTiedVendorInfo? vendor;
    if (rawVendor is Map<String, dynamic>) {
      vendor = PlatformTiedVendorInfo.fromJson(rawVendor);
    }

    return PlatformWorker(
      id: json['id'] as int? ?? 0,
      employeeId: json['employee_id'] as String? ?? '',
      name: json['name'] as String? ?? 'Technician',
      email: json['email'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      city: json['city'] as String? ?? '',
      skills: skillsList,
      isOnline: json['is_online'] as bool? ?? false,
      currentAvailability: json['current_availability'] as String? ?? 'AVAILABLE',
      workforceType: (json['workforce_type'] as String? ?? 'SOLO').toUpperCase(),
      tiedVendor: vendor,
      registrationStatus: json['registration_status'] as String? ?? 'approved',
      hourlyRate: (json['hourly_rate'] is num)
          ? (json['hourly_rate'] as num).toDouble()
          : 0.0,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'employee_id': employeeId,
        'name': name,
        'email': email,
        'phone': phone,
        'city': city,
        'skills': skills,
        'is_online': isOnline,
        'current_availability': currentAvailability,
        'workforce_type': workforceType,
        'tied_vendor': tiedVendor?.toJson(),
        'registration_status': registrationStatus,
        'hourly_rate': hourlyRate,
      };
}

/// Vendor summary for target vendor selection in assignment dropdowns.
@immutable
class PlatformVendorSummary {
  const PlatformVendorSummary({
    required this.id,
    required this.companyName,
    this.city,
    this.tiedWorkersCount = 0,
    this.ownerName,
    this.ownerPhone,
  });

  final int id;
  final String companyName;
  final String? city;
  final int tiedWorkersCount;
  final String? ownerName;
  final String? ownerPhone;

  factory PlatformVendorSummary.fromJson(Map<String, dynamic> json) {
    return PlatformVendorSummary(
      id: json['id'] as int? ?? 0,
      companyName: json['company_name'] as String? ??
          json['name'] as String? ??
          'Vendor Company',
      city: json['city'] as String?,
      tiedWorkersCount: json['tied_workers_count'] as int? ?? 0,
      ownerName: json['owner_name'] as String?,
      ownerPhone: json['owner_phone'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'company_name': companyName,
        'city': city,
        'tied_workers_count': tiedWorkersCount,
        'owner_name': ownerName,
        'owner_phone': ownerPhone,
      };
}

/// Workforce roster response wrapper from `GET /workforce/platform/workforce/`.
@immutable
class PlatformWorkforceResponse {
  const PlatformWorkforceResponse({
    required this.workers,
    required this.totalCount,
    required this.counts,
  });

  final List<PlatformWorker> workers;
  final int totalCount;
  final PlatformWorkforceCounts counts;

  factory PlatformWorkforceResponse.fromJson(Map<String, dynamic> json) {
    final rawWorkers = json['workers'];
    final workersList = <PlatformWorker>[];
    if (rawWorkers is List) {
      for (final item in rawWorkers) {
        if (item is Map<String, dynamic>) {
          workersList.add(PlatformWorker.fromJson(item));
        }
      }
    }

    final rawCounts = json['counts'];
    final counts = rawCounts is Map<String, dynamic>
        ? PlatformWorkforceCounts.fromJson(rawCounts)
        : PlatformWorkforceCounts(
            all: workersList.length,
            solo: workersList.where((w) => w.isSolo).length,
            tied: workersList.where((w) => w.isTied).length,
          );

    return PlatformWorkforceResponse(
      workers: workersList,
      totalCount: json['total_count'] as int? ?? workersList.length,
      counts: counts,
    );
  }
}
