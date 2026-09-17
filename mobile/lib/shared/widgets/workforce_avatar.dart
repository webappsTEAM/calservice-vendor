import 'package:flutter/material.dart';

import '../../core/config/app_config.dart';
import '../../core/theme/app_theme.dart';

/// The official SEVO Workforce Avatar Widget.
///
/// Features:
/// - Supports both absolute (`https://...`) and relative (`/media/...`) backend image URLs.
/// - Smooth image loading with fade-in and subtle background loading state.
/// - Graceful fallback to initial badge upon network failure, 404, or empty URL.
/// - Never shows broken image icons or throws unhandled image exceptions.
/// - Optional presence indicator badge (online emerald, busy orange, offline slate).
/// - Follows the Peacock Blue + Emerald Green enterprise design system.
class WorkforceAvatar extends StatelessWidget {
  const WorkforceAvatar({
    super.key,
    this.imageUrl,
    this.name,
    this.initial,
    this.radius = 20,
    this.backgroundColor,
    this.foregroundColor,
    this.borderColor,
    this.borderWidth = 0,
    this.showPresence = false,
    this.isOnline = false,
    this.availability,
    this.fontSize,
    this.onTap,
  });

  /// The avatar URL (can be relative e.g. `/media/...` or absolute `https://...`).
  final String? imageUrl;

  /// Full name or display name to extract initial if [initial] is not provided.
  final String? name;

  /// Explicit initial string (e.g. "T", "M"). If omitted, computed from [name].
  final String? initial;

  /// Avatar circle radius. Total diameter will be 2 * radius.
  final double radius;

  /// Background color for the initial avatar.
  final Color? backgroundColor;

  /// Text color for the initial.
  final Color? foregroundColor;

  /// Optional outer ring border color.
  final Color? borderColor;

  /// Outer border width.
  final double borderWidth;

  /// Whether to show a live presence status badge on the bottom right.
  final bool showPresence;

  /// Whether technician is currently online.
  final bool isOnline;

  /// Specific availability string ('online', 'busy', 'offline').
  final String? availability;

  /// Custom font size for the initial text.
  final double? fontSize;

  /// Optional tap callback.
  final VoidCallback? onTap;

  String _resolveInitial() {
    if (initial != null && initial!.trim().isNotEmpty) {
      return initial!.trim()[0].toUpperCase();
    }
    if (name != null && name!.trim().isNotEmpty) {
      final parts = name!.trim().split(RegExp(r'\s+'));
      if (parts.isNotEmpty && parts[0].isNotEmpty) {
        return parts[0][0].toUpperCase();
      }
    }
    return 'T';
  }

  Color _resolvePresenceColor() {
    final status = (availability ?? (isOnline ? 'online' : 'offline')).toLowerCase();
    switch (status) {
      case 'online':
      case 'available':
        return const Color(0xFF10B981); // Emerald
      case 'busy':
      case 'on_job':
        return const Color(0xFFF59E0B); // Amber/Orange
      default:
        return const Color(0xFF94A3B8); // Slate
    }
  }

  @override
  Widget build(BuildContext context) {
    final resolvedUrl = AppConfig.resolveMediaUrl(imageUrl);
    final displayInitial = _resolveInitial();
    final size = radius * 2;
    final resolvedFontSize = fontSize ?? (radius * 0.85).clamp(10.0, 28.0);

    final defaultBg = backgroundColor ?? AppColors.primary.withValues(alpha: 0.12);
    final defaultFg = foregroundColor ?? AppColors.primary;

    Widget avatarCore;

    if (resolvedUrl != null && resolvedUrl.isNotEmpty) {
      avatarCore = ClipOval(
        child: Image.network(
          resolvedUrl,
          width: size,
          height: size,
          fit: BoxFit.cover,
          frameBuilder: (context, child, frame, wasSynchronouslyLoaded) {
            if (wasSynchronouslyLoaded || frame != null) {
              return child;
            }
            return _buildFallback(displayInitial, resolvedFontSize, defaultBg, defaultFg);
          },
          loadingBuilder: (context, child, loadingProgress) {
            if (loadingProgress == null) return child;
            return _buildFallback(displayInitial, resolvedFontSize, defaultBg, defaultFg);
          },
          errorBuilder: (context, error, stackTrace) {
            return _buildFallback(displayInitial, resolvedFontSize, defaultBg, defaultFg);
          },
        ),
      );
    } else {
      avatarCore = _buildFallback(displayInitial, resolvedFontSize, defaultBg, defaultFg);
    }

    Widget content = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: defaultBg,
        border: borderWidth > 0
            ? Border.all(
                color: borderColor ?? Colors.white.withValues(alpha: 0.8),
                width: borderWidth,
              )
            : null,
      ),
      child: avatarCore,
    );

    if (showPresence) {
      final badgeSize = (radius * 0.55).clamp(10.0, 16.0);
      final badgeBorderWidth = (badgeSize * 0.16).clamp(1.5, 2.5);

      content = Stack(
        clipBehavior: Clip.none,
        children: [
          content,
          Positioned(
            right: 0,
            bottom: 0,
            child: Container(
              width: badgeSize,
              height: badgeSize,
              decoration: BoxDecoration(
                color: _resolvePresenceColor(),
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.white,
                  width: badgeBorderWidth,
                ),
              ),
            ),
          ),
        ],
      );
    }

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(radius),
        child: content,
      );
    }

    return content;
  }

  Widget _buildFallback(String initial, double fontSize, Color bg, Color fg) {
    return Container(
      width: radius * 2,
      height: radius * 2,
      alignment: Alignment.center,
      color: bg,
      child: Text(
        initial,
        style: TextStyle(
          fontSize: fontSize,
          fontWeight: FontWeight.w900,
          color: fg,
          letterSpacing: 0.2,
        ),
      ),
    );
  }
}
