import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_theme.dart';

/// Reusable metric card with responsive layout and clear hierarchy.
class MonitoringMetricCard extends StatelessWidget {
  const MonitoringMetricCard({
    super.key,
    required this.title,
    required this.value,
    this.explanation,
    this.badgeText,
    this.badgeColor,
    this.icon,
    this.iconColor,
  });

  final String title;
  final String value;
  final String? explanation;
  final String? badgeText;
  final Color? badgeColor;
  final IconData? icon;
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    final effectiveBadgeColor = badgeColor ?? const Color(0xFF059669);
    final effectiveIconColor = iconColor ?? const Color(0xFF004E89);

    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x040A2540),
            blurRadius: 4,
            offset: Offset(0, 1.5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top Row: Icon + Title + Optional Badge
          Row(
            children: [
              if (icon != null) ...[
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: effectiveIconColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Icon(icon, size: 16, color: effectiveIconColor),
                ),
                const SizedBox(width: 8),
              ],
              Expanded(
                child: Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
              if (badgeText != null) ...[
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: effectiveBadgeColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: effectiveBadgeColor.withValues(alpha: 0.35),
                      width: 0.7,
                    ),
                  ),
                  child: Text(
                    badgeText!,
                    style: TextStyle(
                      fontSize: 9.5,
                      fontWeight: FontWeight.w800,
                      color: effectiveBadgeColor,
                    ),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 8),

          // Value
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              value,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w900,
                color: Color(0xFF0A2540),
                letterSpacing: -0.4,
              ),
            ),
          ),

          // Explanation
          if (explanation != null) ...[
            const SizedBox(height: 6),
            Text(
              explanation!,
              style: TextStyle(
                fontSize: 11.5,
                color: AppColors.textMuted,
                height: 1.35,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
