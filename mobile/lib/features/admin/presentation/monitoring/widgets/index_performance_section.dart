import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/admin_monitoring.dart';
import 'package:mobile/features/admin/presentation/monitoring/admin_monitoring_providers.dart';
import 'index_card.dart';
import 'index_filter_sheet.dart';

/// Section rendering PostgreSQL search shortcut indexes, search, status filters, and pagination.
class IndexPerformanceSection extends ConsumerStatefulWidget {
  const IndexPerformanceSection({
    super.key,
    required this.data,
  });

  final AdminMonitoringData data;

  @override
  ConsumerState<IndexPerformanceSection> createState() => _IndexPerformanceSectionState();
}

class _IndexPerformanceSectionState extends ConsumerState<IndexPerformanceSection> {
  late TextEditingController _searchController;

  @override
  void initState() {
    super.initState();
    final filter = ref.read(adminMonitoringFilterProvider);
    _searchController = TextEditingController(text: filter.search);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final indexHealth = widget.data.indexHealth;
    final filter = ref.watch(adminMonitoringFilterProvider);
    final indexes = indexHealth.indexes;
    final allTables = indexHealth.allTables;

    final startItem = indexHealth.filteredCount == 0
        ? 0
        : (indexHealth.page - 1) * indexHealth.pageSize + 1;
    final endItem = (startItem + indexes.length - 1).clamp(0, indexHealth.filteredCount);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ── Section Title & Subtitle ─────────────────────────────────────
        const Text(
          'Database Search Shortcuts',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w900,
            color: Color(0xFF0A2540),
            letterSpacing: -0.3,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          'Index Performance & Scans',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: AppColors.textMuted,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),

        // ── Non-Technical Explanation Card ──────────────────────────────
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: const Color(0xFFEFF6FF),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFFBFDBFE)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              Icon(Icons.lightbulb_outline_rounded, size: 18, color: Color(0xFF1D4ED8)),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Indexes allow the database to jump straight to the exact row instead of reading through thousands of records.',
                  style: TextStyle(
                    fontSize: 12,
                    color: Color(0xFF1E40AF),
                    height: 1.35,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.sm),

