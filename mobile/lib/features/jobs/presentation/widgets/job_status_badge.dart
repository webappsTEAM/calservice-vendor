import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';

/// Professional status badge for Workforce Jobs.
///
/// Follows the classic design system:
/// - AVAILABLE / NEW OFFER: Emerald Green or Peacock Blue accent
/// - IN PROGRESS / ON THE WAY / ARRIVED / ACCEPTED: Peacock Blue accent
/// - COMPLETED: Emerald Green
/// - CANCELLED / REJECTED: Muted Slate Gray / Muted Rose
/// - PENDING / PAYMENT PENDING: Amber / Gold
class JobStatusBadge extends StatelessWidget {
  const JobStatusBadge({
    super.key,
    required this.status,
    this.label,
    this.dense = true,
  });

  final String status;
  final String? label;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final cleanStatus = status.trim().toLowerCase().replaceAll('-', '_').replaceAll(' ', '_');

    final Color bgColor;
    final Color borderColor;
    final Color textColor;
    final String displayLabel;

    switch (cleanStatus) {
      case 'available':
      case 'offered':
      case 'new_offer':
      case 'open':
        bgColor = const Color(0xFFECFDF5);
        borderColor = const Color(0xFFA7F3D0);
        textColor = const Color(0xFF065F46);
        displayLabel = label ?? 'AVAILABLE';
        break;

      case 'in_progress':
      case 'active':
        bgColor = const Color(0xFFEFF6FF);
        borderColor = const Color(0xFFBFDBFE);
        textColor = const Color(0xFF1E40AF);
        displayLabel = label ?? 'IN PROGRESS';
        break;

      case 'on_the_way':
      case 'en_route':
        bgColor = const Color(0xFFF0F9FF);
        borderColor = const Color(0xFFBAE6FD);
        textColor = const Color(0xFF0369A1);
        displayLabel = label ?? 'ON THE WAY';
        break;

      case 'arrived':
        bgColor = const Color(0xFFF0FDFA);
        borderColor = const Color(0xFF99F6E4);
        textColor = const Color(0xFF0F766E);
        displayLabel = label ?? 'ARRIVED';
        break;

      case 'accepted':
      case 'assigned':
        bgColor = const Color(0xFFF1F5F9);
        borderColor = const Color(0xFFCBD5E1);
        textColor = const Color(0xFF1E293B);
        displayLabel = label ?? 'ACCEPTED';
        break;

      case 'proof_submitted':
      case 'service_completed':
        bgColor = const Color(0xFFEFF6FF);
        borderColor = const Color(0xFFBFDBFE);
        textColor = const Color(0xFF1E40AF);
        displayLabel = label ?? 'PROOF SUBMITTED';
        break;

      case 'completed':
        bgColor = const Color(0xFFECFDF5);
        borderColor = const Color(0xFFA7F3D0);
        textColor = const Color(0xFF065F46);
        displayLabel = label ?? 'COMPLETED';
        break;

      case 'cancelled':
      case 'rejected':
      case 'declined':
        bgColor = const Color(0xFFF8FAFC);
        borderColor = const Color(0xFFE2E8F0);
        textColor = const Color(0xFF64748B);
        displayLabel = label ?? 'CANCELLED';
        break;

      case 'pending':
      case 'payment_pending':
      case 'unassigned':
      default:
        bgColor = const Color(0xFFFFFBEB);
        borderColor = const Color(0xFFFDE68A);
        textColor = const Color(0xFF92400E);
        displayLabel = label ??
            (cleanStatus.isEmpty ? 'PENDING' : cleanStatus.replaceAll('_', ' ').toUpperCase());
        break;
    }

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dense ? 7 : 9,
        vertical: dense ? 2.5 : 4,
      ),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(AppRadius.chip),
        border: Border.all(color: borderColor, width: 0.8),
      ),
      child: Text(
        displayLabel,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          fontSize: dense ? 10.5 : 11.5,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.4,
          color: textColor,
          height: 1.2,
        ),
      ),
    );
  }
}
