import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../profile_providers.dart';

/// Displays the confirmation dialog when an employee attempts to switch availability to offline.
Future<bool> showGoingOfflineDialog(BuildContext context) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text(
        'Going Offline?',
        style: TextStyle(
          fontWeight: FontWeight.w800,
          fontSize: 17,
          color: Color(0xFF0F172A),
        ),
      ),
      content: const Text(
        'You may stop receiving new service offers while you are offline.',
        style: TextStyle(
          fontSize: 13.5,
          height: 1.4,
          color: Color(0xFF334155),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xFF475569),
            foregroundColor: Colors.white,
          ),
          onPressed: () => Navigator.of(ctx).pop(true),
          child: const Text('Go Offline'),
        ),
      ],
    ),
  );
  return result ?? false;
}

/// Displays the interactive Availability Selector Bottom Sheet matching web workforce specs.
Future<void> showAvailabilitySelectorSheet(
  BuildContext context,
  WidgetRef ref, {
  required bool isOnline,
  required bool hasActiveJob,
  String? activeJobRef,
}) async {
  await showModalBottomSheet<void>(
    context: context,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
    ),
    builder: (ctx) => _AvailabilitySelectorModal(
      isOnline: isOnline,
      hasActiveJob: hasActiveJob,
      activeJobRef: activeJobRef,
    ),
  );
}

class _AvailabilitySelectorModal extends ConsumerWidget {
  const _AvailabilitySelectorModal({
    required this.isOnline,
    required this.hasActiveJob,
    this.activeJobRef,
  });

  final bool isOnline;
  final bool hasActiveJob;
  final String? activeJobRef;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final availState = ref.watch(availabilityControllerProvider);
    final isLoading = availState.isLoading;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          AppSpacing.md,
          AppSpacing.lg,
          AppSpacing.xl,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Handle bar
            Center(
              child: Container(
                width: 36,
                height: 4,
                margin: const EdgeInsets.only(bottom: AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            // Header Row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Update Availability Status',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0F172A),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Select your active dispatch status. Online technicians receive high-priority service dispatches in their active operating zones.',
              style: TextStyle(fontSize: 12, color: AppColors.textSecondary, height: 1.35),
            ),
            const SizedBox(height: AppSpacing.lg),

            // Option 1: 🟢 Online / Available
            _AvailabilityOptionTile(
              title: 'Online / Available',
              subtitle: 'Available to receive new service requests',
              isSelected: isOnline,
              accentColor: const Color(0xFF059669),
              bgColor: const Color(0xFFECFDF5),
              borderColor: isOnline ? const Color(0xFF10B981) : const Color(0xFFE2E8F0),
              icon: Icons.check_circle_rounded,
              onTap: isLoading || isOnline
                  ? null
                  : () async {
                      Navigator.of(context).pop();
                      final res = await ref
                          .read(availabilityControllerProvider.notifier)
                          .setAvailability(
                            targetOnline: true,
                            hasActiveJob: hasActiveJob,
                            activeJobRef: activeJobRef,
                          );
                      if (res == true && context.mounted) {
                        ScaffoldMessenger.of(context).hideCurrentSnackBar();
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Row(
                              children: const [
                                Icon(Icons.check_circle_rounded, color: Color(0xFF34D399), size: 18),
                                SizedBox(width: AppSpacing.sm),
                                Expanded(
                                  child: Text(
                                    'You are now online and available for jobs.',
                                    style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                            ),
                            backgroundColor: const Color(0xFF0F172A),
                            behavior: SnackBarBehavior.floating,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
                            duration: const Duration(milliseconds: 3000),
                          ),
                        );
                      }
                    },
            ),
            const SizedBox(height: AppSpacing.md),

            // Option 2: ⚪ Offline / Unavailable
            _AvailabilityOptionTile(
              title: 'Offline / Unavailable',
              subtitle: 'Currently unavailable for new service requests',
              isSelected: !isOnline,
              accentColor: const Color(0xFF64748B),
              bgColor: const Color(0xFFF8FAFC),
              borderColor: !isOnline ? const Color(0xFF94A3B8) : const Color(0xFFE2E8F0),
              icon: Icons.power_settings_new_rounded,
              onTap: isLoading || !isOnline
                  ? null
                  : () async {
                      Navigator.of(context).pop();
                      if (hasActiveJob) {
                        ref
                            .read(availabilityControllerProvider.notifier)
                            .setAvailability(
                              targetOnline: false,
                              hasActiveJob: hasActiveJob,
                              activeJobRef: activeJobRef,
                            );
                        return;
                      }

                      final confirmed = await showGoingOfflineDialog(context);
                      if (!confirmed || !context.mounted) return;

                      final res = await ref
                          .read(availabilityControllerProvider.notifier)
                          .setAvailability(
                            targetOnline: false,
                            hasActiveJob: hasActiveJob,
                            activeJobRef: activeJobRef,
                          );
                      if (res == false && context.mounted) {
                        ScaffoldMessenger.of(context).hideCurrentSnackBar();
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Row(
                              children: const [
                                Icon(Icons.power_settings_new_rounded, color: Colors.white, size: 18),
                                SizedBox(width: AppSpacing.sm),
                                Expanded(
                                  child: Text(
                                    'You are now offline.',
                                    style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                            ),
                            backgroundColor: const Color(0xFF0F172A),
                            behavior: SnackBarBehavior.floating,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
                            duration: const Duration(milliseconds: 3000),
                          ),
                        );
                      }
                    },
            ),
          ],
        ),
      ),
    );
  }
}

