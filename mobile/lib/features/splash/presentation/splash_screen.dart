import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_motion.dart';
import '../../../core/theme/app_theme.dart';
import 'splash_controller.dart';

/// Polished, cohesive animated splash screen for Sevo Workforce.
///
/// Lockup Composition:
///        [ SEVO LOGO ]
///              ↓ (16px gap)
///            SEVO
///              ↓ (6px gap)
///         WORKFORCE
///
/// Timeline (7500ms total duration):
/// - 0.0 – 0.7s (0 – 700ms): Peacock gradient backdrop & ambient emerald glow appear.
/// - 0.7 – 2.5s (700 – 2500ms): 1.8s progressive Left-to-Right wipe/reveal of Sevo logo with glowing beam.
/// - 2.5 – 3.2s (2500 – 3200ms): Logo gently scales from 0.90 -> 1.0 and settles.
/// - 3.0 – 4.0s (3000 – 4000ms): Subtle diagonal light sheen sweeps across the logo.
/// - 3.5 – 4.6s (3500 – 4600ms): "SEVO" brand title fades and slides into position.
/// - 4.5 – 5.4s (4500 – 5400ms): "WORKFORCE" subtitle fades and slides into position.
/// - 5.4 – 7.5s (5400 – 7500ms): 2.1s steady hold of the completed branding lockup.
/// - At 7.5s: Smooth transition to the existing destination.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _glowAnimation;
  late final Animation<double> _wipeAnimation;
  late final Animation<double> _scaleAnimation;
  late final Animation<double> _sheenAnimation;
  late final Animation<double> _titleFadeAnimation;
  late final Animation<Offset> _titleSlideAnimation;
  late final Animation<double> _badgeFadeAnimation;
  late final Animation<Offset> _badgeSlideAnimation;

  @override
  void initState() {
    super.initState();

    final isReduced = AppMotion.isReduced;
    final totalDuration = isReduced
        ? Duration.zero
        : const Duration(milliseconds: 7500);

    _controller = AnimationController(
      vsync: this,
      duration: totalDuration,
    );

    // 1. Ambient Glow (0.0 – 0.7s): Interval(0.000, 0.0933)
    _glowAnimation = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.000, 0.0933, curve: Curves.easeOutCubic),
    );

    // 2. Clear Logo Wipe / Reveal (0.7 – 2.5s): Interval(0.0933, 0.3333)
    _wipeAnimation = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.0933, 0.3333, curve: Curves.easeInOutCubic),
    );

    // 3. Logo Scale & Settle (2.5 – 3.2s): Interval(0.3333, 0.4267)
    _scaleAnimation = Tween<double>(begin: 0.90, end: 1.00).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.3333, 0.4267, curve: Curves.easeOutCubic),
      ),
    );

    // 4. Subtle Light Sheen (3.0 – 4.0s): Interval(0.4000, 0.5333)
    _sheenAnimation = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.4000, 0.5333, curve: Curves.easeInOut),
    );

    // 5. "SEVO" Title Entrance (3.5 – 4.6s): Interval(0.4667, 0.6133)
    _titleFadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.4667, 0.6133, curve: Curves.easeOut),
    );
    _titleSlideAnimation = Tween<Offset>(
      begin: const Offset(0.0, 0.30),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.4667, 0.6133, curve: Curves.easeOutCubic),
      ),
    );

    // 6. "WORKFORCE" Subtitle Entrance (4.5 – 5.4s): Interval(0.6000, 0.7200)
    _badgeFadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.6000, 0.7200, curve: Curves.easeOut),
    );
    _badgeSlideAnimation = Tween<Offset>(
      begin: const Offset(0.0, 0.25),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.6000, 0.7200, curve: Curves.easeOutCubic),
      ),
    );

    _controller.addStatusListener((status) {
      if (status == AnimationStatus.completed && mounted) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) {
            ref.read(splashControllerProvider.notifier).complete();
          }
        });
      }
    });

    if (isReduced) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          ref.read(splashControllerProvider.notifier).complete();
        }
      });
    } else {
      _controller.forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.peacockNavy,
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF061526), // Deepest peacock base
              Color(0xFF0A2540), // Peacock navy
              Color(0xFF004E89), // Peacock blue
            ],
            stops: [0.0, 0.45, 1.0],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              physics: const NeverScrollableScrollPhysics(),
              child: AnimatedBuilder(
                animation: _controller,
                builder: (context, child) {
                  final wipeProgress = _wipeAnimation.value;

                  return Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // ── 1. LOGO (120x120 tight bounding box) ───────────────
                      SizedBox(
                        width: 120,
                        height: 120,
                        child: Stack(
                          clipBehavior: Clip.none,
                          alignment: Alignment.center,
                          children: [
                            // Ambient Emerald Glow (positioned directly behind logo)
                            if (_glowAnimation.value > 0.01)
                              Positioned(
                                width: 180,
                                height: 180,
                                child: Transform.scale(
                                  scale: 0.60 + (_glowAnimation.value * 0.55),
                                  child: Opacity(
                                    opacity: (_glowAnimation.value * 0.40).clamp(0.0, 1.0),
                                    child: Container(
                                      decoration: BoxDecoration(
                                        shape: BoxShape.circle,
                                        gradient: RadialGradient(
                                          colors: [
                                            const Color(0xFF10B981).withValues(alpha: 0.65),
                                            const Color(0xFF004E89).withValues(alpha: 0.30),
                                            Colors.transparent,
                                          ],
                                          stops: const [0.0, 0.55, 1.0],
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),

                            // Entire Logo Card is Progressively Unveiled via Horizontal Wipe
                            Transform.scale(
                              scale: _scaleAnimation.value,
                              child: ClipRect(
                                clipper: _HorizontalWipeClipper(
                                  progress: wipeProgress,
                                ),
                                child: Container(
                                  width: 120,
                                  height: 120,
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(28),
                                    boxShadow: [
                                      BoxShadow(
                                        color: const Color(0xFF059669).withValues(
                                          alpha: 0.30 * wipeProgress,
                                        ),
                                        blurRadius: 24,
                                        spreadRadius: 3,
                                        offset: const Offset(0, 6),
                                      ),
                                    ],
                                  ),
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(28),
                                    child: Stack(
                                      fit: StackFit.expand,
                                      children: [
                                        // Official Sevo Logo Asset
                                        Padding(
                                          padding: const EdgeInsets.all(16.0),
                                          child: Image.asset(
                                            'assets/images/sevo_logo.png',
                                            fit: BoxFit.contain,
                                            errorBuilder: (context, error, stackTrace) =>
                                                const Icon(
                                              Icons.handyman_rounded,
                                              size: 60,
                                              color: Color(0xFF0A2540),
                                            ),
                                          ),
                                        ),

                                        // Luminous Leading Edge Beam (travels across during wipe)
                                        if (wipeProgress > 0.01 && wipeProgress < 0.99)
                                          CustomPaint(
                                            painter: _WipeLeadingBeamPainter(
                                              progress: wipeProgress,
                                            ),
                                          ),

                                        // Subtle Diagonal Sheen (sweeps across during settle)
                                        if (_sheenAnimation.value > 0.001 &&
                                            _sheenAnimation.value < 0.999)
                                          Positioned.fill(
                                            child: CustomPaint(
                                              painter: _SheenPainter(
                                                progress: _sheenAnimation.value,
                                              ),
                                            ),
                                          ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                      // ── Balanced, tight gap between Logo & SEVO ───────────
                      const SizedBox(height: 16),

                      // ── 2. "SEVO" Title Entrance (3.5 – 4.6s) ──────────────
                      SlideTransition(
                        position: _titleSlideAnimation,
                        child: FadeTransition(
                          opacity: _titleFadeAnimation,
                          child: const Text(
                            'SEVO',
                            style: TextStyle(
                              fontSize: 30,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 4.5,
                              color: Colors.white,
                              height: 1.1,
                            ),
                          ),
                        ),
                      ),

                      // ── Small, balanced gap between SEVO & WORKFORCE ────────
                      const SizedBox(height: 6),

                      // ── 3. "WORKFORCE" Subtitle Entrance (4.5 – 5.4s) ──────
                      SlideTransition(
                        position: _badgeSlideAnimation,
                        child: FadeTransition(
                          opacity: _badgeFadeAnimation,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 3.5,
                            ),
                            decoration: BoxDecoration(
                              color: const Color(0xFF059669).withValues(alpha: 0.16),
                              borderRadius: BorderRadius.circular(5),
                              border: Border.all(
                                color: const Color(0xFF34D399).withValues(alpha: 0.35),
                                width: 0.8,
                              ),
                            ),
                            child: const Text(
                              'WORKFORCE',
                              style: TextStyle(
                                fontSize: 10.5,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 2.5,
                                color: Color(0xFF6EE7B7),
                                height: 1.1,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Clips the child horizontally from left to right based on [progress] (0.0 -> 1.0).
class _HorizontalWipeClipper extends CustomClipper<Rect> {
  const _HorizontalWipeClipper({required this.progress});

  final double progress;

  @override
  Rect getClip(Size size) {
    final width = size.width * progress.clamp(0.0, 1.0);
    return Rect.fromLTRB(0, 0, width, size.height);
  }

  @override
  bool shouldReclip(covariant _HorizontalWipeClipper oldClipper) {
    return oldClipper.progress != progress;
  }
}

/// Paints a bright, luminous leading-edge wipe beam to make the wipe effect visually striking.
class _WipeLeadingBeamPainter extends CustomPainter {
  const _WipeLeadingBeamPainter({required this.progress});

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final x = size.width * progress.clamp(0.0, 1.0);
    const beamWidth = 16.0;

    // Glowing beam gradient centered at x
    final paint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.centerLeft,
        end: Alignment.centerRight,
        colors: [
          const Color(0xFF34D399).withValues(alpha: 0.0),
          const Color(0xFF6EE7B7).withValues(alpha: 0.75),
          Colors.white.withValues(alpha: 0.95),
          const Color(0xFF34D399).withValues(alpha: 0.0),
        ],
        stops: const [0.0, 0.45, 0.55, 1.0],
      ).createShader(Rect.fromLTWH(x - (beamWidth / 2), 0, beamWidth, size.height));

    canvas.drawRect(
      Rect.fromLTWH(x - (beamWidth / 2), 0, beamWidth, size.height),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant _WipeLeadingBeamPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}

/// Paints a sleek diagonal sheen line across the logo container.
class _SheenPainter extends CustomPainter {
  const _SheenPainter({required this.progress});

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final width = size.width;
    final height = size.height;

    // Sweeps diagonally from top-left to bottom-right
    final sweepDistance = width + height + 70;
    final currentOffset = -35.0 + (progress * sweepDistance);

    final paint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          Colors.white.withValues(alpha: 0.0),
          Colors.white.withValues(alpha: 0.35),
          Colors.white.withValues(alpha: 0.0),
        ],
        stops: const [0.0, 0.5, 1.0],
      ).createShader(Rect.fromLTWH(0, 0, width, height));

    final path = Path()
      ..moveTo(currentOffset - 20, 0)
      ..lineTo(currentOffset + 20, 0)
      ..lineTo(currentOffset - 20 + width, height)
      ..lineTo(currentOffset - 60 + width, height)
      ..close();

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _SheenPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
