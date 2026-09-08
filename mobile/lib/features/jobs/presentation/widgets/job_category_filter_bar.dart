import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import 'category_helper.dart';

class JobCategoryFilterBar extends StatelessWidget {
  const JobCategoryFilterBar({
    super.key,
    required this.selectedCategory,
    required this.onCategorySelected,
    this.availableCategories = const [],
  });

  final String? selectedCategory;
  final ValueChanged<String?> onCategorySelected;
  final List<String> availableCategories;

  @override
  Widget build(BuildContext context) {
    // Combine standard categories and any extra categories present in jobs
    final allCategoryNames = <String>[];
    for (final standard in kStandardServiceCategories) {
      allCategoryNames.add(standard.name);
    }
    for (final extra in availableCategories) {
      if (extra.trim().isNotEmpty &&
          !allCategoryNames.any((c) => c.toLowerCase() == extra.toLowerCase())) {
        allCategoryNames.add(extra.trim());
      }
    }

    final isAllSelected = selectedCategory == null || selectedCategory!.isEmpty;

    return SizedBox(
      height: 32,
      child: ListView(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        children: [
          // "All Categories" chip
          _CategoryChip(
            label: 'All Categories',
            icon: Icons.apps_rounded,
            isSelected: isAllSelected,
            onTap: () => onCategorySelected(null),
          ),
          const SizedBox(width: AppSpacing.xs),
          for (final cat in allCategoryNames) ...[
            _CategoryChip(
              label: cat,
              icon: iconForCategory(cat),
              isSelected: selectedCategory?.toLowerCase() == cat.toLowerCase(),
              onTap: () => onCategorySelected(cat),
            ),
            const SizedBox(width: AppSpacing.xs),
          ],
        ],
      ),
    );
  }
}

class _CategoryChip extends StatelessWidget {
  const _CategoryChip({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.chip),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.peacockBlue.withValues(alpha: 0.12) : AppColors.surface,
            borderRadius: BorderRadius.circular(AppRadius.chip),
            border: Border.all(
              color: isSelected ? AppColors.peacockBlue : AppColors.border,
              width: isSelected ? 1.2 : 0.8,
            ),
          ),
          alignment: Alignment.center,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 13,
                color: isSelected ? AppColors.peacockBlue : AppColors.textMuted,
              ),
              const SizedBox(width: 5),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                  color: isSelected ? AppColors.peacockNavy : AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
