import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/async_value_view.dart';
import '../../../shared/widgets/empty_state.dart';
import '../../../shared/widgets/status_chip.dart';
import '../../jobs/presentation/widgets/category_helper.dart';
import '../../profile/domain/employee_profile.dart';
import '../../profile/presentation/profile_providers.dart';
import '../domain/service_catalog.dart';
import 'services_providers.dart';

class ServicesScreen extends ConsumerStatefulWidget {
  const ServicesScreen({super.key});

  @override
  ConsumerState<ServicesScreen> createState() => _ServicesScreenState();
}

class _ServicesScreenState extends ConsumerState<ServicesScreen> {
  final Set<dynamic> _selectedServiceIds = {};

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(employeeProfileProvider);
    final catalogAsync = ref.watch(serviceCatalogProvider);
    final skillsAsync = ref.watch(employeeSkillsProvider);
    final actionState = ref.watch(servicesControllerProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.peacockNavy,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: false,
        leading: Navigator.of(context).canPop()
            ? IconButton(
                icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
                tooltip: 'Back',
                onPressed: () => Navigator.of(context).pop(),
              )
            : null,
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: AppColors.peacockGradient,
          ),
        ),
        title: const Text(
          'Services & Skills',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w800,
            color: Colors.white,
            letterSpacing: 0.2,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 22),
            tooltip: 'Refresh Services',
            onPressed: () {
              ref.invalidate(employeeProfileProvider);
              ref.invalidate(serviceCatalogProvider);
              ref.invalidate(employeeSkillsProvider);
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(employeeProfileProvider);
          ref.invalidate(serviceCatalogProvider);
          ref.invalidate(employeeSkillsProvider);
          await ref.read(employeeProfileProvider.future);
        },
        child: AsyncValueView<EmployeeProfile>(
          value: profileAsync,
          onRetry: () {
            ref.invalidate(employeeProfileProvider);
            ref.invalidate(serviceCatalogProvider);
            ref.invalidate(employeeSkillsProvider);
          },
          builder: (context, profile) {
            final approvedServices = profile.approvedServices;
            final allRequestedServices = profile.allRequestedServices;
            final pendingServices = allRequestedServices.where((s) => s.status.toLowerCase() == 'pending').toList();
            final rejectedServices = allRequestedServices.where((s) => s.status.toLowerCase() == 'rejected').toList();

            final categories = catalogAsync.value ?? const <CatalogCategory>[];

            // Map each approved service to its category
            final Map<String, List<ApprovedService>> categorizedApproved = _groupApprovedServicesByCategory(
              approvedServices,
              allRequestedServices,
              categories,
            );

            return ListView(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.lg,
                AppSpacing.lg,
                AppSpacing.lg,
                AppSpacing.xxl,
              ),
              children: [
                // Header & Subtitle
                const Text(
                  'Services & Skills',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0F172A),
                    letterSpacing: -0.3,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Manage your authorized trade services, skills portfolio, and request new service categories',
                  style: TextStyle(
                    fontSize: 12.5,
                    color: Color(0xFF64748B),
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: AppSpacing.md),

                // Top Action: Request New Service
                SizedBox(
                  width: double.infinity,
                  height: 46,
                  child: ElevatedButton.icon(
                    onPressed: () => _openRequestNewServiceSheet(categories, allRequestedServices),
                    icon: const Icon(Icons.add_business_rounded, size: 18),
                    label: const Text(
                      'Request New Service',
                      style: TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.2,
                      ),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.peacockBlue,
                      foregroundColor: Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),

                // Active Trade Qualifications Summary Card
                _ActiveTradeQualificationsCard(
                  totalServicesCount: approvedServices.length,
                  categoryCount: categorizedApproved.keys.length,
                ),
                const SizedBox(height: AppSpacing.lg),

                // Approved Services Grouped by Category
                if (approvedServices.isEmpty)
                  Card(
                    color: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: const BorderSide(color: Color(0xFFE2E8F0)),
                    ),
                    child: const Padding(
                      padding: EdgeInsets.all(AppSpacing.xl),
                      child: EmptyState(
                        icon: Icons.handyman_outlined,
                        title: 'No services authorized yet',
                        message: 'Tap "Request New Service" above to browse the catalog and request operational authorization.',
                        compact: true,
                      ),
                    ),
                  )
                else
                  ...categorizedApproved.entries.map((entry) {
                    final categoryName = entry.key;
                    final svcs = entry.value;

                    return _CategoryServiceSection(
                      categoryName: categoryName,
                      services: svcs,
                      isLoading: actionState.isLoading,
                      onRemove: (serviceId, name) => _confirmRemoveService(serviceId, name),
                    );
                  }),

                // Pending Admin Review Section
                if (pendingServices.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.lg),
                  _PendingServicesCard(pendingServices: pendingServices),
                ],

                // Rejected Service Requests Section
                if (rejectedServices.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.lg),
                  _RejectedServicesCard(
                    rejectedServices: rejectedServices,
                    isLoading: actionState.isLoading,
                    onReapply: (serviceId, name) => _handleRequestService(serviceId, name),
                  ),
                ],

                // Available Catalog Section
                const SizedBox(height: AppSpacing.lg),
                AsyncValueView<List<CatalogCategory>>(
                  value: catalogAsync,
                  onRetry: () => ref.invalidate(serviceCatalogProvider),
                  builder: (context, categoriesList) {
                    return _AvailableCatalogSection(
                      categories: categoriesList,
                      allRequestedServices: allRequestedServices,
                      selectedServiceIds: _selectedServiceIds,
                      isLoading: actionState.isLoading,
                      onToggleSelect: (id) {
                        setState(() {
                          if (_selectedServiceIds.contains(id)) {
                            _selectedServiceIds.remove(id);
                          } else {
                            _selectedServiceIds.add(id);
                          }
                        });
                      },
                      onToggleCategory: (categoryRequestableIds) {
                        setState(() {
                          final allInCatSelected = categoryRequestableIds.isNotEmpty &&
                              categoryRequestableIds.every(_selectedServiceIds.contains);
                          if (allInCatSelected) {
                            _selectedServiceIds.removeAll(categoryRequestableIds);
                          } else {
                            _selectedServiceIds.addAll(categoryRequestableIds);
                          }
                        });
                      },
                      onToggleAll: (allRequestableIds) {
                        setState(() {
                          final allSelected = allRequestableIds.isNotEmpty &&
                              allRequestableIds.every(_selectedServiceIds.contains);
                          if (allSelected) {
                            _selectedServiceIds.removeAll(allRequestableIds);
                          } else {
                            _selectedServiceIds.addAll(allRequestableIds);
                          }
                        });
                      },
                      onRequestService: (id, name) => _handleRequestService(id, name),
                      onBulkRequest: () => _handleBulkRequest(),
                      onClearSelection: () => setState(() => _selectedServiceIds.clear()),
                    );
                  },
                ),

                // Verified Skills Section
                const SizedBox(height: AppSpacing.lg),
                AsyncValueView<List<EmployeeSkill>>(
                  value: skillsAsync,
                  onRetry: () => ref.invalidate(employeeSkillsProvider),
                  builder: (context, skills) {
                    return _VerifiedSkillsSection(skills: skills);
                  },
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Map<String, List<ApprovedService>> _groupApprovedServicesByCategory(
    List<ApprovedService> approved,
    List<RequestedService> allRequested,
    List<CatalogCategory> catalog,
  ) {
    final Map<String, List<ApprovedService>> grouped = {};

    // Build quick lookup from catalog
    final Map<String, String> serviceToCategory = {};
    for (final cat in catalog) {
      for (final svc in cat.services) {
        serviceToCategory[svc.id.toString()] = cat.name;
        serviceToCategory[svc.name.trim().toLowerCase()] = cat.name;
      }
    }

    // Build lookup from allRequestedServices
    for (final req in allRequested) {
      if (req.categoryName != null && req.categoryName!.isNotEmpty) {
        serviceToCategory[req.id.toString()] = req.categoryName!;
        serviceToCategory[req.name.trim().toLowerCase()] = req.categoryName!;
      }
    }

    for (final svc in approved) {
      final cat = serviceToCategory[svc.id.toString()] ??
          serviceToCategory[svc.name.trim().toLowerCase()] ??
          'General';

      grouped.putIfAbsent(cat, () => []).add(svc);
    }

    return grouped;
  }

  Future<void> _openRequestNewServiceSheet([
    List<CatalogCategory>? categories,
    List<RequestedService>? allRequestedServices,
  ]) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => RequestNewServicesModal(
        categories: categories,
        allRequestedServices: allRequestedServices,
        onRequestSingle: (id, name) async {
          Navigator.of(ctx).pop();
          await _handleRequestService(id, name);
        },
        onRequestBulk: (ids) async {
          Navigator.of(ctx).pop();
          _selectedServiceIds.addAll(ids);
          await _handleBulkRequest();
        },
      ),
    );
  }

  Future<void> _handleRequestService(dynamic serviceId, String name) async {
    final success = await ref
        .read(servicesControllerProvider.notifier)
        .requestService(serviceId: serviceId, name: name);

    if (!mounted) return;

    if (success) {
      setState(() => _selectedServiceIds.remove(serviceId));
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Service authorization request for "$name" submitted for Admin review.'),
          backgroundColor: const Color(0xFF10B981),
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to submit service authorization request.'),
          backgroundColor: Color(0xFFEF4444),
        ),
      );
    }
  }

  Future<void> _handleBulkRequest() async {
    final ids = _selectedServiceIds.toList();
    if (ids.isEmpty) return;

    final success = await ref
        .read(servicesControllerProvider.notifier)
        .bulkRequestServices(ids);

    if (!mounted) return;

    if (success) {
      final count = ids.length;
      setState(() => _selectedServiceIds.clear());
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Authorization requests for $count service(s) submitted for Admin review.'),
          backgroundColor: const Color(0xFF10B981),
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to submit bulk authorization requests.'),
          backgroundColor: Color(0xFFEF4444),
        ),
      );
    }
  }

  Future<void> _confirmRemoveService(dynamic serviceId, String name) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text(
          'Remove Service?',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
        ),
        content: const Text(
          'Are you sure you want to remove this service from your authorized skills?',
          style: TextStyle(fontSize: 13, color: Color(0xFF475569)),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFFDC2626),
            ),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    final success = await ref
        .read(servicesControllerProvider.notifier)
        .removeService(serviceId);

    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Service removed successfully'),
          backgroundColor: Color(0xFF10B981),
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to remove service.'),
          backgroundColor: Color(0xFFEF4444),
        ),
      );
    }
  }
}

