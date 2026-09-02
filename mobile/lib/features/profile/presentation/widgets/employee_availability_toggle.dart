import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../profile_providers.dart';

/// A polished, compact, accessible availability toggle pill for the Employee/Technician.
///
/// Features:
/// - Clear visual distinction between ONLINE (emerald indicator, subtle green glow/border)
///   and OFFLINE (neutral/slate indicator, subtle neutral background).
/// - Loading state: disables interaction, shows miniature spinner and `UPDATING...` label.
/// - Active job lock: visually communicates if offline transition is restricted due to active work.
/// - Accessibility: Semantic actions and status announcements.
/// - Responsive: Constrained box and flexible layout preventing RenderFlex overflows on narrow screens (320px+).
class EmployeeAvailabilityToggle extends ConsumerWidget {
  const EmployeeAvailabilityToggle({
    super.key,
    required this.isOnline,
    this.hasActiveJob = false,
    this.activeJobRef,
    this.dense = false,
  });

  final bool isOnline;
  final bool hasActiveJob;
  final String? activeJobRef;
  final bool dense;

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
                    final res = await ref
                        .read(availabilityControllerProvider.notifier)
                        .toggleAvailability(
                          currentOnline: isOnline,
                          hasActiveJob: hasActiveJob,
                          activeJobRef: activeJobRef,
                        );
                    if (res != null && context.mounted) {
                      ScaffoldMessenger.of(context).hideCurrentSnackBar();
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Row(
                            children: [
                              Icon(
                                res ? Icons.check_circle_rounded : Icons.power_settings_new_rounded,
                                color: res ? const Color(0xFF34D399) : Colors.white,
                                size: 18,
                              ),
                              const SizedBox(width: AppSpacing.sm),
                              Expanded(
                                child: Text(
                                  res
                                      ? 'You are now ONLINE and ready to receive dispatches.'
                                      : 'You are now OFFLINE.',
                                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
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
