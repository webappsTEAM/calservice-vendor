import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
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
import 'widgets/greeting_header.dart';
import 'widgets/today_overview_card.dart';

/// The Home overview — deliberately not a copy of the desktop dashboard.
/// Shows only what the technician needs to understand at a glance: who they
/// are, whether they're online, an incoming offer or active job if there is
/// one, and a small recent-activity preview. Everything else lives on its
/// own tab.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activeJobsAsync = ref.watch(activeJobsProvider);
    final completedJobsAsync = ref.watch(completedJobsProvider);

    return Scaffold(
      appBar: const WorkforceAppBar(showStatusSubBar: true),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(activeJobsProvider);
          ref.invalidate(completedJobsProvider);
          ref.invalidate(employeeProfileProvider);
          ref.invalidate(shiftStatusProvider);
          await ref.read(activeJobsProvider.future);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.xxl,
          ),
          children: [
            const GreetingHeader(),
            const SizedBox(height: AppSpacing.md),
            WorkforceShowcaseSection(
              cardsPadding: EdgeInsets.zero,
              headingPadding: const EdgeInsets.only(bottom: AppSpacing.xs),
              onTap: () => context.go('/jobs'),
            ),
            const SizedBox(height: AppSpacing.md),
            TodayOverviewCard(
              activeCount: activeJobsAsync.valueOrNull?.length,
              completedCount: completedJobsAsync.valueOrNull?.length,
            ),
            const SizedBox(height: AppSpacing.md),
            const _QuickActionsSection(),
            const SizedBox(height: AppSpacing.lg),
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
          onTap: () => context.go('/jobs'),
        ),
        const SizedBox(width: AppSpacing.sm),
        _QuickActionTile(
          icon: Icons.handyman_outlined,
          color: const Color(0xFF059669),
          label: 'My Services',
          onTap: () => context.push('/more/services'),
        ),
        const SizedBox(width: AppSpacing.sm),
        _QuickActionTile(
          icon: Icons.insights_rounded,
          color: const Color(0xFFD97706),
          label: 'Performance',
          onTap: () => context.push('/more/performance'),
        ),
        const SizedBox(width: AppSpacing.sm),
        _QuickActionTile(
          icon: Icons.location_on_outlined,
          color: const Color(0xFF6366F1),
          label: 'Locations',
          onTap: () => context.push('/more/locations'),
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
        if (incomingOffer != null) ...[
          OfferCard(job: incomingOffer),
          const SizedBox(height: AppSpacing.lg),
        ],
        if (currentActiveJob != null) ...[
          ActiveJobCard(job: currentActiveJob),
          const SizedBox(height: AppSpacing.lg),
        ],
        if (pool.isNotEmpty) ...[
          Row(
            children: [
              Text(sectionTitle, style: Theme.of(context).textTheme.labelSmall),
              const Spacer(),
              TextButton(
                onPressed: () => context.go('/jobs'),
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