        // ── Actual Measurement Information Card ─────────────────────────
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                      color: Color(0xFF059669),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'ACTUAL MEASUREMENT',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.8,
                      color: Color(0xFF475569),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              _buildLegendRow('⚡ Shortcut Used:', 'How many times PostgreSQL used this shortcut to fulfill queries.'),
              const SizedBox(height: 4),
              _buildLegendRow('📖 Entries Examined:', 'How many index entries were checked during search lookups.'),
              const SizedBox(height: 4),
              _buildLegendRow('🎯 Rows Returned:', 'Actual live records delivered back to the application.'),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),

        // ── Search & Filter Controls ────────────────────────────────────
        // Search Input Field
        TextField(
          controller: _searchController,
          decoration: InputDecoration(
            hintText: 'Search table or index name...',
            prefixIcon: const Icon(Icons.search_rounded, size: 18),
            suffixIcon: filter.search.isNotEmpty
                ? IconButton(
                    icon: const Icon(Icons.clear_rounded, size: 16),
                    onPressed: () {
                      _searchController.clear();
                      ref.read(adminMonitoringFilterProvider.notifier).state =
                          filter.copyWith(search: '', page: 1);
                    },
                  )
                : null,
            isDense: true,
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(color: Color(0xFFCBD5E1)),
            ),
          ),
          onSubmitted: (val) {
            ref.read(adminMonitoringFilterProvider.notifier).state =
                filter.copyWith(search: val.trim(), page: 1);
          },
        ),
        const SizedBox(height: 8),

        // Filter Bar: Table Filter Button + Status Chips
        Row(
          children: [
            // Table selector button
            OutlinedButton.icon(
              onPressed: () {
                IndexTableFilterSheet.show(
                  context,
                  tables: allTables,
                  selectedTable: filter.table,
                  onSelected: (table) {
                    ref.read(adminMonitoringFilterProvider.notifier).state =
                        filter.copyWith(table: table, page: 1);
                  },
                );
              },
              icon: const Icon(Icons.table_chart_outlined, size: 14),
              label: Text(
                filter.table == 'ALL' ? 'All Tables' : filter.table,
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ),
            const SizedBox(width: 8),

            // Status Filter Chips
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _buildStatusChip('All Statuses', 'ALL', filter.status),
                    const SizedBox(width: 6),
                    _buildStatusChip('Actively Used', 'USED', filter.status),
                    const SizedBox(width: 6),
                    _buildStatusChip('No Scans Recorded', 'NO_SCANS', filter.status),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),

        // Pagination summary row: "Showing X to Y of Z indexes"
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                'Showing $startItem to $endItem of ${indexHealth.filteredCount} indexes',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
            if (filter.table != 'ALL' || filter.status != 'ALL' || filter.search.isNotEmpty) ...[
              const SizedBox(width: 6),
              TextButton(
                onPressed: () {
                  _searchController.clear();
                  ref.read(adminMonitoringFilterProvider.notifier).state =
                      const AdminMonitoringFilter();
                },
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: const Text('Clear Filters', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
              ),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.sm),

        // ── Index Cards List ────────────────────────────────────────────
        if (indexes.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.xl),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Column(
              children: [
                const Icon(Icons.search_off_rounded, size: 36, color: Color(0xFF94A3B8)),
                const SizedBox(height: 8),
                Text(
                  filter.search.isNotEmpty || filter.table != 'ALL' || filter.status != 'ALL'
                      ? 'No indexes matching your filters.'
                      : 'No index telemetry available.',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF475569),
                  ),
                ),
              ],
            ),
          )
        else
          ...indexes.map((idx) => IndexCard(index: idx)),

        // ── Pagination Controls ─────────────────────────────────────────
        if (indexHealth.totalPages > 1) ...[
          const SizedBox(height: AppSpacing.sm),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                OutlinedButton.icon(
                  onPressed: indexHealth.page > 1
                      ? () {
                          ref.read(adminMonitoringFilterProvider.notifier).state =
                              filter.copyWith(page: indexHealth.page - 1);
                        }
                      : null,
                  icon: const Icon(Icons.chevron_left_rounded, size: 16),
                  label: const Text('Previous', style: TextStyle(fontSize: 11.5)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    minimumSize: Size.zero,
                  ),
                ),
                const SizedBox(width: 12),
                Text(
                  'Page ${indexHealth.page} of ${indexHealth.totalPages}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0A2540),
                  ),
                ),
                const SizedBox(width: 12),
                OutlinedButton.icon(
                  onPressed: indexHealth.page < indexHealth.totalPages
                      ? () {
                          ref.read(adminMonitoringFilterProvider.notifier).state =
                              filter.copyWith(page: indexHealth.page + 1);
                        }
                      : null,
                  icon: const Icon(Icons.chevron_right_rounded, size: 16),
                  label: const Text('Next', style: TextStyle(fontSize: 11.5)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    minimumSize: Size.zero,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildLegendRow(String title, String desc) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            color: Color(0xFF1E293B),
          ),
        ),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            desc,
            style: TextStyle(
              fontSize: 11,
              color: AppColors.textMuted,
              height: 1.25,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStatusChip(String label, String value, String currentStatus) {
    final isSelected = currentStatus == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      selectedColor: const Color(0xFF004E89),
      labelStyle: TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        color: isSelected ? Colors.white : AppColors.textSecondary,
      ),
      padding: EdgeInsets.zero,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      onSelected: (selected) {
        if (selected) {
          ref.read(adminMonitoringFilterProvider.notifier).state =
              ref.read(adminMonitoringFilterProvider).copyWith(status: value, page: 1);
        }
      },
    );
  }
}