// ── Active Trade Qualifications Summary Card ─────────────────────────────────

class _ActiveTradeQualificationsCard extends StatelessWidget {
  const _ActiveTradeQualificationsCard({
    required this.totalServicesCount,
    required this.categoryCount,
  });

  final int totalServicesCount;
  final int categoryCount;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFE0F2FE),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.workspace_premium_outlined,
                    size: 22,
                    color: AppColors.peacockBlue,
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Active Trade Qualifications',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'You are currently authorized to accept customer service requests for ${categoryCount > 0 ? '$categoryCount trades' : 'your authorized trades'}.',
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFF64748B),
                          height: 1.3,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.md,
                vertical: 10,
              ),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Total Services',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF334155),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFECFDF5),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFFA7F3D0)),
                    ),
                    child: Text(
                      '$totalServicesCount',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF059669),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Category Service Group & Cards ───────────────────────────────────────────

class _CategoryServiceSection extends StatelessWidget {
  const _CategoryServiceSection({
    required this.categoryName,
    required this.services,
    required this.isLoading,
    required this.onRemove,
  });

  final String categoryName;
  final List<ApprovedService> services;
  final bool isLoading;
  final void Function(dynamic serviceId, String name) onRemove;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: AppSpacing.sm, bottom: AppSpacing.xs),
          child: Row(
            children: [
              const Icon(
                Icons.build_circle_outlined,
                size: 15,
                color: AppColors.peacockBlue,
              ),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  categoryName,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0F172A),
                  ),
                ),
              ),
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  '${services.length}',
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF64748B),
                  ),
                ),
              ),
            ],
          ),
        ),
        ...services.map((svc) => _ServiceCard(
              categoryName: categoryName,
              service: svc,
              isLoading: isLoading,
              onRemove: () => onRemove(svc.id, svc.name),
            )),
        const SizedBox(height: AppSpacing.sm),
      ],
    );
  }
}

