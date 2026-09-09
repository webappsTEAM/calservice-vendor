/// Domain model representing a vendor-sent invitation to a technician.
class VendorSentInvitation {
  const VendorSentInvitation({
    required this.id,
    required this.inviteCode,
    required this.invitedEmail,
    this.technicianName,
    this.technicianEmail,
    this.technicianPhone,
    required this.status,
    required this.channel,
    this.createdAt,
    this.expiresAt,
    this.message,
  });

  final int id;
  final String inviteCode;
  final String invitedEmail;
  final String? technicianName;
  final String? technicianEmail;
  final String? technicianPhone;
  final String status;
  final String channel;
  final String? createdAt;
  final String? expiresAt;
  final String? message;

  bool get isPending => status.toUpperCase() == 'PENDING';
  bool get isAccepted => status.toUpperCase() == 'ACCEPTED';
  bool get isRejected => status.toUpperCase() == 'REJECTED';
  bool get isExpired => status.toUpperCase() == 'EXPIRED';
  bool get isCancelled => status.toUpperCase() == 'CANCELLED';

  factory VendorSentInvitation.fromJson(Map<String, dynamic> json) {
    return VendorSentInvitation(
      id: json['id'] as int? ?? 0,
      inviteCode: json['invite_code'] as String? ?? '',
      invitedEmail: json['invited_email'] as String? ?? '',
      technicianName: json['technician_name'] as String?,
      technicianEmail: json['technician_email'] as String?,
      technicianPhone: json['technician_phone'] as String?,
      status: json['status'] as String? ?? 'PENDING',
      channel: json['channel'] as String? ?? 'DIRECT_EMAIL',
      createdAt: json['created_at'] as String?,
      expiresAt: json['expires_at'] as String?,
      message: json['message'] as String?,
    );
  }
}

class VendorInvitationsResponse {
  const VendorInvitationsResponse({
    required this.invitations,
    required this.counts,
  });

  final List<VendorSentInvitation> invitations;
  final Map<String, int> counts;

  factory VendorInvitationsResponse.fromJson(Map<String, dynamic> json) {
    final list = (json['invitations'] as List<dynamic>?)
            ?.whereType<Map<String, dynamic>>()
            .map(VendorSentInvitation.fromJson)
            .toList() ??
        const [];

    final rawCounts = json['counts'] as Map<String, dynamic>? ?? {};
    final countsMap = <String, int>{};
    for (final entry in rawCounts.entries) {
      if (entry.value is int) {
        countsMap[entry.key] = entry.value as int;
      }
    }

    return VendorInvitationsResponse(
      invitations: list,
      counts: countsMap,
    );
  }
}
