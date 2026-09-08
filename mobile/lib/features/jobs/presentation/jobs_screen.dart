import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../../routing/app_routes.dart';
import '../../../shared/widgets/empty_state.dart';
import '../../notifications/presentation/notifications_providers.dart';
import '../../profile/presentation/profile_providers.dart';
import '../domain/job.dart';
import 'jobs_providers.dart';
import 'widgets/job_card.dart';
import 'widgets/job_card_skeleton.dart';
import 'widgets/job_category_filter_bar.dart';
import 'widgets/job_status_filter_bar.dart';
import 'widgets/new_offer_banner.dart';

/// Classic Premium Jobs & Orders screen for Workforce mobile app.
///
/// Features:
/// 1. Classic App Bar: "My Orders & Jobs" + Job count badge + Search toggle
/// 2. New Service Offer Alert banner (when pending offers exist)
/// 3. Horizontally scrollable Job Status Filters (All, New Offers, In Progress, Completed)
/// 4. Horizontally scrollable Category Filters (All, Electrical, AC, Plumbing, etc.)
/// 5. Classic Job Cards with full hierarchy, customer actions, and status action bars
/// 6. Pull-to-refresh and professional loading/empty/error states
class JobsScreen extends ConsumerStatefulWidget {
  const JobsScreen({super.key});

  @override
  ConsumerState<JobsScreen> createState() => _JobsScreenState();
}

class _JobsScreenState extends ConsumerState<JobsScreen> {
  JobStatusFilter _selectedStatus = JobStatusFilter.all;
  String? _selectedCategory;
  bool _isSearchOpen = false;
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _refreshAll() async {
    ref.invalidate(activeJobsProvider);
    ref.invalidate(completedJobsProvider);
    ref.invalidate(employeeProfileProvider);
    ref.invalidate(shiftStatusProvider);
    await Future.wait([
      ref.read(activeJobsProvider.future),
      ref.read(completedJobsProvider.future),
    ]);
  }

  bool _isJobOffer(Job job) {
    return (job.isOffer || job.activeOffer?.status == 'OFFERED') &&
        job.activeOffer?.status != 'EXPIRED' &&
        job.activeOffer?.status != 'SUPERSEDED_BY_ACCEPTANCE' &&
        !(job.activeOffer?.isExpired ?? false) &&
        !job.isAssignedToCurrentEmployee;
  }

  bool _isJobCompleted(Job job) {
    return job.status.toLowerCase() == 'completed';
  }

  bool _isJobCancelled(Job job) {
    return ['cancelled', 'rejected', 'declined'].contains(job.status.toLowerCase());
  }

  bool _isJobInProgress(Job job) {
    return !_isJobOffer(job) && !_isJobCompleted(job) && !_isJobCancelled(job);
  }

  @override
  Widget build(BuildContext context) {
    final activeAsync = ref.watch(activeJobsProvider);
    final completedAsync = ref.watch(completedJobsProvider);
    final hasActiveJob = ref.watch(hasActiveJobProvider);
    final unreadCount = ref.watch(unreadNotificationsCountProvider);

    final activeJobs = activeAsync.valueOrNull ?? const <Job>[];
    final completedJobs = completedAsync.valueOrNull ?? const <Job>[];

    // Combine active & completed with deduplication by ID
    final allJobsMap = <int, Job>{};
    for (final j in activeJobs) {
      allJobsMap[j.id] = j;
    }
    for (final j in completedJobs) {
      allJobsMap[j.id] = j;
    }
    final allJobs = allJobsMap.values.toList();

    // Compute counts across all known jobs
    int newOffersCount = 0;
    int inProgressCount = 0;
    int completedCount = 0;
    int cancelledCount = 0;

    final availableCategories = <String>{};

    for (final j in allJobs) {
      if (j.serviceCategory != null && j.serviceCategory!.trim().isNotEmpty) {
        availableCategories.add(j.serviceCategory!.trim());
      }
      if (_isJobOffer(j)) {
        newOffersCount++;
      } else if (_isJobCompleted(j)) {
        completedCount++;
      } else if (_isJobCancelled(j)) {
        cancelledCount++;
      } else {
        inProgressCount++;
      }
    }

    // Filter by Status
    List<Job> statusFilteredJobs = switch (_selectedStatus) {
      JobStatusFilter.all => allJobs,
      JobStatusFilter.newOffers => allJobs.where(_isJobOffer).toList(),
      JobStatusFilter.inProgress => allJobs.where(_isJobInProgress).toList(),
      JobStatusFilter.completed => allJobs.where(_isJobCompleted).toList(),
      JobStatusFilter.cancelled => allJobs.where(_isJobCancelled).toList(),
    };

    // Filter by Category
    if (_selectedCategory != null && _selectedCategory!.isNotEmpty) {
      final catQuery = _selectedCategory!.toLowerCase();
      statusFilteredJobs = statusFilteredJobs.where((j) {
        final cat = (j.serviceCategory ?? '').toLowerCase();
        final title = j.displayTitle.toLowerCase();
        return cat.contains(catQuery) || title.contains(catQuery);
      }).toList();
    }

    // Filter by Search query
    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      statusFilteredJobs = statusFilteredJobs.where((j) {
        return j.requestId.toLowerCase().contains(q) ||
            j.displayTitle.toLowerCase().contains(q) ||
            (j.customerName?.toLowerCase().contains(q) ?? false) ||
            (j.address?.toLowerCase().contains(q) ?? false) ||
            (j.serviceCategory?.toLowerCase().contains(q) ?? false);
      }).toList();
    }

