import 'package:flutter/material.dart';

import '../../core/theme/app_motion.dart';
import '../../core/theme/app_theme.dart';

/// The standard Classic Enterprise surface.
///
/// The audit found 204 hand-rolled `Container(decoration: BoxDecoration(...))`
/// surfaces against 142 themed `Card(` widgets — meaning most surfaces in the
/// app bypass `CardThemeData` entirely and re-declare their own colour,
/// radius and border. This gives those surfaces one migration target.
///
/// Classic by construction: flat (no shadow), 1px border, 12px radius, and
/// colours resolved from [AppColors] so dark mode and high contrast work
/// without the call site thinking about it.
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.lg),
    this.onTap,
    this.tone,
    this.margin,
    this.backgroundColor,
    this.borderColor,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  /// When non-null the card becomes tappable and gains a restrained
  /// press/hover response.
  final VoidCallback? onTap;

  /// Optional status treatment — tints the fill and border to match a
  /// semantic family (e.g. [AppColors.warning] for a pending offer).
  final SemanticColor? tone;

  final EdgeInsetsGeometry? margin;
  final Color? backgroundColor;
  final Color? borderColor;

  @override
  Widget build(BuildContext context) {
    final background = backgroundColor ?? tone?.tint ?? AppColors.surface;
    final resolvedBorderColor = borderColor ?? tone?.tintBorder ?? AppColors.border;

    final surface = AnimatedContainer(
      duration: AppMotion.resolve(AppMotion.fast),
      curve: AppMotion.curve,
      padding: padding,
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppRadius.cardStandard),
        border: Border.all(color: resolvedBorderColor),
        boxShadow: AppElevation.none,
      ),
      child: child,
    );

    if (onTap == null) {
      return margin == null ? surface : Padding(padding: margin!, child: surface);
    }

    final tappable = Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(AppRadius.cardStandard),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.cardStandard),
        child: surface,
      ),
    );

    return margin == null ? tappable : Padding(padding: margin!, child: tappable);
  }
}
