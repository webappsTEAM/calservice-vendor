import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/empty_state.dart';
import '../../../../shared/widgets/status_chip.dart';
import '../../../../shared/widgets/workforce_app_bar.dart';
import '../../../../shared/widgets/workforce_avatar.dart';
import '../../domain/admin_application.dart';
import '../admin_dashboard_providers.dart';
import '../widgets/admin_drawer.dart';

/// Admin Workforce Employee Roster Screen.
/// Displays directory of field technicians, presence statuses, and dispatch credentials.
class AdminEmployeesScreen extends ConsumerStatefulWidget {
  const AdminEmployeesScreen({super.key});

  @override
  ConsumerState<AdminEmployeesScreen> createState() => _AdminEmployeesScreenState();
}

class _AdminEmployeesScreenState extends ConsumerState<AdminEmployeesScreen> {
  String _searchTerm = '';
  String _statusFilter = 'ALL'; // 'ALL', 'APPROVED', 'PENDING'
  String _presenceFilter = 'ALL'; // 'ALL', 'ONLINE', 'OFFLINE'
  int _currentPage = 1;
  static const int _pageSize = 10;

  final TextEditingController _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final applicationsAsync = ref.watch(adminApplicationsListProvider(null));

    return Scaffold(
      appBar: const WorkforceAppBar(
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: applicationsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline_rounded, color: Color(0xFFDC2626), size: 40),
                const SizedBox(height: 12),
                Text('Failed to load employee roster: $err', textAlign: TextAlign.center),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: () => ref.invalidate(adminApplicationsListProvider(null)),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
        data: (allTechs) {
          // Filter technicians
          final filtered = allTechs.where((tech) {
            final term = _searchTerm.toLowerCase().trim();
            final name = (tech.name ?? '').toLowerCase();
            final empId = (tech.employeeId ?? '').toLowerCase();
            final phone = (tech.phone ?? '').toLowerCase();
            final email = (tech.email ?? '').toLowerCase();
            final company = (tech.companyName ?? '').toLowerCase();
            final matchesSearch = term.isEmpty ||
                name.contains(term) ||
                empId.contains(term) ||
                phone.contains(term) ||
                email.contains(term) ||
                company.contains(term);

            // Status filter
            bool matchesStatus = true;
            if (_statusFilter == 'ACTIVE') {
              matchesStatus = tech.isApproved || tech.registrationStatus == 'active';
            } else if (_statusFilter == 'PENDING') {
              matchesStatus = tech.isPending;
            } else if (_statusFilter == 'INACTIVE') {
              matchesStatus = tech.registrationStatus == 'not_started' ||
                  tech.registrationStatus == 'in_progress' ||
                  (!tech.isApproved && !tech.isPending && !tech.isCorrectionRequired && !tech.isRejected);
            } else if (_statusFilter == 'CORRECTION_REQUIRED') {
              matchesStatus = tech.isCorrectionRequired;
            } else if (_statusFilter == 'REJECTED') {
              matchesStatus = tech.isRejected;
            }

            // Presence filter
            bool matchesPresence = true;
            if (_presenceFilter == 'ONLINE') {
              matchesPresence = tech.isOnline && !tech.isBusy;
            } else if (_presenceFilter == 'OFFLINE') {
              matchesPresence = !tech.isOnline && !tech.isBusy;
            } else if (_presenceFilter == 'BUSY') {
              matchesPresence = tech.isBusy;
            }

            return matchesSearch && matchesStatus && matchesPresence;
          }).toList();

          final totalCount = filtered.length;
          final totalPages = (totalCount / _pageSize).ceil().clamp(1, 9999);
          final safePage = _currentPage.clamp(1, totalPages);
          final startIndex = (safePage - 1) * _pageSize;
          final endIndex = (startIndex + _pageSize).clamp(0, totalCount);
          final pageItems = startIndex < totalCount
              ? filtered.sublist(startIndex, endIndex)
              : <AdminApplication>[];

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(adminApplicationsListProvider(null));
              await ref.read(adminApplicationsListProvider(null).future);
            },
            child: ListView(
              padding: const EdgeInsets.all(AppSpacing.md),
              children: [
                // ── Header Title & Subtitle ──────────────────────────────────
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEFF6FF),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(
                        Icons.people_alt_rounded,
                        color: Color(0xFF2563EB),
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Workforce Employee Roster',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF0F172A),
                            ),
                          ),
                          const SizedBox(height: 2),
                          const Text(
                            'Directory of field technicians, active roster statuses, and dispatch credentials',
                            style: TextStyle(
                              fontSize: 12,
                              color: Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),

                // ── Search Field ─────────────────────────────────────────────
                TextField(
                  controller: _searchController,
                  onChanged: (val) => setState(() {
                    _searchTerm = val;
                    _currentPage = 1;
                  }),
                  decoration: InputDecoration(
                    hintText: 'Search by technician name, ID, or phone...',
                    hintStyle: const TextStyle(fontSize: 13, color: Color(0xFF94A3B8)),
                    prefixIcon: const Icon(Icons.search_rounded, size: 20, color: Color(0xFF64748B)),
                    suffixIcon: _searchTerm.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear_rounded, size: 18),
                            onPressed: () {
                              _searchController.clear();
                              setState(() {
                                _searchTerm = '';
                                _currentPage = 1;
                              });
                            },
                          )
                        : null,
                    filled: true,
                    fillColor: Colors.white,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(AppRadius.input),
                      borderSide: const BorderSide(color: Color(0xFFCBD5E1)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(AppRadius.input),
                      borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),

                // ── Status & Presence Dropdown Filters ─────────────────────────
                LayoutBuilder(
                  builder: (context, constraints) {
                    final isCompact = constraints.maxWidth < 360;
                    if (isCompact) {
                      return Column(
                        children: [
                          _buildStatusDropdown(),
                          const SizedBox(height: 8),
                          _buildPresenceDropdown(),
                        ],
                      );
                    }
                    return Row(
                      children: [
                        Expanded(child: _buildStatusDropdown()),
                        const SizedBox(width: 8),
                        Expanded(child: _buildPresenceDropdown()),
                      ],
                    );
                  },
                ),
                const SizedBox(height: AppSpacing.md),

                // ── Technicians List ─────────────────────────────────────────
                if (filtered.isEmpty)
                  const EmptyState(
                    icon: Icons.people_outline_rounded,
                    title: 'No Technicians Found',
                    message: 'No employee records match the selected filters.',
                  )
                else ...[
                  ...pageItems.map((tech) => _AdminEmployeeCard(
                        tech: tech,
                        onViewDetails: () => _showEmployeeDetailsModal(context, tech),
                      )),

                  const SizedBox(height: AppSpacing.md),

                  // ── Mobile Pagination Bar ──────────────────────────────────
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(AppRadius.card),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        IconButton(
                          onPressed: safePage > 1
                              ? () => setState(() => _currentPage = safePage - 1)
                              : null,
                          icon: const Icon(Icons.chevron_left_rounded, size: 20),
                          tooltip: 'Prev Page',
                          visualDensity: VisualDensity.compact,
                        ),
                        Flexible(
                          child: Text(
                            'Page $safePage / $totalPages ($totalCount)',
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF475569),
                            ),
                            textAlign: TextAlign.center,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        IconButton(
                          onPressed: safePage < totalPages
                              ? () => setState(() => _currentPage = safePage + 1)
                              : null,
                          icon: const Icon(Icons.chevron_right_rounded, size: 20),
                          tooltip: 'Next Page',
                          visualDensity: VisualDensity.compact,
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: AppSpacing.xl),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildStatusDropdown() {
    final isSelected = _statusFilter != 'ALL';
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.input),
        border: Border.all(
          color: isSelected ? const Color(0xFF004E89) : const Color(0xFFCBD5E1),
          width: isSelected ? 1.5 : 1.0,
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x040A2540),
            blurRadius: 4,
            offset: Offset(0, 1),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          key: const Key('admin_status_filter_dropdown'),
          value: _statusFilter,
          isExpanded: true,
          icon: const Icon(Icons.keyboard_arrow_down_rounded, size: 20, color: Color(0xFF64748B)),
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w600,
            color: isSelected ? const Color(0xFF004E89) : const Color(0xFF334155),
          ),
          onChanged: (val) {
            if (val != null) {
              setState(() {
                _statusFilter = val;
                _currentPage = 1;
              });
            }
          },
          items: const [
            DropdownMenuItem(
              value: 'ALL',
              child: Row(
                children: [
                  Icon(Icons.filter_alt_outlined, size: 16, color: Color(0xFF64748B)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text('All Status', overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
            DropdownMenuItem(
              value: 'ACTIVE',
              child: Row(
                children: [
                  Icon(Icons.check_circle_outline_rounded, size: 16, color: Color(0xFF10B981)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text('Active', overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
            DropdownMenuItem(
              value: 'PENDING',
              child: Row(
                children: [
                  Icon(Icons.hourglass_top_rounded, size: 16, color: Color(0xFFF59E0B)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text('Pending', overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
            DropdownMenuItem(
              value: 'INACTIVE',
              child: Row(
                children: [
                  Icon(Icons.pause_circle_outline_rounded, size: 16, color: Color(0xFF94A3B8)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text('Inactive', overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
            DropdownMenuItem(
              value: 'CORRECTION_REQUIRED',
              child: Row(
                children: [
                  Icon(Icons.edit_note_rounded, size: 16, color: Color(0xFFF97316)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text('Correction Required', overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
            DropdownMenuItem(
              value: 'REJECTED',
              child: Row(
                children: [
                  Icon(Icons.cancel_outlined, size: 16, color: Color(0xFFF43F5E)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text('Rejected', overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPresenceDropdown() {
    final isSelected = _presenceFilter != 'ALL';
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.input),
        border: Border.all(
          color: isSelected ? const Color(0xFF059669) : const Color(0xFFCBD5E1),
          width: isSelected ? 1.5 : 1.0,
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x040A2540),
            blurRadius: 4,
            offset: Offset(0, 1),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          key: const Key('admin_presence_filter_dropdown'),
          value: _presenceFilter,
          isExpanded: true,
          icon: const Icon(Icons.keyboard_arrow_down_rounded, size: 20, color: Color(0xFF64748B)),
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w600,
            color: isSelected ? const Color(0xFF059669) : const Color(0xFF334155),
          ),
          onChanged: (val) {
            if (val != null) {
              setState(() {
                _presenceFilter = val;
                _currentPage = 1;
              });
            }
          },
          items: const [
            DropdownMenuItem(
              value: 'ALL',
              child: Row(
                children: [
                  Icon(Icons.sensors_rounded, size: 16, color: Color(0xFF64748B)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text('All Presence', overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
            DropdownMenuItem(
              value: 'ONLINE',
              child: Row(
                children: [
                  Icon(Icons.wifi_tethering_rounded, size: 16, color: Color(0xFF10B981)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text('Online', overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
            DropdownMenuItem(
              value: 'OFFLINE',
              child: Row(
                children: [
                  Icon(Icons.wifi_tethering_off_rounded, size: 16, color: Color(0xFF94A3B8)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text('Offline', overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
            DropdownMenuItem(
              value: 'BUSY',
              child: Row(
                children: [
                  Icon(Icons.work_outline_rounded, size: 16, color: Color(0xFF3B82F6)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text('Busy (On Job)', overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showEmployeeDetailsModal(BuildContext context, AdminApplication tech) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
      ),
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        maxChildSize: 0.9,
        minChildSize: 0.4,
        expand: false,
        builder: (sheetCtx, scrollController) => ListView(
          controller: scrollController,
          padding: const EdgeInsets.all(AppSpacing.lg),
          children: [
            Center(
              child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: const Color(0xFFCBD5E1),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                WorkforceAvatar(
                  imageUrl: tech.avatar,
                  name: tech.name,
                  initial: tech.initial,
                  radius: 26,
                  fontSize: 20,
                  backgroundColor: const Color(0xFF004E89).withValues(alpha: 0.1),
                  foregroundColor: const Color(0xFF004E89),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        tech.name ?? 'Technician #${tech.id}',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        tech.employeeId != null ? 'ID: ${tech.employeeId}' : 'ID: Pending',
                        style: const TextStyle(
                          fontSize: 12,
                          fontFamily: 'monospace',
                          color: Color(0xFF64748B),
                        ),
                      ),
                    ],
                  ),
                ),
                StatusChip(status: tech.registrationStatus, dense: true),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            const Divider(height: 1),
            const SizedBox(height: AppSpacing.md),

            // Presence & Contact Info
            _detailRow(Icons.sensors_rounded, 'Presence', tech.isOnline ? 'Online (Ready)' : 'Offline',
                valColor: tech.isOnline ? const Color(0xFF059669) : const Color(0xFF64748B)),
            if (tech.phone != null)
              _detailRow(Icons.phone_rounded, 'Phone', tech.phone!),
            if (tech.email != null)
              _detailRow(Icons.email_rounded, 'Email', tech.email!),
            if (tech.companyName != null)
              _detailRow(Icons.business_rounded, 'Company', tech.companyName!),

            const SizedBox(height: AppSpacing.md),
            const Text(
              'Approved Services',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Color(0xFF0F172A)),
            ),
            const SizedBox(height: AppSpacing.xs),
            if (tech.allRequestedServices.isEmpty)
              const Text('No services currently assigned.',
                  style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)))
            else
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: tech.allRequestedServices.map((s) {
                  final isAppr = s.isApproved;
                  return Chip(
                    visualDensity: VisualDensity.compact,
                    backgroundColor: isAppr ? const Color(0xFFECFDF5) : const Color(0xFFF1F5F9),
                    side: BorderSide(
                        color: isAppr ? const Color(0xFFA7F3D0) : const Color(0xFFE2E8F0)),
                    label: Text(
                      s.name,
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        color: isAppr ? const Color(0xFF065F46) : const Color(0xFF475569),
                      ),
                    ),
                  );
                }).toList(),
              ),

            const SizedBox(height: AppSpacing.lg),
            FilledButton.icon(
              onPressed: () {
                Navigator.of(ctx).pop();
                context.push('/admin/applications/${tech.id}');
              },
              icon: const Icon(Icons.folder_shared_rounded, size: 18),
              label: const Text('Review Full Dossier'),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF004E89),
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _detailRow(IconData icon, String label, String value, {Color? valColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(icon, size: 16, color: const Color(0xFF64748B)),
          const SizedBox(width: 8),
          Text('$label: ', style: const TextStyle(fontSize: 12.5, color: Color(0xFF64748B))),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
                color: valColor ?? const Color(0xFF0F172A),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AdminEmployeeCard extends StatelessWidget {
  const _AdminEmployeeCard({
    required this.tech,
    required this.onViewDetails,
  });

  final AdminApplication tech;
  final VoidCallback onViewDetails;

  @override
  Widget build(BuildContext context) {
    final services = tech.approvedServices.isNotEmpty
        ? tech.approvedServices.map((s) => s.name).join(' • ')
        : (tech.allRequestedServices.isNotEmpty
            ? tech.allRequestedServices.map((s) => s.name).join(' • ')
            : 'No services assigned');

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x060A2540),
            blurRadius: 4,
            offset: Offset(0, 1.5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Row 1: Avatar, Name, ID, Approval Status
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              WorkforceAvatar(
                imageUrl: tech.avatar,
                name: tech.name,
                initial: tech.initial,
                radius: 18,
                fontSize: 14,
                backgroundColor: const Color(0xFF004E89).withValues(alpha: 0.1),
                foregroundColor: const Color(0xFF004E89),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      tech.name ?? 'Technician #${tech.id}',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 1),
                    Text(
                      tech.employeeId != null ? 'ID: ${tech.employeeId}' : 'ID: Pending',
                      style: const TextStyle(
                        fontSize: 11,
                        fontFamily: 'monospace',
                        color: Color(0xFF64748B),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              Flexible(
                child: StatusChip(status: tech.registrationStatus, dense: true),
              ),
            ],
          ),

          const SizedBox(height: 10),

          // Row 2: Presence Indicator Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: tech.isBusy
                  ? const Color(0xFFEFF6FF)
                  : (tech.isOnline ? const Color(0xFFECFDF5) : const Color(0xFFF1F5F9)),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: tech.isBusy
                    ? const Color(0xFFBFDBFE)
                    : (tech.isOnline ? const Color(0xFFA7F3D0) : const Color(0xFFE2E8F0)),
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
                    color: tech.isBusy
                        ? const Color(0xFF3B82F6)
                        : (tech.isOnline ? const Color(0xFF10B981) : const Color(0xFF94A3B8)),
                  ),
                ),
                const SizedBox(width: 5),
                Text(
                  tech.isBusy
                      ? 'Busy (On Job)'
                      : (tech.isOnline ? 'Online (Ready)' : 'Offline'),
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: tech.isBusy
                        ? const Color(0xFF1D4ED8)
                        : (tech.isOnline ? const Color(0xFF065F46) : const Color(0xFF64748B)),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 8),

          // Row 3: Services Count & Preview
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Services: ',
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF475569),
                ),
              ),
              Text(
                '${tech.allRequestedServices.length}',
                style: const TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF004E89),
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(
            services,
            style: const TextStyle(
              fontSize: 11.5,
              color: Color(0xFF64748B),
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),

          // Row 4: Phone & View Details Action
          const SizedBox(height: 10),
          const Divider(height: 1),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (tech.phone != null && tech.phone!.isNotEmpty)
                Expanded(
                  child: Text.rich(
                    TextSpan(
                      children: [
                        const WidgetSpan(
                          alignment: PlaceholderAlignment.middle,
                          child: Padding(
                            padding: EdgeInsets.only(right: 4),
                            child: Icon(Icons.phone_rounded, size: 14, color: Color(0xFF64748B)),
                          ),
                        ),
                        TextSpan(
                          text: tech.phone!,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF334155),
                          ),
                        ),
                      ],
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                )
              else
                const Text('—', style: TextStyle(color: Color(0xFF94A3B8))),
              const SizedBox(width: 8),
              InkWell(
                onTap: onViewDetails,
                borderRadius: BorderRadius.circular(4),
                child: const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'View Details',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF004E89),
                        ),
                      ),
                      SizedBox(width: 2),
                      Icon(Icons.arrow_forward_rounded, size: 14, color: Color(0xFF004E89)),
                    ],
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