class _AvailabilityOptionTile extends StatelessWidget {
  const _AvailabilityOptionTile({
    required this.title,
    required this.subtitle,
    required this.isSelected,
    required this.accentColor,
    required this.bgColor,
    required this.borderColor,
    required this.icon,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final bool isSelected;
  final Color accentColor;
  final Color bgColor;
  final Color borderColor;
  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.card),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(AppRadius.card),
          border: Border.all(color: borderColor, width: isSelected ? 1.5 : 1.0),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: accentColor.withValues(alpha: 0.12),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ]
              : null,
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: isSelected
                    ? accentColor.withValues(alpha: 0.15)
                    : Colors.white,
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 20, color: accentColor),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: isSelected ? const Color(0xFF0F172A) : AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 11.5,
                      color: AppColors.textMuted,
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ),
            if (isSelected)
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: accentColor,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.check, size: 12, color: Colors.white),
              ),
          ],
        ),
      ),
    );
  }
}

/// A polished, compact, accessible availability toggle pill for the Employee/Technician.
///
/// Features:
/// - Clear visual distinction between ONLINE (emerald indicator, subtle green glow/border)
///   and OFFLINE (neutral/slate indicator, subtle neutral background).
/// - Loading state: disables interaction, shows miniature spinner and `UPDATING...` label.
/// - Active job lock: visually communicates if offline transition is restricted due to active work.
/// - Confirmation dialog when switching to offline.
/// - Accessibility: Semantic actions and status announcements.
/// - Responsive: Constrained box and flexible layout preventing RenderFlex overflows on narrow screens (320px+).
class EmployeeAvailabilityToggle extends ConsumerWidget {
  const EmployeeAvailabilityToggle({
    super.key,
    required this.isOnline,
    this.hasActiveJob = false,
    this.activeJobRef,
    this.dense = false,
    this.showConfirmation = false,
  });

  final bool isOnline;
  final bool hasActiveJob;
  final String? activeJobRef;
  final bool dense;
  final bool showConfirmation;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final availState = ref.watch(availabilityControllerProvider);
    final isLoading = availState.isLoading;

