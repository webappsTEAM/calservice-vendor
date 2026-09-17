import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/workforce_avatar.dart';
import '../../../auth/presentation/auth_controller.dart';
import '../../../jobs/presentation/jobs_providers.dart';
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

    final profile = profileAsync.valueOrNull;
    final displayName = profile?.fullName.trim().isNotEmpty == true
        ? profile!.fullName
        : (user?.displayName.trim().isNotEmpty == true
            ? user!.displayName
            : 'Technician');
    final initial = displayName.isNotEmpty ? displayName[0].toUpperCase() : 'T';
    final photoUrl = profile?.avatar ?? user?.avatar;
    final greeting = _greetingForHour(DateTime.now().hour);
    final isOnline = profile?.isOnline ?? false;

    final String roleTitle;
    if (profile?.title != null && profile!.title!.trim().isNotEmpty) {
      roleTitle = profile.title!.trim();
    } else if (user?.role != null && user!.role.isNotEmpty) {
      roleTitle = user.role == 'employee' ? 'Senior Technician' : user.role.toUpperCase();
    } else {
      roleTitle = 'Field Technician';
    }

    final String companyName;
    if (profile?.companyName != null && profile!.companyName!.trim().isNotEmpty) {
      companyName = profile.companyName!.trim();
    } else if (user?.companyName != null && user!.companyName!.trim().isNotEmpty) {
      companyName = user.companyName!.trim();
    } else {
      companyName = 'SEVO Workforce Partner';
    }

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
                WorkforceAvatar(
                  imageUrl: photoUrl,
                  name: displayName,
                  initial: initial,
                  radius: 28,
                  fontSize: 20,
                  backgroundColor: Colors.white.withValues(alpha: 0.2),
                  foregroundColor: Colors.white,
                  showPresence: true,
                  isOnline: isOnline,
                  availability: profile?.liveAvailability,
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              greeting,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 11.5,
                                color: Colors.white.withValues(alpha: 0.8),
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Flexible(
                            child: Text(
                              '•  $roleTitle',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 11.5,
                                color: Color(0xFF6EE7B7),
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
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
                      const SizedBox(height: 2),
                      Row(
                        children: [
                          Icon(
                            Icons.business_rounded,
                            size: 12,
                            color: Colors.white.withValues(alpha: 0.7),
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              companyName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.white.withValues(alpha: 0.8),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: [
                          InkWell(
                            onTap: () async {
                              final hasActiveJob = ref.read(hasActiveJobProvider);
                              final activeJob = ref.read(currentActiveJobProvider);
                              final res = await ref.read(availabilityControllerProvider.notifier).toggleAvailability(
                                currentOnline: isOnline,
                                hasActiveJob: hasActiveJob,
                                activeJobRef: activeJob?.requestId,
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
                                                ? 'You are now online and available for jobs.'
                                                : 'You are now offline.',
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
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: (isOnline ? const Color(0xFF10B981) : Colors.grey)
                                    .withValues(alpha: 0.25),
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(
                                  color: (isOnline ? const Color(0xFF34D399) : Colors.grey)
                                      .withValues(alpha: 0.5),
                                  width: 0.8,
                                ),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: 6,
                                    height: 6,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: isOnline ? const Color(0xFF34D399) : Colors.white70,
                                    ),
                                  ),
                                  const SizedBox(width: 4),
                                  Text(
                                    isOnline ? 'ONLINE' : 'OFFLINE',
                                    style: const TextStyle(
                                      fontSize: 9.5,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 0.6,
                                      color: Colors.white,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          shiftAsync.maybeWhen(
                            data: (shift) => shift == null
                                ? const SizedBox.shrink()
                                : Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
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

