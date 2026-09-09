import 'package:flutter/material.dart';

import '../../../../../core/theme/app_theme.dart';
import '../../data/superadmin_workforce_repository.dart';
import '../superadmin_workforce_providers.dart';

/// Live summary metrics section on the Super Admin Workforce Roster screen.
class WorkforceSummaryMetrics extends StatelessWidget {
  const WorkforceSummaryMetrics({
    super.key,
    required this.data,
    required this.selectedFilter,
    required this.onSelectFilter,
  });

  final PlatformWorkforceOverviewData data;
  final WorkforceFilterType selectedFilter;
  final ValueChanged<WorkforceFilterType> onSelectFilter;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isNarrow = constraints.maxWidth < 340;

        final cardTotal = _MetricBox(
          label: 'TOTAL TECHNICIANS',
          value: '${data.totalTechnicians}',
          subtext: 'Registered on platform',
          color: const Color(0xFF0F172A),
          icon: Icons.people_alt_rounded,
          iconColor: const Color(0xFF004E89),
          isSelected: selectedFilter == WorkforceFilterType.all,
          onTap: () => onSelectFilter(WorkforceFilterType.all),
        );

        final cardSolo = _MetricBox(
          label: 'SOLO WORKERS',
          value: '${data.soloWorkersCount}',
          subtext: 'Independent technicians',
          color: const Color(0xFF2563EB),
          icon: Icons.person_rounded,
          iconColor: const Color(0xFF2563EB),
          isSelected: selectedFilter == WorkforceFilterType.solo,
          onTap: () => onSelectFilter(WorkforceFilterType.solo),
        );

        final cardTied = _MetricBox(
          label: 'TIED WORKERS',
          value: '${data.tiedWorkersCount}',
          subtext: 'Vendor-linked personnel',
          color: const Color(0xFF059669),
          icon: Icons.business_rounded,
          iconColor: const Color(0xFF059669),
          isSelected: selectedFilter == WorkforceFilterType.tied,
          onTap: () => onSelectFilter(WorkforceFilterType.tied),
        );

        final cardAudits = _MetricBox(
          label: 'RELIEVING AUDITS',
          value: '${data.pendingSevoAuditCount}',
          subtext: data.pendingSevoAuditCount > 0
              ? 'Action required'
              : 'All audits cleared',
          color: const Color(0xFF7C3AED),
          icon: Icons.gavel_rounded,
          iconColor: const Color(0xFF7C3AED),
          hasAlert: data.pendingSevoAuditCount > 0,
          isSelected: selectedFilter == WorkforceFilterType.relievingAudits,
          onTap: () => onSelectFilter(WorkforceFilterType.relievingAudits),
        );

        if (isNarrow) {
          return Column(
            children: [
              cardTotal,
              const SizedBox(height: 8),
              cardSolo,
              const SizedBox(height: 8),
              cardTied,
              const SizedBox(height: 8),
              cardAudits,
            ],
          );
        }

        return Column(
          children: [
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(child: cardTotal),
                  const SizedBox(width: 8),
                  Expanded(child: cardSolo),
                ],
              ),
            ),
            const SizedBox(height: 8),
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(child: cardTied),
                  const SizedBox(width: 8),
                  Expanded(child: cardAudits),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

class _MetricBox extends StatelessWidget {
  const _MetricBox({
    required this.label,
    required this.value,
    required this.subtext,
    required this.color,
    required this.icon,
    required this.iconColor,
    this.hasAlert = false,
    this.isSelected = false,
    required this.onTap,
  });

  final String label;
  final String value;
  final String subtext;
  final Color color;
  final IconData icon;
  final Color iconColor;
  final bool hasAlert;
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
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.sm + 2,
            vertical: AppSpacing.sm + 4,
          ),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(
              color: isSelected ? color : const Color(0xFFE2E8F0),
              width: isSelected ? 1.5 : 1.0,
            ),
            boxShadow: [
              if (isSelected)
                BoxShadow(
                  color: color.withValues(alpha: 0.12),
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
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      label,
                      style: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF64748B),
                        letterSpacing: 0.5,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 4),
                  if (hasAlert)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 5,
                        vertical: 1.5,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFEE2E2),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        'AUDIT',
                        style: TextStyle(
                          color: Color(0xFFDC2626),
                          fontSize: 8.5,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    )
                  else
                    Icon(icon, size: 14, color: iconColor),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                value,
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  color: color,
                  letterSpacing: -0.4,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtext,
                style: const TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                  color: Color(0xFF94A3B8),
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
