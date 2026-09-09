import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/empty_state.dart';
import '../../../../shared/widgets/status_chip.dart';
import '../../../../shared/widgets/workforce_app_bar.dart';
import '../../../../shared/widgets/workforce_avatar.dart';
import '../../data/admin_dashboard_api.dart';
import '../../domain/tied_technician.dart';
import '../admin_dashboard_providers.dart';
import '../widgets/admin_drawer.dart';

/// Admin Tied Technicians Screen.
/// Displays and manages technicians linked to the authenticated service provider vendor business.
class AdminTiedTechniciansScreen extends ConsumerStatefulWidget {
  const AdminTiedTechniciansScreen({super.key});

  @override
  ConsumerState<AdminTiedTechniciansScreen> createState() =>
      _AdminTiedTechniciansScreenState();
}

class _AdminTiedTechniciansScreenState
    extends ConsumerState<AdminTiedTechniciansScreen> {
  String _selectedStatus = 'ALL';
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();
  int? _actionLoadingRelId;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _handleStatusAction({
    required int relationshipId,
    required String action,
    required String techName,
  }) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('${action == 'SUSPEND' ? 'Suspend' : action == 'ACTIVATE' ? 'Reactivate' : 'Update'} Technician'),
        content: Text(
          'Are you sure you want to ${action.toLowerCase()} $techName from your active service network?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: action == 'SUSPEND'
                  ? const Color(0xFFD97706)
                  : const Color(0xFF004E89),
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(action == 'SUSPEND' ? 'Suspend' : 'Confirm'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      setState(() => _actionLoadingRelId = relationshipId);
      final api = ref.read(adminDashboardApiProvider);
      await api.updateVendorTechnicianStatus(
        relationshipId: relationshipId,
        action: action,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$techName status updated successfully.'),
            backgroundColor: const Color(0xFF059669),
          ),
        );
        ref.invalidate(adminVendorNetworkProvider);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update status: $e'),
            backgroundColor: const Color(0xFFDC2626),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _actionLoadingRelId = null);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final params = VendorNetworkParams(
      status: _selectedStatus == 'ALL' ? null : _selectedStatus,
      search: _searchQuery.trim().isEmpty ? null : _searchQuery.trim(),
    );
    final networkAsync = ref.watch(adminVendorNetworkProvider(params));

    return Scaffold(
      appBar: const WorkforceAppBar(
        titleText: 'Tied Technicians',
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(adminVendorNetworkProvider);
          await ref.read(adminVendorNetworkProvider(params).future);
        },
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.md),
          children: [
            // ── Header Card ──────────────────────────────────────────────
            Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(AppRadius.card),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEFF6FF),
                          borderRadius: BorderRadius.circular(5),
                          border: Border.all(color: const Color(0xFFBFDBFE)),
                        ),
                        child: const Text(
                          'MY WORKFORCE',
                          style: TextStyle(
                            fontSize: 9.5,
                            fontWeight: FontWeight.w900,
                            color: Color(0xFF004E89),
                            letterSpacing: 0.6,
                          ),
                        ),
                      ),
                      IconButton(
                        onPressed: () => ref.invalidate(adminVendorNetworkProvider),
                        icon: const Icon(Icons.refresh_rounded, size: 20, color: Color(0xFF004E89)),
                        tooltip: 'Refresh Roster',
                        visualDensity: VisualDensity.compact,
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Tied Technicians',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                      color: Color(0xFF0F172A),
                    ),
                  ),
                  const SizedBox(height: 2),
                  const Text(
                    'Technicians attached to your service provider company entity',
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFF64748B),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── Search & Filter ──────────────────────────────────────────
            TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search by technician name, email or phone...',
                prefixIcon: const Icon(Icons.search_rounded, size: 20, color: Color(0xFF64748B)),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear_rounded, size: 18),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchQuery = '');
                        },
                      )
                    : null,
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.card),
                  borderSide: const BorderSide(color: Color(0xFFCBD5E1)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.card),
                  borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                ),
              ),
              onChanged: (val) => setState(() => _searchQuery = val),
            ),
            const SizedBox(height: AppSpacing.sm),

            // ── Status Filter Chips ──────────────────────────────────────
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildStatusChip('ALL', 'All'),
                  const SizedBox(width: 6),
                  _buildStatusChip('ACTIVE', 'Active'),
                  const SizedBox(width: 6),
                  _buildStatusChip('SUSPENDED', 'Suspended'),
                  const SizedBox(width: 6),
                  _buildStatusChip('RESIGNED', 'Resigned'),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── Technician List or States ────────────────────────────────
            networkAsync.when(
              loading: () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(AppSpacing.xl),
                  child: CircularProgressIndicator(),
                ),
              ),
              error: (err, _) => Container(
                padding: const EdgeInsets.all(AppSpacing.lg),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(AppRadius.card),
                  border: Border.all(color: const Color(0xFFFECACA)),
                ),
                child: Column(
                  children: [
                    const Icon(Icons.error_outline_rounded, color: Color(0xFFDC2626), size: 36),
                    const SizedBox(height: 8),
                    Text(
                      'Failed to load tied technicians: $err',
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 12.5, color: Color(0xFF991B1B)),
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: () => ref.invalidate(adminVendorNetworkProvider),
                      icon: const Icon(Icons.refresh_rounded, size: 16),
                      label: const Text('Retry'),
                    ),
                  ],
                ),
              ),
              data: (data) {
                final techs = data.technicians;
                if (techs.isEmpty) {
                  return const EmptyState(
                    icon: Icons.people_outline_rounded,
                    title: 'No Tied Technicians',
                    message: 'No technicians found matching the selected filter criteria.',
                  );
                }

                return Column(
                  children: techs.map((tech) => _buildTechCard(tech)).toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusChip(String value, String label) {
    final isSelected = _selectedStatus == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (_) => setState(() => _selectedStatus = value),
      selectedColor: const Color(0xFF004E89),
      backgroundColor: Colors.white,
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w700,
        color: isSelected ? Colors.white : const Color(0xFF475569),
      ),
      side: BorderSide(
        color: isSelected ? const Color(0xFF004E89) : const Color(0xFFCBD5E1),
      ),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    );
  }

  Widget _buildTechCard(TiedTechnician tech) {
    final isActing = _actionLoadingRelId == tech.relationshipId;

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x040A2540),
            blurRadius: 3,
            offset: Offset(0, 1),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top Row: Avatar + Name + Badges
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              WorkforceAvatar(
                name: tech.name,
                radius: 22,
                fontSize: 14,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            tech.name,
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF0F172A),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: tech.isOnline ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text(
                      tech.title,
                      style: const TextStyle(
                        fontSize: 11.5,
                        color: Color(0xFF64748B),
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              StatusChip(
                status: tech.status,
              ),
            ],
          ),
          const SizedBox(height: 10),
          const Divider(height: 1, color: Color(0xFFF1F5F9)),
          const SizedBox(height: 10),

          // Contact Details & Metrics
          Row(
            children: [
              if (tech.phone.isNotEmpty) ...[
                const Icon(Icons.phone_outlined, size: 14, color: Color(0xFF64748B)),
                const SizedBox(width: 4),
                Text(
                  tech.phone,
                  style: const TextStyle(fontSize: 11.5, color: Color(0xFF334155)),
                ),
                const SizedBox(width: 12),
              ],
              if (tech.averageRating > 0) ...[
                const Icon(Icons.star_rounded, size: 15, color: Color(0xFFF59E0B)),
                const SizedBox(width: 3),
                Text(
                  '${tech.averageRating.toStringAsFixed(1)} (${tech.ratingCount})',
                  style: const TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(width: 8),
              ],
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  tech.tier,
                  style: const TextStyle(
                    fontSize: 9.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF475569),
                  ),
                ),
              ),
            ],
          ),

          // Skills Tags
          if (tech.scopeSkills.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: tech.scopeSkills.take(4).map((skill) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEFF6FF),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: const Color(0xFFDBEAFE), width: 0.8),
                  ),
                  child: Text(
                    skill,
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF004E89),
                    ),
                  ),
                );
              }).toList(),
            ),
          ],

          const SizedBox(height: 10),
          // Action Buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (isActing)
                const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              else if (tech.isActive)
                OutlinedButton.icon(
                  onPressed: () => _handleStatusAction(
                    relationshipId: tech.relationshipId,
                    action: 'SUSPEND',
                    techName: tech.name,
                  ),
                  icon: const Icon(Icons.pause_circle_outline_rounded, size: 14, color: Color(0xFFD97706)),
                  label: const Text('Suspend'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFFB45309),
                    visualDensity: VisualDensity.compact,
                    textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  ),
                )
              else if (tech.isSuspended)
                FilledButton.icon(
                  onPressed: () => _handleStatusAction(
                    relationshipId: tech.relationshipId,
                    action: 'ACTIVATE',
                    techName: tech.name,
                  ),
                  icon: const Icon(Icons.play_circle_outline_rounded, size: 14),
                  label: const Text('Reactivate'),
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF004E89),
                    visualDensity: VisualDensity.compact,
                    textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
