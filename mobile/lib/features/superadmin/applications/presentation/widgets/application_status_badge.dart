import 'package:flutter/material.dart';

/// Semantic status badge for platform application statuses.
class ApplicationStatusBadge extends StatelessWidget {
  const ApplicationStatusBadge({
    super.key,
    required this.status,
    this.dense = false,
  });

  final String status;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final normalized = status.toLowerCase().trim();

    Color bgColor;
    Color textColor;
    Color borderColor;
    String displayLabel;
    IconData icon;

    switch (normalized) {
      case 'submitted':
      case 'pending':
        bgColor = const Color(0xFFFEF3C7);
        textColor = const Color(0xFF92400E);
        borderColor = const Color(0xFFFDE68A);
        displayLabel = 'Pending Review';
        icon = Icons.schedule_rounded;
        break;
      case 'under_review':
        bgColor = const Color(0xFFEFF6FF);
        textColor = const Color(0xFF1D4ED8);
        borderColor = const Color(0xFFBFDBFE);
        displayLabel = 'Under Review';
        icon = Icons.search_rounded;
        break;
      case 'approved':
      case 'active':
        bgColor = const Color(0xFFECFDF5);
        textColor = const Color(0xFF065F46);
        borderColor = const Color(0xFFA7F3D0);
        displayLabel = 'Approved';
        icon = Icons.check_circle_rounded;
        break;
      case 'correction_required':
        bgColor = const Color(0xFFFFF7ED);
        textColor = const Color(0xFFC2410C);
        borderColor = const Color(0xFFFED7AA);
        displayLabel = 'Corrections Required';
        icon = Icons.edit_note_rounded;
        break;
      case 'rejected':
        bgColor = const Color(0xFFFEF2F2);
        textColor = const Color(0xFF991B1B);
        borderColor = const Color(0xFFFECACA);
        displayLabel = 'Rejected';
        icon = Icons.cancel_rounded;
        break;
      case 'in_progress':
        bgColor = const Color(0xFFF0FDF4);
        textColor = const Color(0xFF166534);
        borderColor = const Color(0xFFBBF7D0);
        displayLabel = 'In Progress';
        icon = Icons.pending_rounded;
        break;
      default:
        bgColor = const Color(0xFFF1F5F9);
        textColor = const Color(0xFF475569);
        borderColor = const Color(0xFFE2E8F0);
        displayLabel = normalized.replaceAll('_', ' ').toUpperCase();
        icon = Icons.info_outline_rounded;
    }

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dense ? 6 : 8,
        vertical: dense ? 2 : 3.5,
      ),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(dense ? 4 : 6),
        border: Border.all(color: borderColor, width: 0.8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: dense ? 11 : 13, color: textColor),
          SizedBox(width: dense ? 3 : 4.5),
          Text(
            displayLabel,
            style: TextStyle(
              fontSize: dense ? 10 : 11,
              fontWeight: FontWeight.w800,
              color: textColor,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }
}
