import 'package:flutter/material.dart';

import '../../../core/utils/json_parsing.dart';

class ActiveVendorInfo {
  const ActiveVendorInfo({
    required this.vendorId,
    required this.vendorName,
    this.relationshipId,
    this.startedAt,
  });

  factory ActiveVendorInfo.fromJson(Map<String, dynamic> json) {
    return ActiveVendorInfo(
      vendorId: parseInt(json['vendor_id']) ?? 0,
      vendorName: parseString(json['vendor_name']) ?? 'Vendor Partner',
      relationshipId: parseInt(json['relationship_id']),
      startedAt: parseDateTime(json['started_at']),
    );
  }

  final int vendorId;
  final String vendorName;
  final int? relationshipId;
  final DateTime? startedAt;
}

class MatchedCriterion {
  const MatchedCriterion({
    required this.attribute,
    required this.value,
    required this.operator,
  });

  factory MatchedCriterion.fromJson(Map<String, dynamic> json) {
    return MatchedCriterion(
      attribute: parseString(json['attribute']) ?? '',
      value: parseString(json['value']) ?? '',
      operator: parseString(json['operator']) ?? '=',
    );
  }

  final String attribute;
  final String value;
  final String operator;
}

class TechnicianInvitation {
  const TechnicianInvitation({
    required this.id,
    required this.vendorId,
    required this.vendorName,
    required this.vendorAddress,
    required this.status,
    required this.channel,
    required this.message,
    required this.matchedCriteria,
    this.expiresAt,
    this.respondedAt,
    this.createdAt,
  });

  factory TechnicianInvitation.fromJson(Map<String, dynamic> json) {
    final criteriaList = json['matched_criteria'] is List
        ? (json['matched_criteria'] as List)
            .map((c) => MatchedCriterion.fromJson(c as Map<String, dynamic>))
            .toList()
        : <MatchedCriterion>[];

    return TechnicianInvitation(
      id: parseInt(json['id']) ?? 0,
      vendorId: parseInt(json['vendor_id']) ?? 0,
      vendorName: parseString(json['vendor_name']) ?? 'Vendor Partner',
      vendorAddress: parseString(json['vendor_address']) ?? '',
      status: parseString(json['status'])?.toUpperCase() ?? 'PENDING',
      channel: parseString(json['channel']) ?? 'PORTAL',
      message: parseString(json['message']) ?? '',
      matchedCriteria: criteriaList,
      expiresAt: parseDateTime(json['expires_at']),
      respondedAt: parseDateTime(json['responded_at']),
      createdAt: parseDateTime(json['created_at']),
    );
  }

  final int id;
  final int vendorId;
  final String vendorName;
  final String vendorAddress;
  final String status;
  final String channel;
  final String message;
  final List<MatchedCriterion> matchedCriteria;
  final DateTime? expiresAt;
  final DateTime? respondedAt;
  final DateTime? createdAt;

  bool get isPending => status == 'PENDING';
  bool get isAccepted => status == 'ACCEPTED';
  bool get isRejected => status == 'REJECTED' || status == 'DECLINED';
  bool get isCancelled => status == 'CANCELLED';
  bool get isExpired => status == 'EXPIRED';

  String get statusDisplay {
    switch (status) {
      case 'PENDING':
        return 'PENDING';
      case 'ACCEPTED':
        return 'ACCEPTED';
      case 'REJECTED':
      case 'DECLINED':
        return 'DECLINED';
      case 'CANCELLED':
        return 'CANCELLED';
      case 'EXPIRED':
        return 'EXPIRED';
      default:
        return status;
    }
  }

  Color get statusColor {
    switch (status) {
      case 'PENDING':
        return const Color(0xFFD97706); // Amber
      case 'ACCEPTED':
        return const Color(0xFF059669); // Emerald Green
      case 'REJECTED':
      case 'DECLINED':
        return const Color(0xFF64748B); // Slate / Muted
      case 'CANCELLED':
        return const Color(0xFFDC2626); // Rose
      case 'EXPIRED':
        return const Color(0xFF94A3B8); // Slate
      default:
        return const Color(0xFF004E89); // Peacock Blue
    }
  }
}

class InvitationsResponse {
  const InvitationsResponse({
    required this.invitations,
    this.activeVendor,
    this.pendingCount = 0,
  });

  factory InvitationsResponse.fromJson(Map<String, dynamic> json) {
    final invList = json['invitations'] is List
        ? (json['invitations'] as List)
            .map((i) => TechnicianInvitation.fromJson(i as Map<String, dynamic>))
            .toList()
        : <TechnicianInvitation>[];

    final activeVendor = json['active_vendor'] is Map<String, dynamic>
        ? ActiveVendorInfo.fromJson(json['active_vendor'] as Map<String, dynamic>)
        : null;

    return InvitationsResponse(
      invitations: invList,
      activeVendor: activeVendor,
      pendingCount: parseInt(json['pending_count']) ??
          invList.where((i) => i.isPending).length,
    );
  }

  final List<TechnicianInvitation> invitations;
  final ActiveVendorInfo? activeVendor;
  final int pendingCount;
}
