import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/superadmin_dashboard.dart';

/// Single metric card displaying an operational figure with semantic color accent.
class WorkforceMetricCard extends StatelessWidget {
  const WorkforceMetricCard({
    super.key,
    required this.label,
    required this.value,
    required this.subtext,
    required this.icon,
    required this.iconColor,
    required this.valueColor,
  });

  final String label;
  final int value;
  final String subtext;
  final IconData icon;
  final Color iconColor;
  final Color valueColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x040A2540),
            blurRadius: 4,
            offset: Offset(0, 1.5),
          ),
        ],
      ),
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Top Row: Metric Label + Small Semantic Icon
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF64748B),
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 4),
              Icon(icon, size: 16, color: iconColor),
            ],
          ),
          const SizedBox(height: 8),
          // Large Numerical Metric
          Text(
            '$value',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w900,
              color: valueColor,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 2),
          // Subtext Context
          Text(
            subtext,
            style: const TextStyle(
              fontSize: 10.5,
              fontWeight: FontWeight.w400,
              color: Color(0xFF94A3B8),
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

/// WORKFORCE OVERVIEW Section:
/// Renders 5 live metric cards:
/// 1. Total Registered
/// 2. Approved & Active (Emerald Green accent)
/// 3. Online & Available (Peacock Blue accent)
/// 4. On Active Jobs (Amber/Orange accent)
/// 5. Pending Review (Amber accent)
class SuperAdminWorkforceOverviewSection extends StatelessWidget {
  const SuperAdminWorkforceOverviewSection({
    super.key,
    required this.data,
  });

  final SuperAdminDashboardData data;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section Header
        Row(
          children: [
            const Icon(
              Icons.people_alt_rounded,
              size: 15,
              color: Color(0xFF004E89),
            ),
            const SizedBox(width: 6),
            Text(
              'WORKFORCE OVERVIEW',
              style: TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w800,
                color: AppColors.textSecondary,
                letterSpacing: 0.8,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          'Personnel roster, availability and field activity',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w400,
            color: AppColors.textMuted,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        // Adaptive Grid for 5 Metric Cards
        LayoutBuilder(
          builder: (context, constraints) {
            final isSmall = constraints.maxWidth < 340;
            final isWide = constraints.maxWidth >= 600;

            final card1 = WorkforceMetricCard(
              label: 'Total Registered',
              value: data.totalRegisteredCount,
              subtext: 'Technicians on roster',
              icon: Icons.people_alt_rounded,
              iconColor: const Color(0xFF004E89),
              valueColor: const Color(0xFF0F172A),
            );

            final card2 = WorkforceMetricCard(
              label: 'Approved & Active',
              value: data.approvedAndActiveCount,
              subtext: 'Authorized for jobs',
              icon: Icons.check_circle_rounded,
              iconColor: const Color(0xFF059669), // Emerald Green
              valueColor: const Color(0xFF047857),
            );

            final card3 = WorkforceMetricCard(
              label: 'Online & Available',
              value: data.onlineAndAvailableCount,
              subtext: 'Ready for dispatch',
              icon: Icons.sensors_rounded,
              iconColor: const Color(0xFF004E89), // Peacock Blue
              valueColor: const Color(0xFF004E89),
            );

            final card4 = WorkforceMetricCard(
              label: 'On Active Jobs',
              value: data.onActiveJobsCount,
              subtext: 'Currently in field',
              icon: Icons.construction_rounded,
              iconColor: const Color(0xFFD97706), // Amber
              valueColor: const Color(0xFFB45309),
            );

            final card5 = WorkforceMetricCard(
              label: 'Pending Review',
              value: data.pendingReviewCount,
              subtext: 'Awaiting dossier check',
              icon: Icons.schedule_rounded,
              iconColor: const Color(0xFFEA580C), // Orange/Amber
              valueColor: const Color(0xFFC2410C),
            );

            if (isSmall) {
              return Column(
                children: [
                  card1,
                  const SizedBox(height: 8),
                  card2,
                  const SizedBox(height: 8),
                  card3,
                  const SizedBox(height: 8),
                  card4,
                  const SizedBox(height: 8),
                  card5,
                ],
              );
            }

            if (isWide) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: card1),
                  const SizedBox(width: 8),
                  Expanded(child: card2),
                  const SizedBox(width: 8),
                  Expanded(child: card3),
                  const SizedBox(width: 8),
                  Expanded(child: card4),
                  const SizedBox(width: 8),
                  Expanded(child: card5),
                ],
              );
            }

            // Standard Mobile 2-column layout with 5th card full width
            return Column(
              children: [
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(child: card1),
                      const SizedBox(width: 10),
                      Expanded(child: card2),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(child: card3),
                      const SizedBox(width: 10),
                      Expanded(child: card4),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                card5,
              ],
            );
          },
        ),
      ],
    );
  }
}