class _ServiceCard extends StatelessWidget {
  const _ServiceCard({
    required this.categoryName,
    required this.service,
    required this.isLoading,
    required this.onRemove,
  });

  final String categoryName;
  final ApprovedService service;
  final bool isLoading;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Row: Category tag + Approved badge
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Flexible(
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.handyman_outlined,
                        size: 13,
                        color: AppColors.peacockBlue,
                      ),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          categoryName,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: AppColors.peacockBlue,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFFECFDF5),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFA7F3D0)),
                  ),
                  child: const Text(
                    'Approved',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF059669),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Main Content: Service Name
            Text(
              service.name,
              style: const TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
                color: Color(0xFF0F172A),
                height: 1.25,
              ),
            ),
            const SizedBox(height: 10),

            // Bottom Row: Eligible for Dispatch + Delete/Remove button
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Flexible(
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.check_circle_outline_rounded,
                        size: 14,
                        color: Color(0xFF059669),
                      ),
                      SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          '✓ Eligible for Dispatch',
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF059669),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(
                    Icons.delete_outline_rounded,
                    size: 18,
                    color: Color(0xFFDC2626),
                  ),
                  tooltip: 'Remove',
                  constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                  padding: EdgeInsets.zero,
                  onPressed: isLoading ? null : onRemove,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ── Pending Admin Review Card ─────────────────────────────────────────────────

class _PendingServicesCard extends StatelessWidget {
  const _PendingServicesCard({required this.pendingServices});

  final List<RequestedService> pendingServices;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFFDE68A)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
            decoration: const BoxDecoration(
              color: Color(0xFFFFFBEB),
              border: Border(bottom: BorderSide(color: Color(0xFFFDE68A))),
            ),
            child: Row(
              children: [
                const Icon(Icons.hourglass_top_rounded, size: 15, color: Color(0xFFD97706)),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    'PENDING ADMIN REVIEW (${pendingServices.length})',
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF92400E),
                    ),
                  ),
                ),
              ],
            ),
          ),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: pendingServices.length,
            separatorBuilder: (context, index) => Divider(height: 1, color: AppColors.border),
            itemBuilder: (context, index) {
              final svc = pendingServices[index];
              final isRemoval = svc.requestType == 'remove';

              return Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            svc.name,
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            isRemoval ? 'REMOVAL PENDING REVIEW' : 'AUTHORIZATION PENDING REVIEW',
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFFB45309),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const StatusChip(status: 'pending', dense: true),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

// ── Rejected Service Requests Card ────────────────────────────────────────────

class _RejectedServicesCard extends StatelessWidget {
  const _RejectedServicesCard({
    required this.rejectedServices,
    required this.isLoading,
    required this.onReapply,
  });

