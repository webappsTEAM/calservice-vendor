import 'package:flutter/material.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/superadmin/applications/domain/platform_application.dart';

/// Responsive metrics summary cards for the Super Admin Applications Approval screen.
class ApplicationMetrics extends StatelessWidget {
  const ApplicationMetrics({
    super.key,
    required this.metrics,
    required this.selectedFilter,
    required this.onSelectFilter,
  });

  final SuperAdminApplicationMetrics metrics;
  final PlatformApplicationStatusFilter selectedFilter;
  final ValueChanged<PlatformApplicationStatusFilter> onSelectFilter;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final cardPending = _MetricCard(
          title: 'Pending Applications',
          subtitle: 'Waiting for review',
          count: metrics.pendingCount,
          icon: Icons.schedule_rounded,
          badgeColor: const Color(0xFFFEF3C7),
          textColor: const Color(0xFF92400E),
          iconColor: const Color(0xFFD97706),
          iconBgColor: const Color(0xFFFFFBEB),
          isSelected: selectedFilter == PlatformApplicationStatusFilter.pending,
          onTap: () => onSelectFilter(PlatformApplicationStatusFilter.pending),
        );

        final cardReview = _MetricCard(
          title: 'Under Review',
          subtitle: 'Currently being reviewed',
          count: metrics.underReviewCount,
          icon: Icons.search_rounded,
          badgeColor: const Color(0xFFDBEAFE),
          textColor: const Color(0xFF1E40AF),
          iconColor: const Color(0xFF2563EB),
          iconBgColor: const Color(0xFFEFF6FF),
          isSelected: selectedFilter == PlatformApplicationStatusFilter.underReview,
          onTap: () => onSelectFilter(PlatformApplicationStatusFilter.underReview),
        );

        final cardApproved = _MetricCard(
          title: 'Approved',
          subtitle: 'Successfully onboarded',
          count: metrics.approvedCount,
          icon: Icons.check_circle_outline_rounded,
          badgeColor: const Color(0xFFD1FAE5),
          textColor: const Color(0xFF065F46),
          iconColor: const Color(0xFF059669),
          iconBgColor: const Color(0xFFECFDF5),
          isSelected: selectedFilter == PlatformApplicationStatusFilter.approved,
          onTap: () => onSelectFilter(PlatformApplicationStatusFilter.approved),
        );

        final cardCorrections = _MetricCard(
          title: 'Corrections Required',
          subtitle: 'Awaiting resubmission',
          count: metrics.correctionsRequiredCount,
          icon: Icons.edit_note_rounded,
          badgeColor: const Color(0xFFFFEDD5),
          textColor: const Color(0xFF9A3412),
          iconColor: const Color(0xFFEA580C),
          iconBgColor: const Color(0xFFFFF7ED),
          isSelected: selectedFilter == PlatformApplicationStatusFilter.correctionsRequired,
          onTap: () => onSelectFilter(PlatformApplicationStatusFilter.correctionsRequired),
        );

        final cardRejected = _MetricCard(
          title: 'Rejected',
          subtitle: 'Declined applications',
          count: metrics.rejectedCount,
          icon: Icons.cancel_outlined,
          badgeColor: const Color(0xFFFEE2E2),
          textColor: const Color(0xFF991B1B),
          iconColor: const Color(0xFFDC2626),
          iconBgColor: const Color(0xFFFEF2F2),
          isSelected: selectedFilter == PlatformApplicationStatusFilter.rejected,
          onTap: () => onSelectFilter(PlatformApplicationStatusFilter.rejected),
        );

        // Small screen (<360px): Single-column stack or 2-column with wrap
        if (constraints.maxWidth < 360) {
          return Column(
            children: [
              cardPending,
              const SizedBox(height: 8),
              cardReview,
              const SizedBox(height: 8),
              cardApproved,
              const SizedBox(height: 8),
              cardCorrections,
              const SizedBox(height: 8),
              cardRejected,
            ],
          );
        }

        // Standard Mobile (360px–599px): 2-column grid
        if (constraints.maxWidth < 600) {
          return Column(
            children: [
              IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(child: cardPending),
                    const SizedBox(width: 8),
                    Expanded(child: cardReview),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(child: cardApproved),
                    const SizedBox(width: 8),
                    Expanded(child: cardCorrections),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              cardRejected,
            ],
          );
        }

        // Wide Mobile / Tablet (>=600px): Scrollable horizontal or multi-column
        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              SizedBox(width: 170, child: cardPending),
              const SizedBox(width: 8),
              SizedBox(width: 170, child: cardReview),
              const SizedBox(width: 8),
              SizedBox(width: 170, child: cardApproved),
              const SizedBox(width: 8),
              SizedBox(width: 170, child: cardCorrections),
              const SizedBox(width: 8),
              SizedBox(width: 170, child: cardRejected),
            ],
          ),
        );
      },
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.title,
    required this.subtitle,
    required this.count,
    required this.icon,
    required this.badgeColor,
    required this.textColor,
    required this.iconColor,
    required this.iconBgColor,
    required this.isSelected,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final int count;
  final IconData icon;
  final Color badgeColor;
  final Color textColor;
  final Color iconColor;
  final Color iconBgColor;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(AppRadius.card),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFFF8FAFC) : Colors.white,
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(
              color: isSelected ? iconColor : const Color(0xFFE2E8F0),
              width: isSelected ? 1.8 : 1.0,
            ),
            boxShadow: [
              BoxShadow(
                color: isSelected
                    ? iconColor.withValues(alpha: 0.12)
                    : const Color(0x060A2540),
                blurRadius: 4,
                offset: const Offset(0, 1.5),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    width: 28,
                    height: 28,
                    decoration: BoxDecoration(
                      color: iconBgColor,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Center(
                      child: Icon(icon, size: 15, color: iconColor),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                    decoration: BoxDecoration(
                      color: badgeColor,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      '$count',
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w900,
                        color: textColor,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                title,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  color: isSelected ? const Color(0xFF0F172A) : const Color(0xFF334155),
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              Text(
                subtitle,
                style: const TextStyle(
                  fontSize: 10,
                  color: Color(0xFF64748B),
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