    final isLoading = (activeAsync.isLoading || completedAsync.isLoading) && allJobs.isEmpty;
    final hasError = activeAsync.hasError && allJobs.isEmpty;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.peacockNavy,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: false,
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFF0A2540), // Deep Peacock Navy
                Color(0xFF004E89), // Peacock Blue
              ],
            ),
          ),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'My Orders & Jobs',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: Colors.white,
                letterSpacing: 0.2,
              ),
            ),
            if (allJobs.isNotEmpty) ...[
              const SizedBox(height: 1),
              Text(
                '${allJobs.length} ${allJobs.length == 1 ? 'Job' : 'Jobs'} Available & Assigned',
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: Color(0xFFBAE6FD),
                ),
              ),
            ],
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(
              _isSearchOpen ? Icons.search_off_rounded : Icons.search_rounded,
              color: Colors.white,
              size: 22,
            ),
            tooltip: _isSearchOpen ? 'Close Search' : 'Search Jobs',
            onPressed: () {
              setState(() {
                _isSearchOpen = !_isSearchOpen;
                if (!_isSearchOpen) {
                  _searchController.clear();
                  _searchQuery = '';
                }
              });
            },
          ),
          IconButton(
            icon: unreadCount > 0
                ? Badge(
                    label: Text(
                      unreadCount > 99 ? '99+' : '$unreadCount',
                      style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold),
                    ),
                    backgroundColor: const Color(0xFFEF4444),
                    child: const Icon(Icons.notifications_outlined, size: 22, color: Colors.white),
                  )
                : const Icon(Icons.notifications_outlined, size: 22, color: Colors.white),
            tooltip: 'Notifications',
            onPressed: () => context.push(AppRoutes.notifications),
          ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 22),
            tooltip: 'Refresh Jobs',
            onPressed: _refreshAll,
          ),
          const SizedBox(width: AppSpacing.xs),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _refreshAll,
          color: AppColors.peacockBlue,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.md,
              AppSpacing.md,
              AppSpacing.md,
              AppSpacing.xxl + 24,
            ),
            children: [
              // ── Optional Search Bar ─────────────────────────────────────────
              if (_isSearchOpen) ...[
                Container(
                  margin: const EdgeInsets.only(bottom: AppSpacing.md),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(AppRadius.chip),
                    border: Border.all(color: AppColors.peacockBlue, width: 1.2),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x0E004E89),
                        blurRadius: 6,
                        offset: Offset(0, 2),
                      ),
                    ],
                  ),
                  child: TextField(
                    controller: _searchController,
                    autofocus: true,
                    decoration: InputDecoration(
                      hintText: 'Search by Job ID, title, customer, or address...',
                      hintStyle: TextStyle(fontSize: 12.5, color: AppColors.textMuted),
                      prefixIcon: const Icon(Icons.search_rounded, size: 20, color: AppColors.peacockBlue),
                      suffixIcon: _searchQuery.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear_rounded, size: 18),
                              onPressed: () {
                                _searchController.clear();
                                setState(() => _searchQuery = '');
                              },
                            )
                          : null,
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                      isDense: true,
                    ),
                    onChanged: (val) => setState(() => _searchQuery = val.trim()),
                  ),
                ),
              ],

              // ── New Service Offer Alert Banner ──────────────────────────────
              if (newOffersCount > 0)
                NewOfferBanner(
                  offerCount: newOffersCount,
                  onTap: () {
                    setState(() => _selectedStatus = JobStatusFilter.newOffers);
                  },
                ),

              // ── Status Filters (Horizontally scrollable) ────────────────────
              JobStatusFilterBar(
                selectedFilter: _selectedStatus,
                allCount: allJobs.length,
                newOffersCount: newOffersCount,
                inProgressCount: inProgressCount,
                completedCount: completedCount,
                cancelledCount: cancelledCount,
                onFilterSelected: (filter) {
                  setState(() => _selectedStatus = filter);
                  if (filter == JobStatusFilter.completed) {
                    ref.read(completedJobsProvider.future);
                  }
                },
              ),
              const SizedBox(height: AppSpacing.sm),

              // ── Category Filters (Horizontally scrollable) ──────────────────
              JobCategoryFilterBar(
                selectedCategory: _selectedCategory,
                availableCategories: availableCategories.toList(),
                onCategorySelected: (cat) => setState(() => _selectedCategory = cat),
              ),
              const SizedBox(height: AppSpacing.md),

              // ── Main Content Area ───────────────────────────────────────────
              if (isLoading) ...[
                const JobCardSkeleton(),
                const JobCardSkeleton(),
                const JobCardSkeleton(),
              ] else if (hasError) ...[
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: AppSpacing.xxl),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.error_outline_rounded,
                          size: 44,
                          color: Color(0xFFDC2626),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        const Text(
                          'Unable to load workforce jobs',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF0F172A),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Please check your network connection and try again.',
                          style: TextStyle(
                            fontSize: 12.5,
                            color: AppColors.textSecondary,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: AppSpacing.lg),
                        ElevatedButton.icon(
                          onPressed: _refreshAll,
                          icon: const Icon(Icons.refresh_rounded, size: 16),
                          label: const Text('Retry'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.peacockNavy,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ] else if (statusFilteredJobs.isEmpty) ...[
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: AppSpacing.xl),
                  child: EmptyState(
                    icon: _emptyIconForFilter(_selectedStatus),
                    title: _emptyTitleForFilter(_selectedStatus, isFiltering: _selectedCategory != null || _searchQuery.isNotEmpty),
                    message: _emptyMessageForFilter(_selectedStatus),
                  ),
                ),
                if (_selectedCategory != null || _searchQuery.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Center(
                    child: OutlinedButton.icon(
                      onPressed: () {
                        setState(() {
                          _selectedCategory = null;
                          _searchController.clear();
                          _searchQuery = '';
                        });
                      },
                      icon: const Icon(Icons.filter_alt_off_outlined, size: 15),
                      label: const Text('Clear Filters & Search'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.peacockBlue,
                        side: const BorderSide(color: AppColors.peacockBlue),
                      ),
                    ),
                  ),
                ],
              ] else ...[
                for (final job in statusFilteredJobs)
                  JobCard(
                    job: job,
                    hasActiveJob: hasActiveJob,
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  IconData _emptyIconForFilter(JobStatusFilter filter) {
    return switch (filter) {
      JobStatusFilter.all => Icons.work_off_outlined,
      JobStatusFilter.newOffers => Icons.bolt_outlined,
      JobStatusFilter.inProgress => Icons.play_disabled_outlined,
      JobStatusFilter.completed => Icons.task_alt_outlined,
      JobStatusFilter.cancelled => Icons.cancel_outlined,
    };
  }

  String _emptyTitleForFilter(JobStatusFilter filter, {bool isFiltering = false}) {
    if (isFiltering) {
      return 'No matching jobs found';
    }
    return switch (filter) {
      JobStatusFilter.all => 'No jobs found',
      JobStatusFilter.newOffers => 'No new offers available',
      JobStatusFilter.inProgress => 'No jobs in progress',
      JobStatusFilter.completed => 'No completed jobs yet',
      JobStatusFilter.cancelled => 'No cancelled jobs',
    };
  }

  String _emptyMessageForFilter(JobStatusFilter filter) {
    return switch (filter) {
      JobStatusFilter.all =>
        'New service opportunities and assigned jobs will appear here automatically.',
      JobStatusFilter.newOffers =>
        'When new exclusive job dispatches become available, you will receive an instant alert here.',
      JobStatusFilter.inProgress =>
        'Jobs that you accept and are actively working on will appear in this section.',
      JobStatusFilter.completed =>
        'Jobs you finish and confirm payment for will be recorded here.',
      JobStatusFilter.cancelled =>
        'Cancelled or declined service assignments will appear here.',
    };
  }
}