  final List<RequestedService> rejectedServices;
  final bool isLoading;
  final void Function(dynamic serviceId, String name) onReapply;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFFECACA)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
            decoration: const BoxDecoration(
              color: Color(0xFFFEF2F2),
              border: Border(bottom: BorderSide(color: Color(0xFFFECACA))),
            ),
            child: Row(
              children: [
                const Icon(Icons.error_outline_rounded, size: 15, color: Color(0xFFDC2626)),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    'REJECTED SERVICE REQUESTS (${rejectedServices.length})',
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF991B1B),
                    ),
                  ),
                ),
              ],
            ),
          ),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: rejectedServices.length,
            separatorBuilder: (context, index) => Divider(height: 1, color: AppColors.border),
            itemBuilder: (context, index) {
              final svc = rejectedServices[index];

              return Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            svc.name,
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                          ),
                        ),
                        const StatusChip(status: 'rejected', dense: true),
                      ],
                    ),
                    if (svc.rejectionReason != null && svc.rejectionReason!.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        'Reason: ${svc.rejectionReason}',
                        style: const TextStyle(fontSize: 11, color: Color(0xFFB91C1C)),
                      ),
                    ],
                    const SizedBox(height: 6),
                    TextButton(
                      onPressed: isLoading ? null : () => onReapply(svc.id, svc.name),
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        visualDensity: VisualDensity.compact,
                      ),
                      child: const Text('Re-apply for Authorization', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

// ── Available Catalog Section ─────────────────────────────────────────────────

class _AvailableCatalogSection extends StatelessWidget {
  const _AvailableCatalogSection({
    required this.categories,
    required this.allRequestedServices,
    required this.selectedServiceIds,
    required this.isLoading,
    required this.onToggleSelect,
    required this.onToggleCategory,
    required this.onToggleAll,
    required this.onRequestService,
    required this.onBulkRequest,
    required this.onClearSelection,
  });

  final List<CatalogCategory> categories;
  final List<RequestedService> allRequestedServices;
  final Set<dynamic> selectedServiceIds;
  final bool isLoading;
  final void Function(dynamic id) onToggleSelect;
  final void Function(List<dynamic> categoryRequestableIds) onToggleCategory;
  final void Function(List<dynamic> allRequestableIds) onToggleAll;
  final void Function(dynamic id, String name) onRequestService;
  final VoidCallback onBulkRequest;
  final VoidCallback onClearSelection;

  bool _isServiceApproved(dynamic id) {
    return allRequestedServices.any((r) => r.id.toString() == id.toString() && r.status.toLowerCase() == 'approved');
  }

  bool _isServicePending(dynamic id) {
    return allRequestedServices.any((r) => r.id.toString() == id.toString() && r.status.toLowerCase() == 'pending');
  }

  bool _isRequestable(dynamic id) {
    return !_isServiceApproved(id) && !_isServicePending(id);
  }

  @override
  Widget build(BuildContext context) {
    final allRequestableServices = categories
        .expand((c) => c.services)
        .where((s) => _isRequestable(s.id))
        .toList();
    final allRequestableIds = allRequestableServices.map((s) => s.id).toList();

    final isAllSelected = allRequestableIds.isNotEmpty &&
        allRequestableIds.every(selectedServiceIds.contains);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Available Service Catalog',
          style: TextStyle(
            fontSize: 13.5,
            fontWeight: FontWeight.w800,
            color: Color(0xFF0F172A),
          ),
        ),
        const SizedBox(height: 2),
        Text(
          'Select the services you are qualified to deliver and request administrative authorization.',
          style: TextStyle(fontSize: 11, color: AppColors.textMuted),
        ),
        const SizedBox(height: AppSpacing.sm),

        // Global Select All and Bulk Bar
        if (allRequestableIds.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
            decoration: BoxDecoration(
              color: AppColors.background,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.border),
            ),
            child: Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.xs,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Checkbox(
                      value: isAllSelected,
                      onChanged: (val) => onToggleAll(allRequestableIds),
                      visualDensity: VisualDensity.compact,
                    ),
                    Flexible(
                      child: Text(
                        'Select All (${allRequestableIds.length})',
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
                if (selectedServiceIds.isNotEmpty)
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ElevatedButton(
                        onPressed: isLoading ? null : onBulkRequest,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.peacockBlue,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          visualDensity: VisualDensity.compact,
                          minimumSize: const Size(0, 32),
                        ),
                        child: Text(
                          'Request (${selectedServiceIds.length})',
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, size: 16),
                        tooltip: 'Clear selection',
                        onPressed: onClearSelection,
                      ),
                    ],
                  ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],

        // Category Groups
        for (final cat in categories) ...[
          _CatalogCategoryCard(
            category: cat,
            selectedServiceIds: selectedServiceIds,
            isLoading: isLoading,
            isApprovedCheck: _isServiceApproved,
            isPendingCheck: _isServicePending,
            isRequestableCheck: _isRequestable,
            onToggleSelect: onToggleSelect,
            onToggleCategory: onToggleCategory,
            onRequestService: onRequestService,
          ),
          const SizedBox(height: AppSpacing.md),
        ],
      ],
    );
  }
}

class _CatalogCategoryCard extends StatelessWidget {
  const _CatalogCategoryCard({
    required this.category,
    required this.selectedServiceIds,
    required this.isLoading,
    required this.isApprovedCheck,
    required this.isPendingCheck,
    required this.isRequestableCheck,
    required this.onToggleSelect,
    required this.onToggleCategory,
    required this.onRequestService,
  });

