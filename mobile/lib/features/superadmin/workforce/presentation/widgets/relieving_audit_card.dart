import 'package:flutter/material.dart';

import '../../../../../core/theme/app_theme.dart';
import '../../domain/platform_relieving_request.dart';

/// Card widget displaying a single resignation / relieving audit record in the queue.
class RelievingAuditCard extends StatelessWidget {
  const RelievingAuditCard({
    super.key,
    required this.request,
    required this.onAudit,
  });

  final PlatformRelievingRequest request;
  final VoidCallback onAudit;

  @override
  Widget build(BuildContext context) {
    final initial = request.technicianName.isNotEmpty
        ? request.technicianName[0].toUpperCase()
        : 'T';
    final isVendorApproved = request.isPendingSevoAudit;
    final isCompleted = request.isCompleted;

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(
          color: isVendorApproved
              ? const Color(0xFFDDD6FE)
              : const Color(0xFFE2E8F0),
          width: isVendorApproved ? 1.4 : 1.0,
        ),
        boxShadow: [
          if (isVendorApproved)
            BoxShadow(
              color: const Color(0xFF7C3AED).withValues(alpha: 0.08),
              blurRadius: 6,
              offset: const Offset(0, 2),
            )
          else
            const BoxShadow(
              color: Color(0x040A2540),
              blurRadius: 4,
              offset: Offset(0, 1.5),
            ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header Row: Technician + Status ─────────────────────────────
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  radius: 19,
                  backgroundColor: const Color(0xFFF3E8FF),
                  child: Text(
                    initial,
                    style: const TextStyle(
                      color: Color(0xFF7C3AED),
                      fontWeight: FontWeight.w800,
                      fontSize: 14,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        request.technicianName,
                        style: const TextStyle(
                          fontSize: 13.5,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF0F172A),
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Req #${request.id} • ${request.vendorName}',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF64748B),
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 6),
                _AuditStatusBadge(status: request.status),
              ],
            ),
          ),

          // ── Resignation Details & Category ──────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.sm),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Flexible(
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFE0E7FF),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            request.reasonDisplay ?? request.reasonCategory,
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF3730A3),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ),
                      if (request.desiredRelievingDate != null) ...[
                        const SizedBox(width: 6),
                        Text(
                          'Effective: ${request.desiredRelievingDate}',
                          style: const TextStyle(
                            fontSize: 10,
                            color: Color(0xFF64748B),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ],
                  ),
                  if (request.resignationNotes != null &&
                      request.resignationNotes!.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      '"${request.resignationNotes}"',
                      style: const TextStyle(
                        fontSize: 11,
                        fontStyle: FontStyle.italic,
                        color: Color(0xFF334155),
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),
          ),

          // ── Vendor Dues Settlement Status ────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.md,
              AppSpacing.sm,
              AppSpacing.md,
              0,
            ),
            child: Row(
              children: [
                Icon(
                  request.vendorSettlementNotes != null
                      ? Icons.check_circle_rounded
                      : Icons.hourglass_top_rounded,
                  size: 13,
                  color: request.vendorSettlementNotes != null
                      ? const Color(0xFF059669)
                      : const Color(0xFFD97706),
                ),
                const SizedBox(width: 5),
                Expanded(
                  child: Text(
                    request.vendorSettlementNotes != null
                        ? 'Vendor Clearance: ${request.vendorSettlementNotes}'
                        : 'Awaiting Vendor Dues Clearance & Signoff',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: request.vendorSettlementNotes != null
                          ? const Color(0xFF065F46)
                          : const Color(0xFF92400E),
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: AppSpacing.sm),
          const Divider(height: 1, color: Color(0xFFF1F5F9)),

          // ── Action Footer ────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.xs + 2,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Contact info
                Flexible(
                  child: Text(
                    request.technicianPhone.isNotEmpty
                        ? request.technicianPhone
                        : request.technicianEmail,
                    style: const TextStyle(
                      fontSize: 11,
                      color: Color(0xFF64748B),
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                // Action Button
                if (isVendorApproved)
                  FilledButton.icon(
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF7C3AED),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      minimumSize: Size.zero,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(6),
                      ),
                    ),
                    icon: const Icon(Icons.verified_user_rounded, size: 13),
                    label: const Text(
                      'Audit & Clear',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    onPressed: onAudit,
                  )
                else if (isCompleted)
                  const Text(
                    'Relieved (Solo Active)',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF059669),
                    ),
                  )
                else
                  const Text(
                    'Vendor Pending',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF94A3B8),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AuditStatusBadge extends StatelessWidget {
  const _AuditStatusBadge({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color text;
    Color border;
    String label;
    IconData icon;

    switch (status.toUpperCase()) {
      case 'VENDOR_APPROVED':
        bg = const Color(0xFFF5F3FF);
        text = const Color(0xFF6D28D9);
        border = const Color(0xFFDDD6FE);
        label = 'AUDIT REQUIRED';
        icon = Icons.gavel_rounded;
        break;
      case 'COMPLETED':
        bg = const Color(0xFFECFDF5);
        text = const Color(0xFF047857);
        border = const Color(0xFFA7F3D0);
        label = 'RELIEVED';
        icon = Icons.check_circle_rounded;
        break;
      case 'SEVO_APPROVED':
        bg = const Color(0xFFEFF6FF);
        text = const Color(0xFF1D4ED8);
        border = const Color(0xFFBFDBFE);
        label = 'APPROVED';
        icon = Icons.shield_rounded;
        break;
      default:
        bg = const Color(0xFFFFFBEB);
        text = const Color(0xFFB45309);
        border = const Color(0xFFFDE68A);
        label = 'REQUESTED';
        icon = Icons.hourglass_empty_rounded;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2.5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: border, width: 0.8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10, color: text),
          const SizedBox(width: 3),
          Text(
            label,
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.w900,
              color: text,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }
}
