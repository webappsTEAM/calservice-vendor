import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../profile/presentation/profile_providers.dart';

/// Dashboard status card combining:
/// 1. Online / Offline toggle card with restriction handling and confirmation dialogs
/// 2. Shift Standby card
/// 3. Current availability card
/// 4. GPS Accuracy + Completed Today telemetry stats
class DashboardStatusCard extends ConsumerWidget {
  const DashboardStatusCard({
    super.key,
    required this.isOnline,
    required this.hasActiveJob,
    required this.shiftStatusLabel,
    required this.isClockedIn,
    this.shiftElapsedText,
    this.isOnBreak = false,
    this.gpsAccuracy,
    required this.completedJobsCount,
    required this.onTapCompletedJobs,
    this.activeJobNumber,
  });

  final bool isOnline;
  final bool hasActiveJob;
  final String shiftStatusLabel;
  final bool isClockedIn;
  final String? shiftElapsedText;
  final bool isOnBreak;
  final double? gpsAccuracy;
  final int completedJobsCount;
  final VoidCallback onTapCompletedJobs;
  final String? activeJobNumber;

  Future<void> _handleAvailabilityToggle(BuildContext context, WidgetRef ref) async {
    final availabilityController = ref.read(availabilityControllerProvider.notifier);

    if (isOnline) {
      if (hasActiveJob) {
        availabilityController.setAvailability(
          targetOnline: false,
          hasActiveJob: hasActiveJob,
          activeJobRef: activeJobNumber,
        );
        return;
      }

      final res = await availabilityController.setAvailability(
        targetOnline: false,
        hasActiveJob: hasActiveJob,
        activeJobRef: activeJobNumber,
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
    } else {
      final res = await availabilityController.setAvailability(
        targetOnline: true,
        hasActiveJob: hasActiveJob,
        activeJobRef: activeJobNumber,
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
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final availabilityState = ref.watch(availabilityControllerProvider);

    final String availabilityBadgeText;
    final Color availabilityColor;
    if (hasActiveJob) {
      availabilityBadgeText = 'ON JOB';
      availabilityColor = const Color(0xFFF59E0B);
    } else if (isOnline) {
      availabilityBadgeText = 'AVAILABLE';
      availabilityColor = const Color(0xFF10B981);
    } else {
      availabilityBadgeText = 'OFFLINE';
      availabilityColor = const Color(0xFF94A3B8);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // ── 1. Online/Offline Status & Toggle Card ──────────────────────────
        Card(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    InkWell(
                      onTap: () => _handleAvailabilityToggle(context, ref),
                      borderRadius: BorderRadius.circular(6),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                        decoration: BoxDecoration(
                          color: (isOnline ? const Color(0xFFD1FAE5) : const Color(0xFFF1F5F9)),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: (isOnline ? const Color(0xFF6EE7B7) : const Color(0xFFCBD5E1)),
                            width: 0.8,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 7,
                              height: 7,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: isOnline ? const Color(0xFF059669) : const Color(0xFF64748B),
                              ),
                            ),
                            const SizedBox(width: 5),
                            Text(
                              isOnline ? 'ONLINE • READY FOR DISPATCH' : 'OFFLINE',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0.5,
                                color: isOnline ? const Color(0xFF065F46) : const Color(0xFF475569),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    if (availabilityState.isLoading)
                      const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.2),
                      )
                    else
                      Transform.scale(
                        scale: 0.85,
                        child: Switch.adaptive(
                          value: isOnline,
                          activeThumbColor: const Color(0xFF004E89),
                          activeTrackColor: const Color(0xFF6EE7B7),
                          onChanged: (_) => _handleAvailabilityToggle(context, ref),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  isOnline
                      ? 'Online — Available for Jobs'
                      : 'Offline — Currently Unavailable',
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0F172A),
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  isOnline
                      ? 'Available to receive new service requests. You will be alerted instantly when a booking is dispatched.'
                      : 'Currently unavailable for new service requests. Switch online when ready for dispatch offers.',
                  style: TextStyle(
                    fontSize: 12,
                    height: 1.4,
                    color: AppColors.textSecondary,
                  ),
                ),
                if (availabilityState.errorMessage != null) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFEF2F2),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFFFCA5A5)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.info_outline_rounded, size: 15, color: Color(0xFFDC2626)),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            availabilityState.errorMessage!,
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF991B1B),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),