  final CatalogCategory category;
  final Set<dynamic> selectedServiceIds;
  final bool isLoading;
  final bool Function(dynamic id) isApprovedCheck;
  final bool Function(dynamic id) isPendingCheck;
  final bool Function(dynamic id) isRequestableCheck;
  final void Function(dynamic id) onToggleSelect;
  final void Function(List<dynamic> requestableIds) onToggleCategory;
  final void Function(dynamic id, String name) onRequestService;

  @override
  Widget build(BuildContext context) {
    final catRequestableServices = category.services.where((s) => isRequestableCheck(s.id)).toList();
    final catRequestableIds = catRequestableServices.map((s) => s.id).toList();

    final isCatAllSelected = catRequestableIds.isNotEmpty &&
        catRequestableIds.every(selectedServiceIds.contains);

    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
            decoration: BoxDecoration(
              color: AppColors.background,
              border: Border(bottom: BorderSide(color: AppColors.border)),
            ),
            child: Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.xs,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Flexible(
                      child: Text(
                        category.name,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.xs),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: AppColors.surface,
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Text(
                        '${category.services.length}',
                        style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: AppColors.textMuted),
                      ),
                    ),
                  ],
                ),
                if (catRequestableIds.isNotEmpty)
                  InkWell(
                    onTap: () => onToggleCategory(catRequestableIds),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Checkbox(
                          value: isCatAllSelected,
                          onChanged: (val) => onToggleCategory(catRequestableIds),
                          visualDensity: VisualDensity.compact,
                        ),
                        Text(
                          'Select All (${catRequestableIds.length})',
                          style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  )
                else
                  Text(
                    'All authorized',
                    style: TextStyle(fontSize: 10, fontStyle: FontStyle.italic, color: AppColors.textMuted),
                  ),
              ],
            ),
          ),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: category.services.length,
            separatorBuilder: (context, index) => Divider(height: 1, color: AppColors.border),
            itemBuilder: (context, index) {
              final s = category.services[index];
              final isApproved = isApprovedCheck(s.id);
              final isPending = isPendingCheck(s.id);
              final isRequestable = isRequestableCheck(s.id);
              final isChecked = selectedServiceIds.contains(s.id);

              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                child: Row(
                  children: [
                    if (isRequestable)
                      Checkbox(
                        value: isChecked,
                        onChanged: (val) => onToggleSelect(s.id),
                        visualDensity: VisualDensity.compact,
                      )
                    else
                      const SizedBox(width: 32),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            s.name,
                            style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold),
                          ),
                          Text(
                            'Approx. ${s.durationMinutes} mins',
                            style: TextStyle(fontSize: 10.5, fontFamily: 'monospace', color: AppColors.textMuted),
                          ),
                        ],
                      ),
                    ),
                    if (isApproved)
                      const StatusChip(status: 'approved', dense: true)
                    else if (isPending)
                      const StatusChip(status: 'pending', dense: true)
                    else
                      ElevatedButton(
                        onPressed: isLoading ? null : () => onRequestService(s.id, s.name),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.peacockBlue,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          visualDensity: VisualDensity.compact,
                          minimumSize: const Size(90, 30),
                        ),
                        child: const Text('Request', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                      ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

// ── Request New Service Modal Sheet ───────────────────────────────────────────

class RequestNewServicesModal extends ConsumerStatefulWidget {
  const RequestNewServicesModal({
    super.key,
    this.categories,
    this.allRequestedServices,
    this.initialCategories,
    this.initialRequestedServices,
    this.hasError = false,
    this.onRequestSingle,
    this.onRequestBulk,
  });

  final List<CatalogCategory>? categories;
  final List<RequestedService>? allRequestedServices;
  final List<CatalogCategory>? initialCategories;
  final List<RequestedService>? initialRequestedServices;
  final bool hasError;
  final void Function(dynamic id, String name)? onRequestSingle;
  final void Function(List<dynamic> ids)? onRequestBulk;

  @override
  ConsumerState<RequestNewServicesModal> createState() => _RequestNewServicesModalState();
}

class _RequestNewServicesModalState extends ConsumerState<RequestNewServicesModal> {
  final Set<dynamic> _selectedCategoryIds = {};
  String _searchQuery = '';
  bool _isSubmitting = false;

  bool _isCategoryApproved(CatalogCategory cat, List<RequestedService> allRequested) {
    if (cat.services.isNotEmpty) {
      return cat.services.every((s) => allRequested.any(
            (r) => r.id.toString() == s.id.toString() && r.status.toLowerCase() == 'approved',
          ));
    }
    return allRequested.any(
      (r) =>
          (r.id.toString() == cat.id.toString() ||
              r.name.toLowerCase() == cat.name.toLowerCase() ||
              r.categoryName?.toLowerCase() == cat.name.toLowerCase()) &&
          r.status.toLowerCase() == 'approved',
    );
  }

  bool _isCategoryPending(CatalogCategory cat, List<RequestedService> allRequested) {
    if (_isCategoryApproved(cat, allRequested)) return false;
    if (cat.services.isNotEmpty) {
      return cat.services.every((s) => allRequested.any(
            (r) =>
                r.id.toString() == s.id.toString() &&
                (r.status.toLowerCase() == 'pending' || r.status.toLowerCase() == 'approved'),
          ));
    }
    return allRequested.any(
      (r) =>
          (r.id.toString() == cat.id.toString() ||
              r.name.toLowerCase() == cat.name.toLowerCase() ||
              r.categoryName?.toLowerCase() == cat.name.toLowerCase()) &&
          r.status.toLowerCase() == 'pending',
    );
  }

  bool _isCategoryRequestable(CatalogCategory cat, List<RequestedService> allRequested) {
    return !_isCategoryApproved(cat, allRequested) && !_isCategoryPending(cat, allRequested);
  }

  void _toggleCategory(dynamic categoryId) {
    setState(() {
      if (_selectedCategoryIds.contains(categoryId)) {
        _selectedCategoryIds.remove(categoryId);
      } else {
        _selectedCategoryIds.add(categoryId);
      }
    });
  }

  Future<void> _handleSubmit(
    List<CatalogCategory> categories,
    List<RequestedService> allRequested,
  ) async {
    if (_selectedCategoryIds.isEmpty || _isSubmitting) return;

    final List<dynamic> idsToSubmit = [];
    for (final catId in _selectedCategoryIds) {
      final cat = categories.firstWhere(
        (c) => c.id.toString() == catId.toString(),
        orElse: () => CatalogCategory(id: catId, name: '', slug: '', services: const []),
      );
      if (cat.services.isNotEmpty) {
        final reqServices = cat.services.where((s) {
          return !allRequested.any((r) =>
              r.id.toString() == s.id.toString() &&
              (r.status.toLowerCase() == 'approved' || r.status.toLowerCase() == 'pending'));
        }).map((s) => s.id).toList();

        if (reqServices.isNotEmpty) {
          idsToSubmit.addAll(reqServices);
        } else {
          idsToSubmit.addAll(cat.services.map((s) => s.id));
        }
      } else {
        idsToSubmit.add(cat.id);
      }
    }

    if (idsToSubmit.isEmpty) {
      idsToSubmit.addAll(_selectedCategoryIds);
    }

    if (widget.onRequestBulk != null) {
      widget.onRequestBulk!(idsToSubmit);
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      final success = await ref
          .read(servicesControllerProvider.notifier)
          .bulkRequestServices(idsToSubmit);

      if (!mounted) return;

      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Service request submitted successfully'),
            backgroundColor: Color(0xFF059669),
            behavior: SnackBarBehavior.floating,
          ),
        );
        ref.invalidate(employeeProfileProvider);
        ref.invalidate(serviceCatalogProvider);
        Navigator.of(context).pop(true);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to submit service request. Please try again.'),
            backgroundColor: Color(0xFFDC2626),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final catalogAsync = ref.watch(serviceCatalogProvider);
    final profileAsync = ref.watch(employeeProfileProvider);

    final rawCategories = widget.categories ??
        widget.initialCategories ??
        catalogAsync.value ??
        const <CatalogCategory>[];

    final allRequested = widget.allRequestedServices ??
        widget.initialRequestedServices ??
        profileAsync.value?.allRequestedServices ??
        const <RequestedService>[];

    final isCatalogLoading = !widget.hasError &&
        (widget.categories == null && widget.initialCategories == null) &&
        catalogAsync.isLoading &&
        !catalogAsync.hasValue;

    final catalogError = widget.hasError
        ? Exception('Failed to load catalog')
        : ((widget.categories == null && widget.initialCategories == null)
            ? catalogAsync.error
            : null);

    return DraggableScrollableSheet(
      initialChildSize: 0.90,
      minChildSize: 0.55,
      maxChildSize: 0.96,
      expand: false,
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              // Top Drag Handle
              Padding(
                padding: const EdgeInsets.only(top: 10, bottom: 6),
                child: Center(
                  child: Container(
                    width: 38,
                    height: 4.5,
                    decoration: BoxDecoration(
                      color: const Color(0xFFCBD5E1),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                ),
              ),

              // Modal Header: Back/Close, Title, Refresh
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 4),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.close_rounded, color: Color(0xFF475569), size: 22),
                      tooltip: 'Close',
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                    const SizedBox(width: 2),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: const [
                          Text(
                            'Request New Services from Catalog',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 15.5,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF0F172A),
                              letterSpacing: -0.2,
                            ),
                          ),
                          SizedBox(height: 2),
                          Text(
                            'Select trade services to request operational authorization',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 11.5,
                              color: Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh_rounded, color: Color(0xFF475569), size: 22),
                      tooltip: 'Refresh Catalog',
                      onPressed: () {
                        ref.invalidate(serviceCatalogProvider);
                        ref.invalidate(employeeProfileProvider);
                      },
                    ),
                  ],
                ),
              ),
              const Divider(height: 1, color: Color(0xFFE2E8F0)),

              // Main Content Area
              Expanded(
                child: isCatalogLoading
                    ? const Center(
                        child: CircularProgressIndicator(
                          color: AppColors.peacockBlue,
                        ),
                      )
                    : catalogError != null
                        ? _CatalogErrorView(
                            onRetry: () {
                              ref.invalidate(serviceCatalogProvider);
                              ref.invalidate(employeeProfileProvider);
                            },
                          )
                        : rawCategories.isEmpty
                            ? const _EmptyCatalogView()
                            : _buildCatalogList(
                                context,
                                scrollController,
                                rawCategories,
                                allRequested,
                              ),
              ),

              // Sticky Bottom Action Bar
              _buildStickyBottomBar(context, rawCategories, allRequested),
            ],
          ),
        );
      },
    );
  }

  Widget _buildCatalogList(
    BuildContext context,
    ScrollController scrollController,
    List<CatalogCategory> categories,
    List<RequestedService> allRequested,
  ) {
    final query = _searchQuery.trim().toLowerCase();

    final filteredCategories = categories.where((cat) {
      final nameMatch = cat.name.toLowerCase().contains(query);
      final tagMatch = cat.displayTag.toLowerCase().contains(query);
      return query.isEmpty || nameMatch || tagMatch;
    }).toList();

    final requestableCategories = filteredCategories
        .where((cat) => _isCategoryRequestable(cat, allRequested))
        .toList();

    return ListView(
      controller: scrollController,
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.md,
        AppSpacing.sm,
        AppSpacing.md,
        AppSpacing.lg,
      ),
      children: [
        // Search Input
        TextField(
          decoration: InputDecoration(
            hintText: 'Search services or categories...',
            hintStyle: const TextStyle(fontSize: 12.5, color: Color(0xFF94A3B8)),
            prefixIcon: const Icon(Icons.search, size: 20, color: Color(0xFF64748B)),
            suffixIcon: _searchQuery.isNotEmpty
                ? IconButton(
                    icon: const Icon(Icons.clear_rounded, size: 18, color: Color(0xFF64748B)),
                    onPressed: () => setState(() => _searchQuery = ''),
                  )
                : null,
            filled: true,
            fillColor: const Color(0xFFF8FAFC),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: AppColors.peacockBlue, width: 1.5),
            ),
          ),
          onChanged: (val) => setState(() => _searchQuery = val),
        ),
        const SizedBox(height: AppSpacing.md),

        // Category Filter Header
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 8,
          runSpacing: 4,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'All Categories',
                  style: TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF1E293B),
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1.5),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: Text(
                    '${filteredCategories.length}',
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF475569),
                    ),
                  ),
                ),
              ],
            ),
            if (requestableCategories.isNotEmpty)
              TextButton(
                onPressed: () {
                  setState(() {
                    final reqIds = requestableCategories.map((c) => c.id).toList();
                    final allSelected = reqIds.every(_selectedCategoryIds.contains);
                    if (allSelected) {
                      _selectedCategoryIds.removeAll(reqIds);
                    } else {
                      _selectedCategoryIds.addAll(reqIds);
                    }
                  });
                },
                style: TextButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                ),
                child: Text(
                  requestableCategories.every((c) => _selectedCategoryIds.contains(c.id))
                      ? 'Deselect All'
                      : 'Select All (${requestableCategories.length})',
                  style: const TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    color: AppColors.peacockBlue,
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),

        if (filteredCategories.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 36),
            child: Center(
              child: Text(
                'No matching services or categories found.',
                style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
              ),
            ),
          )
        else
          ...filteredCategories.map((cat) {
            final isApproved = _isCategoryApproved(cat, allRequested);
            final isPending = _isCategoryPending(cat, allRequested);
            final isReq = _isCategoryRequestable(cat, allRequested);
            final isSelected = _selectedCategoryIds.contains(cat.id);

            return Card(
              margin: const EdgeInsets.only(bottom: AppSpacing.sm),
              color: isSelected ? const Color(0xFFF0F9FF) : Colors.white,
              elevation: 0.5,
              shadowColor: const Color(0x0A000000),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(
                  color: isSelected ? AppColors.peacockBlue : const Color(0xFFE2E8F0),
                  width: isSelected ? 1.5 : 1.0,
                ),
              ),
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: isReq ? () => _toggleCategory(cat.id) : null,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: 12,
                  ),
                  child: Row(
                    children: [
                      // Left Category Icon
                      Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: isSelected
                              ? const Color(0xFFE0F2FE)
                              : const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: isSelected
                                ? const Color(0xFFBAE6FD)
                                : const Color(0xFFE2E8F0),
                          ),
                        ),
                        child: Icon(
                          iconForCategory(cat.name),
                          size: 20,
                          color: isSelected
                              ? AppColors.peacockBlue
                              : const Color(0xFF475569),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),

                      // Center Category Details
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 1.5,
                              ),
                              decoration: BoxDecoration(
                                color: isSelected
                                    ? const Color(0xFFE0F2FE)
                                    : const Color(0xFFF1F5F9),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                cat.displayTag,
                                style: TextStyle(
                                  fontSize: 9,
                                  fontWeight: FontWeight.w800,
                                  color: isSelected
                                      ? AppColors.peacockBlue
                                      : const Color(0xFF64748B),
                                  letterSpacing: 0.5,
                                ),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              cat.name,
                              style: TextStyle(
                                fontSize: 13.5,
                                fontWeight: FontWeight.w700,
                                color: isSelected
                                    ? AppColors.peacockNavy
                                    : const Color(0xFF0F172A),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),

                      // Right Side Checkbox or Status Badge
                      if (isApproved)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 7,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFECFDF5),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: const Color(0xFFA7F3D0),
                            ),
                          ),
                          child: const Text(
                            '✓ Already Approved',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF059669),
                            ),
                          ),
                        )
                      else if (isPending)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 7,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFFFFBEB),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: const Color(0xFFFDE68A),
                            ),
                          ),
                          child: const Text(
                            '⏳ Pending Review',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFFD97706),
                            ),
                          ),
                        )
                      else
                        SizedBox(
                          width: 24,
                          height: 24,
                          child: Checkbox(
                            value: isSelected,
                            activeColor: AppColors.peacockBlue,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(4),
                            ),
                            onChanged: (val) => _toggleCategory(cat.id),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            );
          }),
      ],
    );
  }

  Widget _buildStickyBottomBar(
    BuildContext context,
    List<CatalogCategory> categories,
    List<RequestedService> allRequested,
  ) {
    return Container(
      padding: EdgeInsets.fromLTRB(
        AppSpacing.md,
        AppSpacing.sm,
        AppSpacing.md,
        MediaQuery.of(context).viewInsets.bottom + AppSpacing.md,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Color(0x0F000000),
            blurRadius: 10,
            offset: Offset(0, -4),
          ),
        ],
        border: Border(
          top: BorderSide(color: Color(0xFFE2E8F0)),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Live Selection Counter
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  _selectedCategoryIds.isEmpty
                      ? '0 service(s) selected'
                      : _selectedCategoryIds.length == 1
                          ? '1 service selected'
                          : '${_selectedCategoryIds.length} services selected',
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w700,
                    color: _selectedCategoryIds.isEmpty
                        ? const Color(0xFF64748B)
                        : AppColors.peacockBlue,
                  ),
                ),
                if (_selectedCategoryIds.isNotEmpty)
                  GestureDetector(
                    onTap: () => setState(() => _selectedCategoryIds.clear()),
                    child: const Text(
                      'Clear Selection',
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFFEF4444),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 44,
                  child: OutlinedButton(
                    onPressed: _isSubmitting ? null : () => Navigator.of(context).pop(),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF475569),
                      side: const BorderSide(color: Color(0xFFCBD5E1)),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: const Text(
                      'Cancel',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                flex: 2,
                child: SizedBox(
                  height: 44,
                  child: ElevatedButton(
                    onPressed: (_selectedCategoryIds.isEmpty || _isSubmitting)
                        ? null
                        : () => _handleSubmit(categories, allRequested),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.peacockBlue,
                      disabledBackgroundColor: const Color(0xFFE2E8F0),
                      foregroundColor: Colors.white,
                      disabledForegroundColor: const Color(0xFF94A3B8),
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: _isSubmitting
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : Text(
                            _selectedCategoryIds.isEmpty
                                ? 'Submit Request'
                                : 'Submit Request (${_selectedCategoryIds.length})',
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _EmptyCatalogView extends StatelessWidget {
  const _EmptyCatalogView();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: const BoxDecoration(
                color: Color(0xFFF1F5F9),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.inventory_2_outlined,
                size: 36,
                color: Color(0xFF64748B),
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'No services available',
              style: TextStyle(
                fontSize: 15.5,
                fontWeight: FontWeight.w800,
                color: Color(0xFF0F172A),
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'New service categories will appear here when available.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12.5, color: Color(0xFF64748B)),
            ),
          ],
        ),
      ),
    );
  }
}

class _CatalogErrorView extends StatelessWidget {
  const _CatalogErrorView({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: const BoxDecoration(
                color: Color(0xFFFEF2F2),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.error_outline_rounded,
                size: 36,
                color: Color(0xFFDC2626),
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Unable to load service catalog',
              style: TextStyle(
                fontSize: 15.5,
                fontWeight: FontWeight.w800,
                color: Color(0xFF0F172A),
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Please check your connection and try again.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12.5, color: Color(0xFF64748B)),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded, size: 16),
              label: const Text('Retry'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.peacockBlue,
                foregroundColor: Colors.white,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Verified Skill Ratings Section ────────────────────────────────────────────

class _VerifiedSkillsSection extends StatelessWidget {
  const _VerifiedSkillsSection({required this.skills});

  final List<EmployeeSkill> skills;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.background,
              border: Border(bottom: BorderSide(color: AppColors.border)),
            ),
            child: Row(
              children: [
                const Icon(Icons.star_outline_rounded, size: 16, color: Color(0xFF2563EB)),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    'VERIFIED SKILL RATINGS (${skills.length})',
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
              ],
            ),
          ),
          if (skills.isEmpty)
            const Padding(
              padding: EdgeInsets.all(AppSpacing.xl),
              child: EmptyState(
                icon: Icons.military_tech_outlined,
                title: 'No skill certifications assigned yet',
                message: 'Verified skill ratings will be displayed once evaluated by Workforce administration.',
                compact: true,
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: skills.length,
              separatorBuilder: (context, index) => Divider(height: 1, color: AppColors.border),
              itemBuilder: (context, index) {
                final sk = skills[index];
                return Padding(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              sk.skillName,
                              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                            ),
                            if (sk.category != null && sk.category!.isNotEmpty)
                              Text(
                                sk.category!,
                                style: TextStyle(fontSize: 10.5, color: AppColors.textMuted),
                              ),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEFF6FF),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: const Color(0xFFBFDBFE)),
                        ),
                        child: Text(
                          sk.proficiencyLevel.toUpperCase(),
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF1D4ED8),
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
