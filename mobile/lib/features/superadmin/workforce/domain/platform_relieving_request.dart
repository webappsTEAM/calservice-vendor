import 'package:flutter/foundation.dart';

/// Domain model representing a resignation / relieving request awaiting SEVO audit.
@immutable
class PlatformRelievingRequest {
  const PlatformRelievingRequest({
    required this.id,
    this.relationshipId,
    required this.technicianId,
    required this.technicianName,
    required this.technicianEmail,
    required this.technicianPhone,
    required this.vendorId,
    required this.vendorName,
    required this.status,
    required this.reasonCategory,
    this.reasonDisplay,
    this.resignationNotes,
    this.desiredRelievingDate,
    this.vendorSettlementNotes,
    this.vendorApprovedAt,
    this.sevoApprovedAt,
    this.sevoAuditNotes,
    this.workerSignoffAck = false,
    this.vendorSignoffAck = false,
    this.createdAt,
  });

  final int id;
  final int? relationshipId;
  final int technicianId;
  final String technicianName;
  final String technicianEmail;
  final String technicianPhone;
  final int vendorId;
  final String vendorName;
  final String status; // 'REQUESTED' | 'VENDOR_APPROVED' | 'SEVO_APPROVED' | 'REJECTED' | 'COMPLETED'
  final String reasonCategory;
  final String? reasonDisplay;
  final String? resignationNotes;
  final String? desiredRelievingDate;
  final String? vendorSettlementNotes;
  final String? vendorApprovedAt;
  final String? sevoApprovedAt;
  final String? sevoAuditNotes;
  final bool workerSignoffAck;
  final bool vendorSignoffAck;
  final String? createdAt;

  bool get isPendingSevoAudit => status.toUpperCase() == 'VENDOR_APPROVED';
  bool get isCompleted => status.toUpperCase() == 'COMPLETED';
  bool get isSevoApproved => status.toUpperCase() == 'SEVO_APPROVED';
  bool get isRequested => status.toUpperCase() == 'REQUESTED';

  factory PlatformRelievingRequest.fromJson(Map<String, dynamic> json) {
    return PlatformRelievingRequest(
      id: json['id'] as int? ?? 0,
      relationshipId: json['relationship_id'] as int?,
      technicianId: json['technician_id'] as int? ?? 0,
      technicianName: json['technician_name'] as String? ?? 'Technician',
      technicianEmail: json['technician_email'] as String? ?? '',
      technicianPhone: json['technician_phone'] as String? ?? '',
      vendorId: json['vendor_id'] as int? ?? 0,
      vendorName: json['vendor_name'] as String? ?? 'Vendor',
      status: (json['status'] as String? ?? 'REQUESTED').toUpperCase(),
      reasonCategory: json['reason_category'] as String? ?? 'TRANSITION_TO_SOLO',
      reasonDisplay: json['reason_display'] as String?,
      resignationNotes: json['resignation_notes'] as String?,
      desiredRelievingDate: json['desired_relieving_date'] as String?,
      vendorSettlementNotes: json['vendor_settlement_notes'] as String?,
      vendorApprovedAt: json['vendor_approved_at'] as String?,
      sevoApprovedAt: json['sevo_approved_at'] as String?,
      sevoAuditNotes: json['sevo_audit_notes'] as String?,
      workerSignoffAck: json['worker_signoff_ack'] as bool? ?? false,
      vendorSignoffAck: json['vendor_signoff_ack'] as bool? ?? false,
      createdAt: json['created_at'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'relationship_id': relationshipId,
        'technician_id': technicianId,
        'technician_name': technicianName,
        'technician_email': technicianEmail,
        'technician_phone': technicianPhone,
        'vendor_id': vendorId,
        'vendor_name': vendorName,
        'status': status,
        'reason_category': reasonCategory,
        'reason_display': reasonDisplay,
        'resignation_notes': resignationNotes,
        'desired_relieving_date': desiredRelievingDate,
        'vendor_settlement_notes': vendorSettlementNotes,
        'vendor_approved_at': vendorApprovedAt,
        'sevo_approved_at': sevoApprovedAt,
        'sevo_audit_notes': sevoAuditNotes,
        'worker_signoff_ack': workerSignoffAck,
        'vendor_signoff_ack': vendorSignoffAck,
        'created_at': createdAt,
      };
}

/// Relieving requests payload response wrapper from `GET /workforce/platform/relieving-requests/`.
@immutable
class PlatformRelievingResponse {
  const PlatformRelievingResponse({
    required this.relievingRequests,
    required this.totalCount,
    required this.pendingSevoCount,
  });

  final List<PlatformRelievingRequest> relievingRequests;
  final int totalCount;
  final int pendingSevoCount;

  factory PlatformRelievingResponse.fromJson(Map<String, dynamic> json) {
    final rawList = json['relieving_requests'];
    final requests = <PlatformRelievingRequest>[];
    if (rawList is List) {
      for (final item in rawList) {
        if (item is Map<String, dynamic>) {
          requests.add(PlatformRelievingRequest.fromJson(item));
        }
      }
    }

    return PlatformRelievingResponse(
      relievingRequests: requests,
      totalCount: json['total_count'] as int? ?? requests.length,
      pendingSevoCount: json['pending_sevo_count'] as int? ??
          requests.where((r) => r.isPendingSevoAudit).length,
    );
  }
}
