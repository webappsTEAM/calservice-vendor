import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../routing/app_routes.dart';
import '../../domain/superadmin_dashboard.dart';

/// Single compact action card for items requiring operational attention.
class ActionCenterCard extends StatelessWidget {
  const ActionCenterCard({
    super.key,
    required this.title,
    required this.description,
    required this.count,
    required this.icon,
    required this.badgeBgColor,
    required this.badgeTextColor,
    required this.iconBgColor,
    required this.iconColor,
    required this.onTap,
  });

  final String title;
  final String description;
  final int count;
  final IconData icon;
  final Color badgeBgColor;
  final Color badgeTextColor;
  final Color iconBgColor;
  final Color iconColor;
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
          decoration: BoxDecoration(
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
              // Top Row: Semantic Icon + Count Pill
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      color: iconBgColor,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Center(
                      child: Icon(icon, size: 17, color: iconColor),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: badgeBgColor,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '$count',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w900,
                        color: badgeTextColor,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              // Card Title + Chevron Indicator
              Row(
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Icon(
                    Icons.chevron_right_rounded,
                    size: 16,
                    color: Color(0xFF94A3B8),
                  ),
                ],
              ),
              const SizedBox(height: 2),
              // Subtitle Description
              Text(
                description,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w400,
                  color: Color(0xFF64748B),
                  height: 1.25,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Action Center section rendering the 4 operational queues.
class SuperAdminActionCenterSection extends StatelessWidget {
  const SuperAdminActionCenterSection({
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
            Container(
              width: 4,
              height: 14,
              decoration: BoxDecoration(
                color: const Color(0xFFF59E0B),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              'ACTION CENTER',
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
          'Items requiring immediate operational attention',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w400,
            color: AppColors.textMuted,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        // Adaptive Grid for 4 Action Cards
        LayoutBuilder(
          builder: (context, constraints) {
            final isSmall = constraints.maxWidth < 340;
            final isWide = constraints.maxWidth >= 600;

            final card1 = ActionCenterCard(
              title: 'Pending Applications',
              description: 'Technician registrations requiring document review',
              count: data.pendingApplicationsCount,
              icon: Icons.assignment_ind_outlined,
              badgeBgColor: const Color(0xFFFEF3C7),
              badgeTextColor: const Color(0xFF92400E),
              iconBgColor: const Color(0xFFFFFBEB),
              iconColor: const Color(0xFFD97706),
              onTap: () => context.push(AppRoutes.superAdminApplications),
            );

            final card2 = ActionCenterCard(
              title: 'Active Technicians',
              description: 'Approved workforce field technicians',
              count: data.activeTechniciansCount,
              icon: Icons.engineering_outlined,
              badgeBgColor: const Color(0xFFECFDF5),
              badgeTextColor: const Color(0xFF065F46),
              iconBgColor: const Color(0xFFF0FDF4),
              iconColor: const Color(0xFF059669),
              onTap: () => context.push(AppRoutes.superAdminWorkforce),
            );

            final card3 = ActionCenterCard(
              title: 'Jobs Awaiting Assignment',
              description: 'Customer bookings requiring technician dispatch',
              count: data.jobsAwaitingAssignmentCount,
              icon: Icons.send_outlined,
              badgeBgColor: const Color(0xFFFFEDD5),
              badgeTextColor: const Color(0xFF9A3412),
              iconBgColor: const Color(0xFFFFF7ED),
              iconColor: const Color(0xFFEA580C),
              onTap: () => context.push(AppRoutes.adminDispatch),
            );

            final card4 = ActionCenterCard(
              title: 'Corrections Pending Resubmission',
              description: 'Technicians notified to re-upload flagged files',
              count: data.correctionsPendingCount,
              icon: Icons.edit_note_rounded,
              badgeBgColor: const Color(0xFFF1F5F9),
              badgeTextColor: const Color(0xFF334155),
              iconBgColor: const Color(0xFFF8FAFC),
              iconColor: const Color(0xFF64748B),
              onTap: () => context.push(
                '${AppRoutes.superAdminApplications}?status=correction_required',
              ),
            );

            if (isSmall) {
              return Column(
                children: [
                  card1,
                  const SizedBox(height: 10),
                  card2,
                  const SizedBox(height: 10),
                  card3,
                  const SizedBox(height: 10),
                  card4,
                ],
              );
            }

            if (isWide) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: card1),
                  const SizedBox(width: 10),
                  Expanded(child: card2),
                  const SizedBox(width: 10),
                  Expanded(child: card3),
                  const SizedBox(width: 10),
                  Expanded(child: card4),
                ],
              );
            }

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
              ],
            );
          },
        ),
      ],
    );
  }
}
