import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../core/theme/app_typography.dart';
import 'app_fade_in.dart';

/// The default single promotional banner image asset.
const String kDefaultServiceSpotlightImage = 'Technician Homepage.jpg';

/// A modern, responsive single-image Service Spotlight section.
///
/// Features:
/// - Displays a single high-fidelity service banner without carousel clutter.
/// - Preserves natural 2:1 aspect ratio without face zooming or distortion.
/// - Fluid responsiveness across all mobile screen widths.
/// - Clean card styling consistent with the Workforce design language.
class WorkforceShowcaseSection extends StatelessWidget {
  const WorkforceShowcaseSection({
    super.key,
    this.heading = 'Service Spotlight',
    this.imageAsset = kDefaultServiceSpotlightImage,
    this.headingPadding = const EdgeInsets.symmetric(horizontal: AppSpacing.md),
    this.cardsPadding = const EdgeInsets.symmetric(horizontal: AppSpacing.md),
    this.aspectRatio = 2.0,
    this.onTap,
  });

  final String heading;
  final String imageAsset;
  final EdgeInsets headingPadding;
  final EdgeInsets cardsPadding;
  final double aspectRatio;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    Widget card = Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.cardStandard),
        border: Border.all(
          color: AppColors.border.withValues(alpha: 0.7),
          width: 1,
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x14000000),
            blurRadius: 8,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.cardStandard - 1),
        child: AspectRatio(
          aspectRatio: aspectRatio,
          child: Image.asset(
            imageAsset,
            fit: BoxFit.cover,
            alignment: Alignment.center,
            errorBuilder: (context, error, stackTrace) {
              return Container(
                color: AppColors.darkSurface,
                alignment: Alignment.center,
                child: const Icon(
                  Icons.handyman_rounded,
                  size: 48,
                  color: Color(0xFF38BDF8),
                ),
              );
            },
          ),
        ),
      ),
    );

    if (onTap != null) {
      card = GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: card,
      );
    }

    return AppFadeIn(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (heading.isNotEmpty) ...[
            Padding(
              padding: headingPadding,
              child: Row(
                children: [
                  Container(
                    width: 3,
                    height: 12,
                    margin: const EdgeInsets.only(right: AppSpacing.xs),
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  Text(
                    heading.toUpperCase(),
                    style: AppTypography.label.copyWith(
                      letterSpacing: 0.8,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.xs + 2),
          ],
          Padding(
            padding: cardsPadding,
            child: card,
          ),
        ],
      ),
    );
  }
}
