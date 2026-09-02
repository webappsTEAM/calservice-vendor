import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../core/theme/app_typography.dart';

/// The uppercase group label that introduces a section, with an optional
/// trailing action ("See all", "Refresh", a count).
///
/// This pattern is repeated by hand across Home, Jobs, More, Performance and
/// the admin dashboard, each re-declaring its own font size, weight and
/// letter spacing. Centralising it is what makes section rhythm consistent
/// between the Employee and Admin sides.
class AppSectionHeader extends StatelessWidget {
  const AppSectionHeader({
    super.key,
    required this.title,
    this.icon,
    this.trailing,
    this.padding = const EdgeInsets.only(bottom: AppSpacing.sm),
  });

  final String title;
  final IconData? icon;

  /// Usually a `TextButton` or a count chip.
  final Widget? trailing;

  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding,
      child: Row(
        children: [
          if (icon != null) ...[
            Icon(icon, size: 15, color: AppColors.textMuted),
            const SizedBox(width: 6),
          ],
          Expanded(
            child: Text(
              title.toUpperCase(),
              style: AppTypography.label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          ?trailing,
        ],
      ),
    );
  }
}
