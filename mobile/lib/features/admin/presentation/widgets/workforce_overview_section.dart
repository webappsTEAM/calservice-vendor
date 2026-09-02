import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/admin_dashboard_metrics.dart';
import 'metric_card.dart';

/// WORKFORCE OVERVIEW Section:
/// Displays the 5 key personnel and operational metrics.
class WorkforceOverviewSection extends StatelessWidget {
  const WorkforceOverviewSection({
    super.key,
    required this.data,
  });

  final AdminDashboardData data;

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

            final card1 = MetricCard(
              label: 'Total Registered',
              value: data.totalRegisteredCount,
              subtext: 'Technicians on roster',
              icon: Icons.people_alt_rounded,
              iconColor: const Color(0xFF004E89),
              valueColor: const Color(0xFF0F172A),
            );

            final card2 = MetricCard(
              label: 'Approved & Active',
              value: data.approvedAndActiveCount,
              subtext: 'Authorized for jobs',
              icon: Icons.check_circle_rounded,
              iconColor: const Color(0xFF059669),
              valueColor: const Color(0xFF047857),
            );

            final card3 = MetricCard(
              label: 'Online & Available',
              value: data.onlineAndAvailableCount,
              subtext: 'Ready for dispatch',
              icon: Icons.sensors_rounded,
              iconColor: const Color(0xFF0284C7),
              valueColor: const Color(0xFF0369A1),
            );

            final card4 = MetricCard(
              label: 'On Active Jobs',
              value: data.onActiveJobsCount,
              subtext: 'Currently in field',
              icon: Icons.construction_rounded,
              iconColor: const Color(0xFFD97706),
              valueColor: const Color(0xFFB45309),
            );

            final card5 = MetricCard(
              label: 'Pending Review',
              value: data.pendingReviewCount,
              subtext: 'Awaiting dossier check',
              icon: Icons.schedule_rounded,
              iconColor: const Color(0xFFEA580C),
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

            // Standard Mobile 2-column layout with 5th card spanning across
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
