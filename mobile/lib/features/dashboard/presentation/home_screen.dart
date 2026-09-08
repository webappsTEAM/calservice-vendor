import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/location/location_service.dart';
import '../../../core/theme/app_theme.dart';
import '../../../routing/app_routes.dart';
import '../../../shared/widgets/async_value_view.dart';
import '../../../shared/widgets/empty_state.dart';
import '../../../shared/widgets/workforce_app_bar.dart';
import '../../../shared/widgets/workforce_showcase_section.dart';
import '../../jobs/domain/job.dart';
import '../../jobs/presentation/jobs_providers.dart';
import '../../jobs/presentation/widgets/active_job_card.dart';
import '../../jobs/presentation/widgets/job_list_tile.dart';
import '../../jobs/presentation/widgets/offer_card.dart';
import '../../profile/presentation/profile_providers.dart';
import 'widgets/authorized_services_card.dart';
import 'widgets/dashboard_live_map.dart';
import 'widgets/dashboard_status_card.dart';
import 'widgets/greeting_header.dart';
import 'widgets/today_overview_card.dart';

/// The official SEVO Workforce Employee / Technician Dashboard.
///
/// Vertically scrollable mobile layout matching the latest web portal IA:
/// 1. Employee greeting & header with WorkforceAvatar + live presence.
/// 2. Active Offer / Assigned Job card (if active).
/// 3. Technician Online/Offline status card with live toggle.
/// 4. Mobile-friendly site map & geofence radar section.
/// 5. Shift Standby card with clock-in/timer info.
/// 6. Current availability state card.
/// 7. GPS Accuracy + Completed Today stats.
/// 8. Authorized Service Capabilities card.
/// 9. Quick Actions & Recent Jobs Queue preview.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  double? _latitude;
  double? _longitude;
  double? _accuracy;
  bool _isGpsLoading = false;
  String? _locationError;

  @override
  void initState() {
    super.initState();
    // Non-blocking initial location fix
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fetchLocation(silent: true);
    });
  }

  Future<void> _fetchLocation({bool silent = false}) async {
    if (_isGpsLoading) return;

    if (!silent && mounted) {
      setState(() {
        _isGpsLoading = true;
        _locationError = null;
      });
    }

    try {
      final loc = await ref.read(locationServiceProvider).getCurrentPosition();
      if (!mounted) return;
      setState(() {
        _latitude = loc.latitude;
        _longitude = loc.longitude;
        _accuracy = loc.accuracy;
        _locationError = null;
        _isGpsLoading = false;
      });
    } on LocationFailure catch (e) {
      if (!mounted) return;
      setState(() {
        _locationError = e.message;
        _isGpsLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _locationError = 'Unable to resolve GPS location.';
        _isGpsLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final activeJobsAsync = ref.watch(activeJobsProvider);
    final completedJobsAsync = ref.watch(completedJobsProvider);
    final profileAsync = ref.watch(employeeProfileProvider);
    final shiftAsync = ref.watch(shiftStatusProvider);
    final incomingOffer = ref.watch(incomingOfferProvider);
    final currentActiveJob = ref.watch(currentActiveJobProvider);
    final hasActiveJob = ref.watch(hasActiveJobProvider);

    final isOnline = profileAsync.valueOrNull?.isOnline ?? false;
    final shift = shiftAsync.valueOrNull;
    final isClockedIn = shift?.isClockedIn ?? false;
    final isOnBreak = shift?.shiftStatus == 'on_break';
    final shiftStatusLabel = shift?.displayLabel ?? (isClockedIn ? 'Clocked In' : 'Standby');

    return Scaffold(
      appBar: const WorkforceAppBar(
        showStatusSubBar: true,
        titleText: 'Technician Cockpit',
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(activeJobsProvider);
          ref.invalidate(completedJobsProvider);
          ref.invalidate(employeeProfileProvider);
          ref.invalidate(shiftStatusProvider);
          await Future.wait([
            ref.read(activeJobsProvider.future),
            _fetchLocation(silent: true),
          ]);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.md,
            AppSpacing.lg,
            AppSpacing.xxl,
          ),
          children: [
            // ── 1. Employee Greeting / Header with WorkforceAvatar ─────────
            const GreetingHeader(),
            const SizedBox(height: AppSpacing.md),

            // ── 2. Incoming Offer or Active Job Priority Card ───────────────
            if (incomingOffer != null) ...[
              OfferCard(job: incomingOffer),
              const SizedBox(height: AppSpacing.md),
            ],
            if (currentActiveJob != null) ...[
              ActiveJobCard(job: currentActiveJob),
              const SizedBox(height: AppSpacing.md),
            ],

            // ── 3. Technician Online/Offline Status & Telemetry Cards ───────
            DashboardStatusCard(
              isOnline: isOnline,
              hasActiveJob: hasActiveJob,
              shiftStatusLabel: shiftStatusLabel,
              isClockedIn: isClockedIn,
              isOnBreak: isOnBreak,
              gpsAccuracy: _accuracy,
              completedJobsCount: completedJobsAsync.valueOrNull?.length ?? 0,
              onTapCompletedJobs: () => context.go(AppRoutes.jobs),
              activeJobNumber: currentActiveJob?.requestId,
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 4. Mobile-Friendly Live Map / Location Section ──────────────
            DashboardLiveMap(
              latitude: _latitude,
              longitude: _longitude,
              accuracy: _accuracy,
              isOnline: isOnline,
              isGpsLoading: _isGpsLoading,
              locationError: _locationError,
              onRefreshLocation: () => _fetchLocation(silent: false),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 5. Authorized Service Capabilities Card ─────────────────────
            AuthorizedServicesCard(
              services: profileAsync.valueOrNull?.allRequestedServices ?? const [],
              onTapManage: () => context.push(AppRoutes.moreServices),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── 6. Today Overview Stats & Quick Actions ─────────────────────
            TodayOverviewCard(
              activeCount: activeJobsAsync.valueOrNull?.length,
              completedCount: completedJobsAsync.valueOrNull?.length,
            ),
            const SizedBox(height: AppSpacing.md),
            const _QuickActionsSection(),
            const SizedBox(height: AppSpacing.md),

            // ── 7. Showcase Spotlight Section ──────────────────────────────
            WorkforceShowcaseSection(
              cardsPadding: EdgeInsets.zero,
              headingPadding: const EdgeInsets.only(bottom: AppSpacing.xs),
              onTap: () => context.go(AppRoutes.jobs),
            ),
            const SizedBox(height: AppSpacing.lg),

            // ── 8. Recent Activity / Queue ──────────────────────────────────
            AsyncValueView<List<Job>>(
              value: activeJobsAsync,
              onRetry: () => ref.invalidate(activeJobsProvider),
              builder: (context, activeJobs) => _HomeJobsSection(activeJobs: activeJobs),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickActionsSection extends StatelessWidget {
  const _QuickActionsSection();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _QuickActionTile(
          icon: Icons.work_outline_rounded,
          color: const Color(0xFF004E89),
          label: 'Jobs Queue',
          onTap: () => context.go(AppRoutes.jobs),
        ),
        const SizedBox(width: AppSpacing.sm),
        _QuickActionTile(
          icon: Icons.handyman_outlined,
          color: const Color(0xFF059669),
          label: 'My Services',
          onTap: () => context.push(AppRoutes.moreServices),
        ),
        const SizedBox(width: AppSpacing.sm),
        _QuickActionTile(
          icon: Icons.insights_rounded,
          color: const Color(0xFFD97706),
          label: 'Performance',
          onTap: () => context.push(AppRoutes.performance),
        ),
        const SizedBox(width: AppSpacing.sm),
        _QuickActionTile(
          icon: Icons.location_on_outlined,
          color: const Color(0xFF6366F1),
          label: 'Locations',
          onTap: () => context.push(AppRoutes.moreLocations),
        ),
      ],
    );
  }
}

class _QuickActionTile extends StatelessWidget {
  const _QuickActionTile({
    required this.icon,
    required this.color,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final Color color;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.cardStandard),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(AppRadius.cardStandard),
            border: Border.all(color: AppColors.border),
            boxShadow: AppElevation.subtle,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, size: 17, color: color),
              ),
              const SizedBox(height: 5),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HomeJobsSection extends ConsumerWidget {
  const _HomeJobsSection({required this.activeJobs});

  final List<Job> activeJobs;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hasActiveJob = ref.watch(hasActiveJobProvider);
    final incomingOffer = ref.watch(incomingOfferProvider);
    final currentActiveJob = ref.watch(currentActiveJobProvider);
    final completedJobs = ref.watch(completedJobsProvider).valueOrNull ?? const <Job>[];

    final remaining = activeJobs
        .where((j) => j.id != incomingOffer?.id && j.id != currentActiveJob?.id)
        .toList();
    final usingCompletedFallback = remaining.isEmpty;
    final pool = usingCompletedFallback ? completedJobs : remaining;
    final sectionTitle = usingCompletedFallback ? 'Recent Activity' : 'Upcoming';

    final nothingToShow = incomingOffer == null && currentActiveJob == null && pool.isEmpty;
    if (nothingToShow) {
      return const EmptyState(
        icon: Icons.task_alt_rounded,
        title: "You're all caught up",
        message: 'New job offers will appear here as soon as they come in.',
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (pool.isNotEmpty) ...[
          Row(
            children: [
              Text(sectionTitle, style: Theme.of(context).textTheme.labelSmall),
              const Spacer(),
              TextButton(
                onPressed: () => context.go(AppRoutes.jobs),
                style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(0, 32)),
                child: const Text('See all'),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
          for (final job in pool.take(3)) JobListTile(job: job, hasActiveJob: hasActiveJob),
        ],
      ],
    );
  }
}
