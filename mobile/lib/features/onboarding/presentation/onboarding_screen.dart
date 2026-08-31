import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../routing/app_routes.dart';
import 'onboarding_controller.dart';

/// Full-fidelity onboarding walkthrough using the 3 provided artwork assets.
///
/// PER USER INSTRUCTIONS:
/// - Uses ONLY the 3 existing image files: onboarding1.jpg, onboarding2.jpg, onboarding3.jpg.
/// - Does NOT render any duplicate visible UI (no duplicate headings, descriptions,
///   page indicator dots, Skip/Back labels, or visible buttons over the artwork).
/// - The onboarding image itself is the primary visual composition exactly as provided.
/// - Preserves the exact 1024x1536 (2:3) aspect ratio without stretching, squashing,
///   distortion, or zooming.
/// - Interactive touch targets are transparent/invisible overlays positioned directly
///   over the corresponding visual areas (Skip, Back, Next, Get Started / View Job).
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  static const List<String> _imageAssets = [
    'onboarding1.jpg',
    'onboarding2.jpg',
    'onboarding3.jpg',
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _nextPage() {
    if (_currentPage < _imageAssets.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 320),
        curve: Curves.easeInOutCubic,
      );
    } else {
      _completeOnboarding();
    }
  }

  void _previousPage() {
    if (_currentPage > 0) {
      _pageController.previousPage(
        duration: const Duration(milliseconds: 320),
        curve: Curves.easeInOutCubic,
      );
    }
  }

  Future<void> _completeOnboarding() async {
    // Persist completion state so onboarding is not shown again on subsequent launches
    await ref.read(onboardingControllerProvider.notifier).completeOnboarding();

    if (!mounted) return;

    if (context.canPop()) {
      context.pop();
    } else {
      context.go(AppRoutes.login);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF01172E),
      body: SafeArea(
        top: false,
        bottom: false,
        child: PageView.builder(
          controller: _pageController,
          itemCount: _imageAssets.length,
          physics: const BouncingScrollPhysics(),
          onPageChanged: (index) => setState(() => _currentPage = index),
          itemBuilder: (context, index) {
            return Center(
              child: AspectRatio(
                aspectRatio: 1024 / 1536,
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final width = constraints.maxWidth;
                    final height = constraints.maxHeight;

                    return Stack(
                      fit: StackFit.expand,
                      children: [
                        // ── 1. The Original Onboarding Image Artwork ───────────
                        // Preserves exact 1024x1536 (2:3) aspect ratio without
                        // stretching, squashing, or face zooming.
                        Image.asset(
                          _imageAssets[index],
                          fit: BoxFit.contain,
                          alignment: Alignment.center,
                          errorBuilder: (context, error, stackTrace) => Container(
                            color: const Color(0xFF01172E),
                            alignment: Alignment.center,
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(
                                  Icons.broken_image_rounded,
                                  color: Colors.white54,
                                  size: 48,
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Missing asset: ${_imageAssets[index]}',
                                  style: const TextStyle(color: Colors.white70, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        ),

                        // ── 2. Transparent Interactive Touch Overlays ─────────
                        // Positioned precisely over the printed UI elements.
                        _buildTouchOverlay(index, width, height),
                      ],
                    );
                  },
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildTouchOverlay(int pageIndex, double width, double height) {
    return Stack(
      children: [
        // ── Top-Right: Transparent Skip Target ─────────────────────────────────
        // In onboarding2.jpg, SKIP is at top-right (x: ~90-96%, y: ~4-7%).
        // We provide the target across all pages for consistent UX.
        Positioned(
          top: 0,
          right: 0,
          width: width * 0.28,
          height: height * 0.10,
          child: Semantics(
            button: true,
            label: 'Skip',
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                key: const Key('onboarding_skip_button'),
                borderRadius: BorderRadius.circular(20),
                splashColor: Colors.white.withValues(alpha: 0.2),
                highlightColor: Colors.white.withValues(alpha: 0.1),
                onTap: _completeOnboarding,
              ),
            ),
          ),
        ),

        // ── Bottom-Left: Transparent Back Target ───────────────────────────────
        // In onboarding2.jpg, "<- BACK" is at bottom-left (x: ~4-39%, y: ~85-96%).
        // Visible on Page 2 and Page 3.
        if (pageIndex > 0)
          Positioned(
            left: width * 0.03,
            bottom: height * 0.03,
            width: width * 0.38,
            height: height * 0.08,
            child: Semantics(
              button: true,
              label: 'Back',
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  key: const Key('onboarding_back_button'),
                  borderRadius: BorderRadius.circular(999),
                  splashColor: Colors.white.withValues(alpha: 0.25),
                  highlightColor: Colors.white.withValues(alpha: 0.1),
                  onTap: _previousPage,
                ),
              ),
            ),
          ),

        // ── Bottom-Right: Transparent Next / Get Started Target ───────────────
        // In onboarding1.jpg and onboarding2.jpg, "NEXT ->" green pill is at:
        // x: ~65-96%, y: ~89-96%.
        // On page 3, this target acts as "Get Started" to complete onboarding.
        Positioned(
          right: width * 0.03,
          bottom: height * 0.03,
          width: width * 0.38,
          height: height * 0.08,
          child: Semantics(
            button: true,
            label: pageIndex == _imageAssets.length - 1 ? 'Get Started' : 'Next',
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                key: Key(
                  pageIndex == _imageAssets.length - 1
                      ? 'onboarding_get_started_button'
                      : 'onboarding_next_button',
                ),
                borderRadius: BorderRadius.circular(999),
                splashColor: Colors.white.withValues(alpha: 0.25),
                highlightColor: Colors.white.withValues(alpha: 0.1),
                onTap: _nextPage,
              ),
            ),
          ),
        ),

        // ── Page 3 Specific: Transparent "View Job" CTA Target ─────────────────
        // In onboarding3.jpg, the notification card has a green "View Job ->" pill
        // at x: ~8-33%, y: ~42-49%. Tapping it also completes onboarding!
        if (pageIndex == 2)
          Positioned(
            left: width * 0.06,
            top: height * 0.41,
            width: width * 0.32,
            height: height * 0.09,
            child: Semantics(
              button: true,
              label: 'View Job',
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  key: const Key('onboarding_view_job_button'),
                  borderRadius: BorderRadius.circular(999),
                  splashColor: Colors.white.withValues(alpha: 0.25),
                  highlightColor: Colors.white.withValues(alpha: 0.1),
                  onTap: _completeOnboarding,
                ),
              ),
            ),
          ),
      ],
    );
  }
}
