import 'package:flutter/material.dart';

/// Central motion tokens.
///
/// Mirrors the [AppColors.configure] pattern: `app.dart` calls
/// [configure] once per frame with the user's saved appearance preference,
/// so every animation in the app can consult a single source of truth for
/// whether motion is allowed.
///
/// The app already ships a "Reduce Animations & Transitions" setting, but
/// today it is wired only to page transitions. Routing new animations
/// through [duration] means adding motion cannot silently regress that
/// accessibility promise.
class AppMotion {
  AppMotion._();

  static bool _reduced = false;

  /// Called from `app.dart` alongside `AppColors.configure`.
  static void configure({required bool reducedMotion}) {
    _reduced = reducedMotion;
  }

  /// Whether the user has asked for reduced motion.
  static bool get isReduced => _reduced;

  // Durations — deliberately narrow. The approved band is 150–250ms.
  static const Duration fast = Duration(milliseconds: 150);
  static const Duration normal = Duration(milliseconds: 200);
  static const Duration slow = Duration(milliseconds: 250);

  /// Standard easing: decelerates into place, no overshoot or bounce.
  static const Curve curve = Curves.easeOutCubic;

  /// Per-item delay for staggered section entrances. Three sections is the
  /// intended maximum, so the last one starts 120ms in.
  static const Duration stagger = Duration(milliseconds: 60);

  /// Resolves a duration against the reduced-motion setting. Always route
  /// animation durations through this rather than using the constants
  /// directly, so a single check disables motion app-wide.
  static Duration resolve(Duration duration) =>
      _reduced ? Duration.zero : duration;

  /// The stagger delay for the item at [index], already reduced-motion
  /// aware and capped so long lists never accumulate a visible wait.
  static Duration staggerFor(int index, {int maxSteps = 3}) {
    if (_reduced) return Duration.zero;
    final steps = index.clamp(0, maxSteps);
    return stagger * steps;
  }
}