        // ── 2. Shift Standby Card ───────────────────────────────────────────
        Card(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 12),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: isClockedIn
                        ? const Color(0xFF059669).withValues(alpha: 0.12)
                        : const Color(0xFF004E89).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    isClockedIn ? Icons.timer_outlined : Icons.schedule_rounded,
                    size: 19,
                    color: isClockedIn ? const Color(0xFF059669) : const Color(0xFF004E89),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            isClockedIn ? 'Shift Active' : 'Shift Standby',
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF0F172A),
                            ),
                          ),
                          if (isOnBreak) ...[
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                              decoration: BoxDecoration(
                                color: const Color(0xFFFEF3C7),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: const Text(
                                'PAUSED',
                                style: TextStyle(
                                  fontSize: 9,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFFB45309),
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        isClockedIn
                            ? (shiftElapsedText != null && shiftElapsedText!.isNotEmpty
                                ? 'Duration: $shiftElapsedText'
                                : 'Clocked in and working on assigned task')
                            : 'Starts automatically upon Customer OTP verification',
                        style: TextStyle(
                          fontSize: 11,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                  decoration: BoxDecoration(
                    color: isClockedIn ? const Color(0xFFECFDF5) : const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: isClockedIn ? const Color(0xFFA7F3D0) : const Color(0xFFE2E8F0),
                    ),
                  ),
                  child: Text(
                    shiftStatusLabel.toUpperCase(),
                    style: TextStyle(
                      fontSize: 9.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.4,
                      color: isClockedIn ? const Color(0xFF065F46) : const Color(0xFF64748B),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),

        // ── 3. Current Availability Card ────────────────────────────────────
        Card(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 12),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: availabilityColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    hasActiveJob
                        ? Icons.bolt_rounded
                        : (isOnline ? Icons.radar_rounded : Icons.power_settings_new_rounded),
                    size: 19,
                    color: availabilityColor,
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Text(
                            'Availability State',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF0F172A),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                            decoration: BoxDecoration(
                              color: availabilityColor.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(
                                color: availabilityColor.withValues(alpha: 0.5),
                                width: 0.8,
                              ),
                            ),
                            child: Text(
                              availabilityBadgeText,
                              style: TextStyle(
                                fontSize: 9.5,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0.4,
                                color: availabilityColor,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        hasActiveJob
                            ? 'Currently on job. Next dispatches held until finish.'
                            : (isOnline
                                ? 'Active and eligible for matching bookings'
                                : 'Offline. Not receiving dispatch requests'),
                        style: TextStyle(
                          fontSize: 11,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),

        // ── 4. GPS Accuracy + Completed Today 2-Column Stats ─────────────────
        Row(
          children: [
            // GPS Accuracy Tile
            Expanded(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'GPS ACCURACY',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.6,
                          color: AppColors.textMuted,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          Icon(
                            Icons.cell_tower_rounded,
                            size: 16,
                            color: isOnline ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              gpsAccuracy != null
                                  ? '±${gpsAccuracy!.round()}m Fix'
                                  : (isOnline ? 'Acquiring...' : 'Inactive'),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF0F172A),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),

            // Completed Today Tile
            Expanded(
              child: InkWell(
                onTap: onTapCompletedJobs,
                borderRadius: BorderRadius.circular(AppRadius.cardStandard),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'COMPLETED TODAY',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.6,
                            color: AppColors.textMuted,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            const Icon(
                              Icons.check_circle_outline_rounded,
                              size: 16,
                              color: Color(0xFF0284C7),
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                '$completedJobsCount Job${completedJobsCount == 1 ? '' : 's'}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF0F172A),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
