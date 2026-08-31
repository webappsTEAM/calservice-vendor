import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/admin_monitoring.dart';

/// Detailed Table Storage ranked by PostgreSQL disk usage.
class TableStorageSection extends StatefulWidget {
  const TableStorageSection({
    super.key,
    required this.data,
  });

  final AdminMonitoringData data;

  @override
  State<TableStorageSection> createState() => _TableStorageSectionState();
}

class _TableStorageSectionState extends State<TableStorageSection> {
  int _visibleCount = 6;

  @override
  Widget build(BuildContext context) {
    final tableStorage = widget.data.indexHealth.tableStorage;
    final maxBytes = tableStorage.isNotEmpty
        ? tableStorage.map((e) => e.totalBytes).reduce((a, b) => a > b ? a : b)
        : 1;

    final displayedTables = tableStorage.take(_visibleCount).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ── Section Title & Subtitle ─────────────────────────────────────
        const Text(
          'Detailed Table Storage',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w900,
            color: Color(0xFF0A2540),
            letterSpacing: -0.3,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          'Ranked by Disk Usage',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: AppColors.textMuted,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),

        // ── Table Storage List ──────────────────────────────────────────
        if (tableStorage.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.lg),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Text(
              'No table storage telemetry available.',
              style: TextStyle(fontSize: 13, color: AppColors.textMuted),
            ),
          )
        else ...[
          ...displayedTables.map((tbl) {
            final proportion = maxBytes > 0 ? (tbl.totalBytes / maxBytes).clamp(0.0, 1.0) : 0.0;

            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(5),
                        decoration: BoxDecoration(
                          color: const Color(0xFF004E89).withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Icon(Icons.table_rows_rounded, size: 16, color: Color(0xFF004E89)),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          tbl.tableName,
                          style: const TextStyle(
                            fontFamily: 'monospace',
                            fontSize: 13,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF0A2540),
                          ),
                        ),
                      ),
                      Text(
                        tbl.totalSize,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w900,
                          color: Color(0xFF0A2540),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),

                  // Data size & Index size breakdown
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          'Data: ${tbl.dataSize}  •  Indexes: ${tbl.indexSize}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF1F5F9),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text(
                          'ACTUAL',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF64748B),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),

                  // Relative Proportion Bar
                  ClipRRect(
                    borderRadius: BorderRadius.circular(999),
                    child: LinearProgressIndicator(
                      value: proportion,
                      backgroundColor: const Color(0xFFF1F5F9),
                      color: const Color(0xFF004E89),
                      minHeight: 4,
                    ),
                  ),
                ],
              ),
            );
          }),

          // View More / Show Less Button
          if (tableStorage.length > 6) ...[
            const SizedBox(height: 4),
            Center(
              child: TextButton.icon(
                onPressed: () {
                  setState(() {
                    if (_visibleCount >= tableStorage.length) {
                      _visibleCount = 6;
                    } else {
                      _visibleCount = (_visibleCount + 6).clamp(6, tableStorage.length);
                    }
                  });
                },
                icon: Icon(
                  _visibleCount >= tableStorage.length
                      ? Icons.expand_less_rounded
                      : Icons.expand_more_rounded,
                  size: 18,
                ),
                label: Text(
                  _visibleCount >= tableStorage.length
                      ? 'Show Less'
                      : 'Show More Tables (${tableStorage.length - _visibleCount} remaining)',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ),
          ],
        ],
      ],
    );
  }
}
