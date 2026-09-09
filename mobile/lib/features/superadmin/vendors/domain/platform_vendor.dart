import 'package:flutter/foundation.dart';

/// Domain model representing a registered vendor company in the SEVO platform.
@immutable
class PlatformVendor {
  const PlatformVendor({
    required this.id,
    required this.companyName,
    required this.slug,
    required this.city,
    required this.address,
    required this.ownerName,
    required this.ownerEmail,
    required this.ownerPhone,
    required this.tiedWorkersCount,
    required this.pendingInvitationsCount,
    this.createdAt,
  });

  final int id;
  final String companyName;
  final String slug;
  final String city;
  final String address;
  final String ownerName;
  final String ownerEmail;
  final String ownerPhone;
  final int tiedWorkersCount;
  final int pendingInvitationsCount;
  final DateTime? createdAt;

  String get displayName =>
      companyName.isNotEmpty ? companyName : 'Vendor Company';

  String get initial => displayName.isNotEmpty ? displayName[0].toUpperCase() : 'V';

  String get effectiveLocation {
    if (city.isNotEmpty) return city;
    if (address.isNotEmpty) return address;
    return 'Not specified';
  }

  factory PlatformVendor.fromJson(Map<String, dynamic> json) {
    DateTime? parseDate(dynamic value) {
      if (value == null) return null;
      if (value is DateTime) return value;
      return DateTime.tryParse(value.toString());
    }

    return PlatformVendor(
      id: json['id'] as int? ?? 0,
      companyName: json['company_name'] as String? ??
          json['name'] as String? ??
          '',
      slug: json['slug'] as String? ?? '',
      city: json['city'] as String? ?? '',
      address: json['address'] as String? ?? '',
      ownerName: json['owner_name'] as String? ?? '',
      ownerEmail: json['owner_email'] as String? ?? '',
      ownerPhone: json['owner_phone'] as String? ?? '',
      tiedWorkersCount: json['tied_workers_count'] as int? ?? 0,
      pendingInvitationsCount: json['pending_invitations_count'] as int? ?? 0,
      createdAt: parseDate(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'company_name': companyName,
        'slug': slug,
        'city': city,
        'address': address,
        'owner_name': ownerName,
        'owner_email': ownerEmail,
        'owner_phone': ownerPhone,
        'tied_workers_count': tiedWorkersCount,
        'pending_invitations_count': pendingInvitationsCount,
        'created_at': createdAt?.toIso8601String(),
      };
}

/// Response wrapper for `GET /workforce/platform/vendors/`.
@immutable
class PlatformVendorsResponse {
  const PlatformVendorsResponse({
    required this.vendors,
    required this.totalCount,
  });

  final List<PlatformVendor> vendors;
  final int totalCount;

  factory PlatformVendorsResponse.fromJson(Map<String, dynamic> json) {
    final rawVendors = json['vendors'];
    final list = <PlatformVendor>[];
    if (rawVendors is List) {
      for (final item in rawVendors) {
        if (item is Map<String, dynamic>) {
          list.add(PlatformVendor.fromJson(item));
        }
      }
    }

    return PlatformVendorsResponse(
      vendors: list,
      totalCount: json['total_count'] as int? ?? list.length,
    );
  }
}
