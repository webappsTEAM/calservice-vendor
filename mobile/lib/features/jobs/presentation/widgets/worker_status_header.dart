import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/status_chip.dart';
import '../../../auth/presentation/auth_controller.dart';
import '../../../profile/presentation/profile_providers.dart';
import '../../../profile/presentation/widgets/employee_availability_toggle.dart';
import '../jobs_providers.dart';

/// Worker Profile / Current Status Header matching the specification:
///
/// Features:
/// - Avatar initial (dynamic from employee's actual name)
/// - Employee name (dynamic)
/// - SEPARATE Job Status: "ON JOB (BUSY)" or "NO ACTIVE JOB"
/// - Employee ID: "ID: ORG--0024" (dynamic)
/// - Availability section:
///   "Availability" header + [ ONLINE ] / [ OFFLINE ] interactive toggle pill
///
/// Ensures "ON JOB (BUSY)" is never merged or confused with availability.
class WorkerStatusHeader extends ConsumerWidget {
  const WorkerStatusHeader({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    final profileAsync = ref.watch(employeeProfileProvider);
    final hasActiveJob = ref.watch(hasActiveJobProvider);
    final activeJob = ref.watch(currentActiveJobProvider);
    final profile = profileAsync.valueOrNull;

    final displayName = profile != null && profile.fullName.trim().isNotEmpty
        ? profile.fullName
        : (user?.displayName.isNotEmpty == true ? user!.displayName : 'Technician');
    final initial = displayName.isNotEmpty ? displayName[0].toUpperCase() : 'T';
    final workerId = profile?.employeeId ?? user?.employeeId ?? user?.username ?? '—';
    final isOnline = profile?.isOnline ?? false;
    final activeJobRef = activeJob?.requestId ?? (activeJob?.id != null ? 'SR-${activeJob!.id}' : null);

    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 350;

        return Container(
          padding: EdgeInsets.all(isCompact ? AppSpacing.sm : AppSpacing.md),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: AppColors.border),
            boxShadow: const [
              BoxShadow(
                color: Color(0x08000000),
                blurRadius: 4,
                offset: Offset(0, 1),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Avatar
                  Container(
                    width: isCompact ? 40 : 46,
                    height: isCompact ? 40 : 46,
                    decoration: BoxDecoration(
                      color: const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(AppRadius.card),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      initial,
                      style: TextStyle(
                        fontSize: isCompact ? 17 : 19,
                        fontWeight: FontWeight.w900,
                        color: const Color(0xFF1E293B),
                      ),
                    ),
                  ),
                  SizedBox(width: isCompact ? AppSpacing.sm : AppSpacing.md),
                  // Details: Name, Job Status, ID
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          displayName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: isCompact ? 14 : 15.5,
                            fontWeight: FontWeight.w800,
                            color: const Color(0xFF0F172A),
                          ),
                        ),
                        const SizedBox(height: 3),
                        // 1. Separate Job Status (distinct from availability)
                        Row(
                          children: [
                            Flexible(
                              child: StatusChip(
                                status: hasActiveJob ? 'busy' : 'neutral',
                                label: hasActiveJob ? 'ON JOB (BUSY)' : 'NO ACTIVE JOB',
                                dense: true,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        // 2. Employee ID
                        Row(
                          children: [
                            const Text(
                              'ID: ',
                              style: TextStyle(
                                fontSize: 11,
                                fontFamily: 'monospace',
                                color: Color(0xFF64748B),
                              ),
                            ),
                            Flexible(
                              child: Text(
                                workerId,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 11,
                                  fontFamily: 'monospace',
                                  fontWeight: FontWeight.w700,
                                  color: Color(0xFF334155),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              const Divider(height: 1, color: Color(0xFFF1F5F9)),
              const SizedBox(height: AppSpacing.sm),
              // Availability Control Area
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Availability',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF1E293B),
                          ),
                        ),
                        const SizedBox(height: 1),
                        Text(
                          isOnline ? 'Ready for dispatch offers' : 'Offline • Not receiving offers',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w500,
                            color: Color(0xFF64748B),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  EmployeeAvailabilityToggle(
                    isOnline: isOnline,
                    hasActiveJob: hasActiveJob,
                    activeJobRef: activeJobRef,
                    dense: isCompact,
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}
