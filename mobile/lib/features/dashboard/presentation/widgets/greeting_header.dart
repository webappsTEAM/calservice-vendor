import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../auth/presentation/auth_controller.dart';
import '../../../profile/presentation/profile_providers.dart';

String _greetingForHour(int hour) {
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

/// The official SEVO Workforce Greeting Hero.
///
/// Features:
/// - Peacock gradient styling (Deep Navy to Peacock Blue with Emerald accent).
/// - Avatar with live presence ring.
/// - Personalized greeting, name, and live status chips.
class GreetingHeader extends ConsumerWidget {
  const GreetingHeader({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    final profileAsync = ref.watch(employeeProfileProvider);
    final shiftAsync = ref.watch(shiftStatusProvider);

    final displayName = user?.displayName ?? 'Technician';
    final initial = displayName.isNotEmpty ? displayName[0].toUpperCase() : 'T';
    final greeting = _greetingForHour(DateTime.now().hour);
    final isOnline = profileAsync.valueOrNull?.isOnline ?? false;

    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF0A2540), // Deep Peacock Navy
            Color(0xFF004E89), // Royal Peacock Blue
            Color(0xFF065F46), // Emerald
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF004E89).withValues(alpha: 0.25),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Stack(
        children: [
          Positioned(
            right: -24,
            top: -24,
            child: Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.05),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Stack(
                  children: [
                    CircleAvatar(
                      radius: 26,
                      backgroundColor: Colors.white.withValues(alpha: 0.2),
                      child: Text(
                        initial,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    Positioned(
                      right: 0,
                      bottom: 0,
                      child: Container(
                        width: 13,
                        height: 13,
                        decoration: BoxDecoration(
                          color: isOnline
                              ? const Color(0xFF10B981)
                              : const Color(0xFF94A3B8),
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 2),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        greeting,
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.white.withValues(alpha: 0.8),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        displayName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: [
                          profileAsync.maybeWhen(
                            data: (profile) => Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: (profile.isOnline ? const Color(0xFF10B981) : Colors.grey)
                                    .withValues(alpha: 0.25),
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(
                                  color: (profile.isOnline ? const Color(0xFF34D399) : Colors.grey)
                                      .withValues(alpha: 0.5),
                                  width: 0.8,
                                ),
                              ),
                              child: Text(
                                profile.isOnline ? 'ONLINE' : 'OFFLINE',
                                style: const TextStyle(
                                  fontSize: 9.5,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 0.6,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                            orElse: () => const SizedBox.shrink(),
                          ),
                          shiftAsync.maybeWhen(
                            data: (shift) => shift == null
                                ? const SizedBox.shrink()
                                : Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: Colors.white.withValues(alpha: 0.2),
                                      borderRadius: BorderRadius.circular(999),
                                    ),
                                    child: Text(
                                      shift.displayLabel.toUpperCase(),
                                      style: const TextStyle(
                                        fontSize: 9.5,
                                        fontWeight: FontWeight.w800,
                                        letterSpacing: 0.6,
                                        color: Colors.white,
                                      ),
                                    ),
                                  ),
                            orElse: () => const SizedBox.shrink(),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

