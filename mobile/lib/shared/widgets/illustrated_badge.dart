import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

/// The concentric "glow ring + elevated icon card" illustration used by
/// every empty-state and full-screen status message in the app
/// ([EmptyState], [StatusScreen]) — factored out so the one visual gets
/// maintained in one place instead of drifting between two copies.
class IllustratedBadge extends StatelessWidget {
  const IllustratedBadge({
    super.key,
    required this.icon,
    this.color,
    this.size = IllustratedBadgeSize.large,
    this.showAccentDot = false,
  });

  final IconData icon;
  final Color? color;
  final IllustratedBadgeSize size;

  /// A small success-colored dot on the badge's corner — reads as "resolved
  /// / up to date" for empty-but-healthy states. Left off by default so
  /// status screens (pending review, rejected, ...) don't imply a positive
  /// outcome that isn't there.
  final bool showAccentDot;

  @override
  Widget build(BuildContext context) {
    final effectiveColor = color ?? AppColors.primary;
    final outerSize = size.outer;
    final innerSize = size.inner;
    final iconSize = size.icon;

    return Stack(
      alignment: Alignment.center,
      children: [
        Container(
          width: outerSize,
          height: outerSize,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: effectiveColor.withValues(alpha: 0.05),
            border: Border.all(color: effectiveColor.withValues(alpha: 0.12), width: 1),
          ),
        ),
        Container(
          width: innerSize,
          height: innerSize,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(size.radius),
            border: Border.all(color: effectiveColor.withValues(alpha: 0.24), width: 1.2),
            boxShadow: [
              BoxShadow(
                color: effectiveColor.withValues(alpha: 0.1),
                blurRadius: 12,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          child: Stack(
            alignment: Alignment.center,
            children: [
              Icon(icon, size: iconSize, color: effectiveColor),
              if (showAccentDot)
                Positioned(
                  right: size.dotInset,
                  bottom: size.dotInset,
                  child: Container(
                    width: size.dot,
                    height: size.dot,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppColors.success.base,
                      border: Border.all(color: Colors.white, width: 1),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

enum IllustratedBadgeSize {
  compact(outer: 56, inner: 42, icon: 22, radius: 12, dot: 5, dotInset: 6),
  large(outer: 76, inner: 58, icon: 30, radius: 16, dot: 7, dotInset: 8),
  hero(outer: 88, inner: 68, icon: 32, radius: 18, dot: 8, dotInset: 9);

  const IllustratedBadgeSize({
    required this.outer,
    required this.inner,
    required this.icon,
    required this.radius,
    required this.dot,
    required this.dotInset,
  });

  final double outer;
  final double inner;
  final double icon;
  final double radius;
  final double dot;
  final double dotInset;
}
