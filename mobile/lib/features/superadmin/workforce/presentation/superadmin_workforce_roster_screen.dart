import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../routing/app_routes.dart';
import '../../../../shared/widgets/async_value_view.dart';
import '../../../../shared/widgets/workforce_app_bar.dart';
import '../../../admin/presentation/widgets/admin_drawer.dart';
import '../data/superadmin_workforce_repository.dart';
import '../domain/platform_relieving_request.dart';
import '../domain/platform_worker.dart';
import 'superadmin_workforce_providers.dart';
import 'widgets/approve_relieving_bottom_sheet.dart';
import 'widgets/relieving_audit_card.dart';
import 'widgets/tie_vendor_bottom_sheet.dart';
import 'widgets/worker_card.dart';
import 'widgets/workforce_summary_metrics.dart';

/// Super Admin Platform Governance: Workforce Roster (Manage All Workforce - Solo & Tied).
class SuperAdminWorkforceRosterScreen extends ConsumerStatefulWidget {
  const SuperAdminWorkforceRosterScreen({
    super.key,
    this.initialVendorId,
  });

  final int? initialVendorId;

  @override
  ConsumerState<SuperAdminWorkforceRosterScreen> createState() =>
      _SuperAdminWorkforceRosterScreenState();
}

class _SuperAdminWorkforceRosterScreenState
    extends ConsumerState<SuperAdminWorkforceRosterScreen> {
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _applyInitialFilters();
    });
  }

  @override
  void didUpdateWidget(covariant SuperAdminWorkforceRosterScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialVendorId != widget.initialVendorId) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _applyInitialFilters();
      });
    }
  }

  void _applyInitialFilters() {
    if (widget.initialVendorId != null && widget.initialVendorId! > 0) {
      ref.read(workforceSelectedVendorIdProvider.notifier).state =
          widget.initialVendorId;
      ref.read(workforceFilterTypeProvider.notifier).state =
          WorkforceFilterType.all;
    } else {
      // General workforce entry: ensure no vendor filter is applied and All Workforce is selected
      ref.read(workforceSelectedVendorIdProvider.notifier).state = null;
      ref.read(workforceFilterTypeProvider.notifier).state =
          WorkforceFilterType.all;
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    setState(() {});
    ref.read(workforceSearchQueryProvider.notifier).state = query.trim();
  }

  void _openTieModal(PlatformWorker worker, List<PlatformVendorSummary> vendors) {
    showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => TieVendorBottomSheet(
        worker: worker,
        vendors: vendors,
      ),
    );
  }

  void _openAuditModal(PlatformRelievingRequest request) {
    showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => ApproveRelievingBottomSheet(request: request),
    );
  }

  @override
  Widget build(BuildContext context) {
    final selectedFilter = ref.watch(workforceFilterTypeProvider);
    final selectedVendorId = ref.watch(workforceSelectedVendorIdProvider);
    final workforceAsync = ref.watch(platformWorkforceDataProvider);

    return Scaffold(
      appBar: const WorkforceAppBar(
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(platformWorkforceDataProvider);
          await ref.read(platformWorkforceDataProvider.future);
        },
        child: AsyncValueView<PlatformWorkforceOverviewData>(
          value: workforceAsync,
          errorMessage: 'Unable to load platform workforce roster',
          onRetry: () => ref.invalidate(platformWorkforceDataProvider),
          builder: (context, data) {
            final isAuditsTab =
                selectedFilter == WorkforceFilterType.relievingAudits;

            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.md,
                AppSpacing.md,
                AppSpacing.md,
                AppSpacing.xxl,
              ),
              children: [
                // ── 1. Header ───────────────────────────────────────────────
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 6,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF004E89)
                                      .withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(
                                    color: const Color(0xFF004E89)
                                        .withValues(alpha: 0.25),
                                  ),
                                ),
                                child: const Text(
                                  'PLATFORM GOVERNANCE',
                                  style: TextStyle(
                                    fontSize: 9,
                                    fontWeight: FontWeight.w900,
                                    color: Color(0xFF004E89),
                                    letterSpacing: 0.6,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          const Text(
                            'Workforce Oversight (Solo & Tied Workers)',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w900,
                              color: Color(0xFF0F172A),
                              letterSpacing: -0.4,
                            ),
                          ),
                          const SizedBox(height: 2),
                          const Text(
                            'SEVO Platform Admin: Manage all technicians, directly tie solo workers to any vendor, audit resignations, and relieve workers.',
                            style: TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.w400,
                              color: Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh_rounded, size: 20),
                      color: const Color(0xFF004E89),
                      tooltip: 'Refresh Roster',
                      onPressed: () =>
                          ref.invalidate(platformWorkforceDataProvider),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // ── Action: Manage Vendor Companies ─────────────────────────
                Material(
                  color: const Color(0xFFEFF6FF),
                  borderRadius: BorderRadius.circular(AppRadius.card),
                  child: InkWell(
                    onTap: () => context.go(AppRoutes.superAdminVendors),
                    borderRadius: BorderRadius.circular(AppRadius.card),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.md,
                        vertical: 10,
                      ),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(AppRadius.card),
                        border: Border.all(color: const Color(0xFFBFDBFE)),
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(6),
                            decoration: const BoxDecoration(
                              color: Color(0xFFDBEAFE),
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.business_rounded,
                              color: Color(0xFF1D4ED8),
                              size: 18,
                            ),
                          ),
                          const SizedBox(width: 10),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Manage Vendor Companies',
                                  style: TextStyle(
                                    color: Color(0xFF1E3A8A),
                                    fontSize: 13,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                                SizedBox(height: 1),
                                Text(
                                  'View registered vendor directory and provider fleet sizes',
                                  style: TextStyle(
                                    color: Color(0xFF3B82F6),
                                    fontSize: 10.5,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Icon(
                            Icons.arrow_forward_ios_rounded,
                            color: Color(0xFF1D4ED8),
                            size: 13,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 14),

                // ── 2. Live Summary Metrics ─────────────────────────────────
                WorkforceSummaryMetrics(
                  data: data,
                  selectedFilter: selectedFilter,
                  onSelectFilter: (filter) {
                    ref.read(workforceFilterTypeProvider.notifier).state =
                        filter;
                  },
                ),
                const SizedBox(height: 16),

                // ── 3. Filter Tabs with Live Badges ─────────────────────────
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _FilterTab(
                        label: 'All Workforce',
                        count: data.totalTechnicians,
                        isSelected: selectedFilter == WorkforceFilterType.all,
                        activeColor: const Color(0xFF004E89),
                        onTap: () => ref
                            .read(workforceFilterTypeProvider.notifier)
                            .state = WorkforceFilterType.all,
                      ),
                      const SizedBox(width: 6),
                      _FilterTab(
                        label: 'Solo Workers',
                        count: data.soloWorkersCount,
                        isSelected: selectedFilter == WorkforceFilterType.solo,
                        activeColor: const Color(0xFF2563EB),
                        onTap: () => ref
                            .read(workforceFilterTypeProvider.notifier)
                            .state = WorkforceFilterType.solo,
                      ),
                      const SizedBox(width: 6),
                      _FilterTab(
                        label: 'Tied Workers',
                        count: data.tiedWorkersCount,
                        isSelected: selectedFilter == WorkforceFilterType.tied,
                        activeColor: const Color(0xFF059669),
                        onTap: () => ref
                            .read(workforceFilterTypeProvider.notifier)
                            .state = WorkforceFilterType.tied,
                      ),
                      const SizedBox(width: 6),
                      _FilterTab(
                        label: 'Resignation Audits',
                        count: data.pendingSevoAuditCount,
                        isSelected: selectedFilter ==
                            WorkforceFilterType.relievingAudits,
                        activeColor: const Color(0xFF7C3AED),
                        hasAlert: data.pendingSevoAuditCount > 0,
                        onTap: () => ref
                            .read(workforceFilterTypeProvider.notifier)
                            .state = WorkforceFilterType.relievingAudits,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // ── 4. Search & Vendor Filter Controls ───────────────────────
                if (!isAuditsTab) ...[
                  // Search Bar
                  Container(
                    height: 40,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Row(
                      children: [
                        const Padding(
                          padding: EdgeInsets.only(left: 10, right: 6),
                          child: Icon(
                            Icons.search_rounded,
                            size: 18,
                            color: Color(0xFF94A3B8),
                          ),
                        ),
                        Expanded(
                          child: TextField(
                            controller: _searchController,
                            style: const TextStyle(
                              fontSize: 12.5,
                              color: Color(0xFF0F172A),
                            ),
                            decoration: const InputDecoration(
                              hintText:
                                  'Search by name, ID (EMP-...), email, phone...',
                              hintStyle: TextStyle(
                                fontSize: 12,
                                color: Color(0xFF94A3B8),
                              ),
                              border: InputBorder.none,
                              isDense: true,
                              contentPadding: EdgeInsets.zero,
                            ),
                            onChanged: _onSearchChanged,
                          ),
                        ),
                        if (_searchController.text.isNotEmpty)
                          IconButton(
                            icon: const Icon(Icons.clear_rounded, size: 16),
                            color: const Color(0xFF94A3B8),
                            onPressed: () {
                              _searchController.clear();
                              _onSearchChanged('');
                            },
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),

                  // Vendor Filter Dropdown
                  if (data.vendors.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<int?>(
                          value: selectedVendorId,
                          isExpanded: true,
                          icon: const Icon(
                            Icons.arrow_drop_down_rounded,
                            color: Color(0xFF64748B),
                          ),
                          hint: const Row(
                            children: [
                              Icon(
                                Icons.business_outlined,
                                size: 14,
                                color: Color(0xFF64748B),
                              ),
                              SizedBox(width: 6),
                              Text(
                                'Filter by Vendor (All Vendors)',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF64748B),
                                ),
                              ),
                            ],
                          ),
                          items: [
                            const DropdownMenuItem<int?>(
                              value: null,
                              child: Text(
                                'All Vendors',
                                style: TextStyle(fontSize: 12),
                              ),
                            ),
                            ...data.vendors.map(
                              (v) => DropdownMenuItem<int?>(
                                value: v.id,
                                child: Text(
                                  '${v.companyName} (${v.tiedWorkersCount} tied)',
                                  style: const TextStyle(fontSize: 12),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ),
                          ],
                          onChanged: (val) {
                            ref
                                .read(workforceSelectedVendorIdProvider.notifier)
                                .state = val;
                          },
                        ),
                      ),
                    ),
                  const SizedBox(height: 14),
                ],

                // ── 5. Main Roster Content List ─────────────────────────────
                if (isAuditsTab) ...[
                  // Relieving & Resignation Audits List
                  if (data.relievingRequests.isEmpty)
                    _EmptyRosterView(
                      icon: Icons.check_circle_outline_rounded,
                      title: 'No Pending Relieving Audits',
                      subtitle:
                          'All technician resignations and vendor clearances have been audited and resolved.',
                      iconColor: const Color(0xFF059669),
                    )
                  else
                    ...data.relievingRequests.map(
                      (req) => RelievingAuditCard(
                        request: req,
                        onAudit: () => _openAuditModal(req),
                      ),
                    ),
                ] else ...[
                  // Personnel Workers List
                  if (data.workers.isEmpty)
                    _EmptyRosterView(
                      icon: Icons.people_outline_rounded,
                      title: 'No technicians found',
                      subtitle:
                          'No workers match your selected filter or search criteria.',
                      iconColor: const Color(0xFF94A3B8),
                    )
                  else
                    ...data.workers.map(
                      (worker) => WorkerCard(
                        worker: worker,
                        onManageTie: () => _openTieModal(worker, data.vendors),
                      ),
                    ),
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}

class _FilterTab extends StatelessWidget {
  const _FilterTab({
    required this.label,
    required this.count,
    required this.isSelected,
    required this.activeColor,
    this.hasAlert = false,
    required this.onTap,
  });

  final String label;
  final int count;
  final bool isSelected;
  final Color activeColor;
  final bool hasAlert;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: isSelected ? activeColor : Colors.white,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6.5),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isSelected ? activeColor : const Color(0xFFCBD5E1),
              width: isSelected ? 1.2 : 1.0,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                  color: isSelected ? Colors.white : const Color(0xFF334155),
                ),
              ),
              const SizedBox(width: 5),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                decoration: BoxDecoration(
                  color: isSelected
                      ? Colors.white.withValues(alpha: 0.25)
                      : (hasAlert
                          ? const Color(0xFFFEE2E2)
                          : const Color(0xFFF1F5F9)),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '$count',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: isSelected
                        ? Colors.white
                        : (hasAlert
                            ? const Color(0xFFDC2626)
                            : const Color(0xFF475569)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyRosterView extends StatelessWidget {
  const _EmptyRosterView({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.iconColor,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color iconColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.xxl,
      ),
      margin: const EdgeInsets.only(top: AppSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 40, color: iconColor),
          const SizedBox(height: 12),
          Text(
            title,
            style: const TextStyle(
              fontSize: 14.5,
              fontWeight: FontWeight.w800,
              color: Color(0xFF0F172A),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: const TextStyle(
              fontSize: 12,
              color: Color(0xFF64748B),
              height: 1.3,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