    // Listen for availability errors and present a concise, non-intrusive floating SnackBar
    ref.listen<AvailabilityState>(availabilityControllerProvider, (previous, next) {
      if (next.errorMessage != null && next.errorMessage != previous?.errorMessage) {
        ScaffoldMessenger.of(context).hideCurrentSnackBar();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.info_outline_rounded, color: Colors.white, size: 18),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    next.errorMessage!,
                    style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
            backgroundColor: const Color(0xFF1E293B),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
            duration: const Duration(seconds: 4),
          ),
        );
        ref.read(availabilityControllerProvider.notifier).clearError();
      }
    });

    final actionTooltip = hasActiveJob && isOnline
        ? 'Locked Online: Currently active on assignment ($activeJobRef)'
        : (isOnline ? 'Switch availability to OFFLINE' : 'Switch availability to ONLINE');

    final semanticLabel = isOnline
        ? 'Current availability: Online. Tap to set availability offline.'
        : 'Current availability: Offline. Tap to set availability online.';

    return Semantics(
      button: true,
      enabled: !isLoading,
      label: semanticLabel,
      child: Tooltip(
        message: actionTooltip,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: isLoading
                ? null
                : () async {
                    if (isOnline) {
                      // Attempting to go offline
                      if (hasActiveJob) {
                        ref
                            .read(availabilityControllerProvider.notifier)
                            .setAvailability(
                              targetOnline: false,
                              hasActiveJob: hasActiveJob,
                              activeJobRef: activeJobRef,
                            );
                        return;
                      }

                      if (showConfirmation) {
                        final confirmed = await showGoingOfflineDialog(context);
                        if (!confirmed || !context.mounted) return;
                      }

                      final res = await ref
                          .read(availabilityControllerProvider.notifier)
                          .setAvailability(
                            targetOnline: false,
                            hasActiveJob: hasActiveJob,
                            activeJobRef: activeJobRef,
                          );
                      if (res == false && context.mounted) {
                        ScaffoldMessenger.of(context).hideCurrentSnackBar();
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Row(
                              children: const [
                                Icon(
                                  Icons.power_settings_new_rounded,
                                  color: Colors.white,
                                  size: 18,
                                ),
                                SizedBox(width: AppSpacing.sm),
                                Expanded(
                                  child: Text(
                                    'You are now offline.',
                                    style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                            ),
                            backgroundColor: const Color(0xFF0F172A),
                            behavior: SnackBarBehavior.floating,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
                            duration: const Duration(milliseconds: 3000),
                          ),
                        );
                      }
                    } else {
                      // Attempting to go online
                      final res = await ref
                          .read(availabilityControllerProvider.notifier)
                          .setAvailability(
                            targetOnline: true,
                            hasActiveJob: hasActiveJob,
                            activeJobRef: activeJobRef,
                          );
                      if (res == true && context.mounted) {
                        ScaffoldMessenger.of(context).hideCurrentSnackBar();
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Row(
                              children: const [
                                Icon(
                                  Icons.check_circle_rounded,
                                  color: Color(0xFF34D399),
                                  size: 18,
                                ),
                                SizedBox(width: AppSpacing.sm),
                                Expanded(
                                  child: Text(
                                    'You are now online and available for jobs.',
                                    style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                            ),
                            backgroundColor: const Color(0xFF0F172A),
                            behavior: SnackBarBehavior.floating,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
                            duration: const Duration(milliseconds: 3000),
                          ),
                        );
                      }
                    }
                  },
            borderRadius: BorderRadius.circular(999),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeInOut,
              padding: EdgeInsets.symmetric(
                horizontal: dense ? 10 : 13,
                vertical: dense ? 5 : 7,
              ),
              decoration: BoxDecoration(
                color: isLoading
                    ? const Color(0xFFF1F5F9)
                    : (isOnline ? const Color(0xFFECFDF5) : const Color(0xFFF8FAFC)),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(
                  color: isLoading
                      ? const Color(0xFFCBD5E1)
                      : (isOnline ? const Color(0xFF10B981) : const Color(0xFFCBD5E1)),
                  width: 1.2,
                ),
                boxShadow: isOnline && !isLoading
                    ? [
                        BoxShadow(
                          color: const Color(0xFF10B981).withValues(alpha: 0.18),
                          blurRadius: 6,
                          offset: const Offset(0, 2),
                        ),
                      ]
                    : [
                        const BoxShadow(
                          color: Color(0x0A000000),
                          blurRadius: 3,
                          offset: Offset(0, 1),
                        ),
                      ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  if (isLoading) ...[
                    const SizedBox(
                      width: 11,
                      height: 11,
                      child: CircularProgressIndicator(
                        strokeWidth: 1.8,
                        valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF64748B)),
                      ),
                    ),
                    const SizedBox(width: 6),
                    const Text(
                      'UPDATING...',
                      style: TextStyle(
                        fontSize: 10.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                        color: Color(0xFF64748B),
                      ),
                    ),
                  ] else ...[
                    // Status dot
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isOnline ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                        border: isOnline
                            ? null
                            : Border.all(color: const Color(0xFF64748B), width: 1.2),
                        boxShadow: isOnline
                            ? [
                                BoxShadow(
                                  color: const Color(0xFF10B981).withValues(alpha: 0.6),
                                  blurRadius: 4,
                                  spreadRadius: 0.5,
                                ),
                              ]
                            : null,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      isOnline ? '● ONLINE' : '○ OFFLINE',
                      style: TextStyle(
                        fontSize: dense ? 10.5 : 11.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                        color: isOnline ? const Color(0xFF065F46) : const Color(0xFF475569),
                      ),
                    ),
                    if (hasActiveJob && isOnline) ...[
                      const SizedBox(width: 4),
                      const Icon(
                        Icons.lock_outline_rounded,
                        size: 11,
                        color: Color(0xFF065F46),
                      ),
                    ],
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
