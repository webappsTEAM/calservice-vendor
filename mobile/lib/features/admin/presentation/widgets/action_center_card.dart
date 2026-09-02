import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';

/// Individual operational card for the Action Center.
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
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Top Accent Indicator Bar
              Container(
                height: 3,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: iconColor,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(AppRadius.card - 1)),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Top Row: Icon Badge & Count Badge
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: iconBgColor,
                            borderRadius: BorderRadius.circular(7),
                          ),
                          child: Icon(icon, size: 16, color: iconColor),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2.5),
                          decoration: BoxDecoration(
                            color: badgeBgColor,
                            borderRadius: BorderRadius.circular(999),
                            border: Border.all(
                              color: badgeTextColor.withValues(alpha: 0.25),
                              width: 0.8,
                            ),
                          ),
                          child: Text(
                            '$count',
                            style: TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w900,
                              color: badgeTextColor,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    // Title
                    Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                        height: 1.25,
                      ),
                    ),
                    const SizedBox(height: 3),
                    // Description
                    Text(
                      description,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w400,
                        color: Color(0xFF64748B),
                        height: 1.25,
                      ),
                    ),
                    const SizedBox(height: 8),
                    // Bottom Action Indicator
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Text(
                          'View',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            color: iconColor,
                          ),
                        ),
                        const SizedBox(width: 3),
                        Icon(
                          Icons.arrow_forward_rounded,
                          size: 12,
                          color: iconColor,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
