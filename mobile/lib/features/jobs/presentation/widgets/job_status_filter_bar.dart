import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';

enum JobStatusFilter {
  all,
  newOffers,
  inProgress,
  completed,
  cancelled,
}

class JobStatusFilterBar extends StatelessWidget {
  const JobStatusFilterBar({
    super.key,
    required this.selectedFilter,
    required this.onFilterSelected,
    required this.allCount,
    required this.newOffersCount,
    required this.inProgressCount,
    required this.completedCount,
    this.cancelledCount = 0,
  });

  final JobStatusFilter selectedFilter;
  final ValueChanged<JobStatusFilter> onFilterSelected;
  final int allCount;
  final int newOffersCount;
  final int inProgressCount;
  final int completedCount;
  final int cancelledCount;

  @override
  Widget build(BuildContext context) {
    final filters = <_StatusFilterItem>[
      _StatusFilterItem(
        filter: JobStatusFilter.all,
        label: 'All Jobs ($allCount)',
        icon: null,
      ),
      _StatusFilterItem(
        filter: JobStatusFilter.newOffers,
        label: 'New Offers ($newOffersCount)',
        icon: Icons.bolt_rounded,
        isAlert: newOffersCount > 0,
      ),
      _StatusFilterItem(
        filter: JobStatusFilter.inProgress,
        label: 'In Progress ($inProgressCount)',
        icon: Icons.play_arrow_rounded,
      ),
      _StatusFilterItem(
        filter: JobStatusFilter.completed,
        label: 'Completed ($completedCount)',
        icon: Icons.check_rounded,
      ),
      if (cancelledCount > 0)
        _StatusFilterItem(
          filter: JobStatusFilter.cancelled,
          label: 'Cancelled ($cancelledCount)',
          icon: Icons.close_rounded,
        ),
    ];

    return SizedBox(
      height: 38,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        itemCount: filters.length,
        separatorBuilder: (context, index) => const SizedBox(width: AppSpacing.sm),
        itemBuilder: (context, index) {
          final item = filters[index];
          final isSelected = selectedFilter == item.filter;

          final Color bgColor;
          final Color textColor;
          final Color borderColor;
          final Color? iconColor;

          if (isSelected) {
            bgColor = AppColors.peacockNavy;
            textColor = Colors.white;
            borderColor = AppColors.peacockBlue;
            iconColor = item.isAlert ? const Color(0xFF34D399) : Colors.white;
          } else {
            bgColor = AppColors.surface;
            textColor = item.isAlert ? const Color(0xFF065F46) : AppColors.textPrimary;
            borderColor = item.isAlert ? const Color(0xFFA7F3D0) : AppColors.border;
            iconColor = item.isAlert ? const Color(0xFF059669) : AppColors.textMuted;
          }

          return Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () => onFilterSelected(item.filter),
              borderRadius: BorderRadius.circular(AppRadius.chip),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: bgColor,
                  borderRadius: BorderRadius.circular(AppRadius.chip),
                  border: Border.all(color: borderColor, width: isSelected ? 1.2 : 0.9),
                  boxShadow: isSelected
                      ? const [
                          BoxShadow(
                            color: Color(0x180A2540),
                            blurRadius: 4,
                            offset: Offset(0, 1.5),
                          ),
                        ]
                      : null,
                ),
                alignment: Alignment.center,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (item.icon != null) ...[
                      Icon(item.icon, size: 14, color: iconColor),
                      const SizedBox(width: 4),
                    ],
                    Text(
                      item.label,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                        color: textColor,
                        letterSpacing: 0.1,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _StatusFilterItem {
  const _StatusFilterItem({
    required this.filter,
    required this.label,
    this.icon,
    this.isAlert = false,
  });

  final JobStatusFilter filter;
  final String label;
  final IconData? icon;
  final bool isAlert;
}
