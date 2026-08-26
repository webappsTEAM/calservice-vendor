import 'package:flutter/material.dart';

import 'app_theme.dart';

/// The Classic Enterprise type scale.
///
/// The audit found 570 inline `fontSize:` declarations against only 43 uses
/// of `Theme.of(context).textTheme`, spread across 18 distinct sizes —
/// including five half-point steps (9.5 / 10.5 / 11.5 / 12.5 / 13.5) that
/// are the fingerprint of per-screen hand-tuning.
///
/// These nine roles collapse that range into a hierarchy with a clear reason
/// to exist at every step. Screens adopt them progressively, phase by phase.
///
/// Deliberately additive: this does NOT alter [ThemeData.textTheme]. Those
/// slots (`bodyMedium` at 13.5, `titleMedium` at 15, ...) are consumed by 43
/// existing call sites and asserted by layout/overflow tests, so changing
/// them would cause exactly the broad visual regression Phase 1 must avoid.
///
/// Colours resolve through [AppColors], so every role is automatically
/// correct in dark mode and under high contrast.
class AppTypography {
  AppTypography._();

  /// Screen-dominating figure or hero title. Sparing use — one per screen.
  static TextStyle get displayTitle => TextStyle(
    fontSize: 22,
    fontWeight: FontWeight.w700,
    height: 1.25,
    color: AppColors.textPrimary,
  );

  /// The title of a screen or a major page region.
  static TextStyle get pageTitle => TextStyle(
    fontSize: 18,
    fontWeight: FontWeight.w700,
    height: 1.3,
    color: AppColors.textPrimary,
  );

  /// A section heading within a screen.
  static TextStyle get sectionTitle => TextStyle(
    fontSize: 15,
    fontWeight: FontWeight.w700,
    height: 1.3,
    color: AppColors.textPrimary,
  );

  /// The title line of a card or list row.
  static TextStyle get cardTitle => TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.w700,
    height: 1.3,
    color: AppColors.textPrimary,
  );

  /// Default reading text.
  static TextStyle get body => TextStyle(
    fontSize: 13,
    height: 1.45,
    color: AppColors.textPrimary,
  );

  /// Secondary explanatory text beneath a title.
  static TextStyle get supporting => TextStyle(
    fontSize: 12,
    height: 1.4,
    color: AppColors.textSecondary,
  );

  /// Timestamps, IDs, counts — low-emphasis detail.
  static TextStyle get metadata => TextStyle(
    fontSize: 11,
    height: 1.35,
    color: AppColors.textMuted,
  );

  /// The small uppercase group label above a section or field.
  static TextStyle get label => TextStyle(
    fontSize: 11,
    fontWeight: FontWeight.w700,
    letterSpacing: 0.6,
    height: 1.3,
    color: AppColors.textMuted,
  );

  /// Text inside a status chip/badge. Kept at 10.5 to match the existing
  /// [StatusChip] metrics exactly — badge widths are asserted by the
  /// responsive overflow tests, so this one half-step is retained on
  /// purpose rather than rounded.
  static const TextStyle statusText = TextStyle(
    fontSize: 10.5,
    fontWeight: FontWeight.w800,
    letterSpacing: 0.4,
    height: 1.2,
  );

  /// Monospace variant for request IDs and coordinates.
  static TextStyle get mono => TextStyle(
    fontSize: 11.5,
    fontFamily: 'monospace',
    color: AppColors.textMuted,
  );
}
