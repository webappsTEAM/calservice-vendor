import 'dart:async';
import 'package:flutter/material.dart';

import '../../core/theme/app_motion.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/app_typography.dart';
import 'app_fade_in.dart';

/// Model representing a single promotional banner in the service carousel.
class PromotionalBanner {
  const PromotionalBanner({
    required this.imageAsset,
    required this.badge,
    required this.title,
    required this.subtitle,
    required this.accentColor,
    this.badgeIcon = Icons.verified_rounded,
  });

  final String imageAsset;
  final String badge;
  final String title;
  final String subtitle;
  final Color accentColor;
  final IconData badgeIcon;
}

/// Backwards compatibility alias for older references.
typedef WorkforceShowcaseCard = PromotionalBanner;

/// The canonical 3 promotional service banners utilizing local high-resolution assets.
List<PromotionalBanner> defaultPromotionalBanners() => const [
  PromotionalBanner(
    imageAsset: 'assets/images/banners/ac_electrical_plumbing_banner.jpg',
    badge: 'EXPERT HOME SERVICES',
    badgeIcon: Icons.handyman_rounded,
    title: 'AC, Electrical & Plumbing',
    subtitle: 'Fast diagnostics, certified repairs & precision installations',
    accentColor: Color(0xFF38BDF8), // Cyan / Sky
  ),
  PromotionalBanner(
    imageAsset: 'assets/images/banners/appliance_repair_service_banner.jpg',
    badge: 'FAST & RELIABLE',
    badgeIcon: Icons.bolt_rounded,
    title: 'Appliance & Electrical Care',
    subtitle: 'Fans, LEDs, water heaters, pumps & switchboard solutions',
    accentColor: Color(0xFF34D399), // Emerald
  ),
  PromotionalBanner(
    imageAsset: 'assets/images/banners/sevo_technician_services_banner.png',
    badge: 'SEVO VERIFIED WORKFORCE',
    badgeIcon: Icons.verified_user_rounded,
    title: 'Skilled On-Demand Technicians',
    subtitle: 'Equipped professionals delivering safe & reliable solutions',
    accentColor: Color(0xFF818CF8), // Indigo / Peacock
  ),
];

/// Legacy fallback helper for backwards compatibility.
List<PromotionalBanner> defaultWorkforceShowcase() => defaultPromotionalBanners();

/// A modern, responsive promotional banner carousel.
///
/// Features:
/// - Auto-scrolling every 5 seconds (safely disabled under reduced-motion).
/// - Interactive manual horizontal swipe.
/// - Active animated indicator dots with tap-to-navigate.
/// - High-contrast gradient typography overlays over local service photography.
/// - Safe lifecycle handling with automatic timer & controller disposal.
class WorkforceShowcaseSection extends StatefulWidget {
  const WorkforceShowcaseSection({
    super.key,
    this.heading = 'Service Spotlight',
    this.banners,
    this.headingPadding = const EdgeInsets.symmetric(horizontal: AppSpacing.md),
    this.cardsPadding = const EdgeInsets.symmetric(horizontal: AppSpacing.md),
    this.height = 172.0,
    this.autoScrollInterval = const Duration(seconds: 5),
  });

  final String heading;
  final List<PromotionalBanner>? banners;
  final EdgeInsets headingPadding;
  final EdgeInsets cardsPadding;
  final double height;
  final Duration autoScrollInterval;

  @override
  State<WorkforceShowcaseSection> createState() => _WorkforceShowcaseSectionState();
}

class _WorkforceShowcaseSectionState extends State<WorkforceShowcaseSection> {
  late final PageController _pageController;
  Timer? _autoScrollTimer;
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    _initAutoScroll();
  }

  void _initAutoScroll() {
    _autoScrollTimer?.cancel();
    if (AppMotion.isReduced) return;

    _autoScrollTimer = Timer.periodic(widget.autoScrollInterval, (timer) {
      if (!mounted || !_pageController.hasClients) return;
      final banners = widget.banners ?? defaultPromotionalBanners();
      if (banners.length <= 1) return;

      final nextPage = (_currentPage + 1) % banners.length;
      _pageController.animateToPage(
        nextPage,
        duration: AppMotion.resolve(const Duration(milliseconds: 450)),
        curve: Curves.easeInOutCubic,
      );
    });
  }

  void _onPageChanged(int index) {
    if (mounted) {
      setState(() {
        _currentPage = index;
      });
    }
  }

  void _onDotTapped(int index) {
    _pageController.animateToPage(
      index,
      duration: AppMotion.resolve(const Duration(milliseconds: 350)),
      curve: Curves.easeInOutCubic,
    );
  }

  @override
  void didUpdateWidget(covariant WorkforceShowcaseSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.autoScrollInterval != widget.autoScrollInterval) {
      _initAutoScroll();
    }
  }

  @override
  void dispose() {
    _autoScrollTimer?.cancel();
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final banners = widget.banners ?? defaultPromotionalBanners();
    if (banners.isEmpty) return const SizedBox.shrink();

    // Check system-level accessibility motion preferences
    final disableAnimations = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (disableAnimations && _autoScrollTimer != null) {
      _autoScrollTimer?.cancel();
      _autoScrollTimer = null;
    }

    return AppFadeIn(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (widget.heading.isNotEmpty) ...[
            Padding(
              padding: widget.headingPadding,
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
                    widget.heading.toUpperCase(),
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
            padding: widget.cardsPadding,
            child: Column(
              children: [
                SizedBox(
                  height: widget.height,
                  child: PageView.builder(
                    controller: _pageController,
                    itemCount: banners.length,
                    onPageChanged: _onPageChanged,
                    itemBuilder: (context, index) {
                      return _PromotionalBannerCard(banner: banners[index]);
                    },
                  ),
                ),
                if (banners.length > 1) ...[
                  const SizedBox(height: AppSpacing.xs + 4),
                  _PageIndicators(
                    count: banners.length,
                    activeIndex: _currentPage,
                    onDotTapped: _onDotTapped,
                    activeColor: banners[_currentPage % banners.length].accentColor,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PromotionalBannerCard extends StatelessWidget {
  const _PromotionalBannerCard({required this.banner});

  final PromotionalBanner banner;

  @override
  Widget build(BuildContext context) {
    return Container(
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
        child: Image.asset(
          banner.imageAsset,
          fit: BoxFit.cover,
          alignment: Alignment.center,
          errorBuilder: (context, error, stackTrace) {
            return Container(
              color: AppColors.darkSurface,
              alignment: Alignment.center,
              child: Icon(
                banner.badgeIcon,
                size: 48,
                color: banner.accentColor.withValues(alpha: 0.5),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _PageIndicators extends StatelessWidget {
  const _PageIndicators({
    required this.count,
    required this.activeIndex,
    required this.onDotTapped,
    required this.activeColor,
  });

  final int count;
  final int activeIndex;
  final ValueChanged<int> onDotTapped;
  final Color activeColor;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(count, (index) {
        final isActive = index == (activeIndex % count);
        return GestureDetector(
          onTap: () => onDotTapped(index),
          behavior: HitTestBehavior.opaque,
          child: AnimatedContainer(
            duration: AppMotion.resolve(const Duration(milliseconds: 280)),
            curve: Curves.easeOutCubic,
            margin: const EdgeInsets.symmetric(horizontal: 3),
            width: isActive ? 20.0 : 6.0,
            height: 6.0,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(3),
              color: isActive
                  ? activeColor
                  : AppColors.textMuted.withValues(alpha: 0.35),
            ),
          ),
        );
      }),
    );
  }
}
