import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/admin_monitoring.dart';

/// Technical SQL Mode presenting raw PostgreSQL engine statistics,
/// cache hit ratios, and table/index disk measurements.
class TechnicalSqlSection extends StatelessWidget {
  const TechnicalSqlSection({
    super.key,
    required this.data,
  });

  final AdminMonitoringData data;

  @override
  Widget build(BuildContext context) {
    final health = data.databaseHealth;
    final dbCache = health.databaseCacheEfficiency;
    final idxCache = health.indexCacheEfficiency;
    final analytics = data.analytics;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        const Text(
          'Technical Engine & Buffer Telemetry',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w900,
            color: Color(0xFF0A2540),
            letterSpacing: -0.3,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          'Direct PostgreSQL pg_stat_database & pg_statio_user_indexes metrics',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: AppColors.textMuted,
          ),
        ),
        const SizedBox(height: AppSpacing.md),

        // Security Notice Banner
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
              Icon(Icons.shield_outlined, size: 18, color: Color(0xFF1D4ED8)),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Read-only performance audit telemetry. Arbitrary SQL execution, connection strings, and database credentials are intentionally restricted.',
                  style: TextStyle(
                    fontSize: 11.5,
                    color: Color(0xFF1E40AF),
                    height: 1.35,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),

        // Technical Metrics Table / Cards
        _buildTechnicalCard(
          title: 'Database Cache Efficiency (pg_stat_database)',
          rows: [
            MapEntry('Database Engine', health.engine.toUpperCase()),
            MapEntry('Database Disk Size', health.databaseSize),
            MapEntry('Buffer Blocks Hit (blks_hit)', '${dbCache.blocksHit}'),
            MapEntry('Buffer Blocks Read (blks_read)', '${dbCache.blocksRead}'),
            MapEntry('Buffer Hit Ratio', dbCache.formattedRatio),
            MapEntry('Engine Status', dbCache.status),
            MapEntry('Measurement Type', dbCache.measurementType),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),

        _buildTechnicalCard(
          title: 'Index Buffer Cache Hit Ratio (pg_statio_user_indexes)',
          rows: [
            MapEntry('Index Blocks Hit (idx_blks_hit)', '${idxCache.blocksHit}'),
            MapEntry('Index Blocks Read (idx_blks_read)', '${idxCache.blocksRead}'),
            MapEntry('Index Hit Ratio', idxCache.formattedRatio),
            MapEntry('Index Cache Status', idxCache.status),
            MapEntry('Stats Reset Timestamp', health.statsResetTimestamp),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),

        _buildTechnicalCard(
          title: 'Index Scans & Utilization (pg_stat_user_indexes)',
          rows: [
            MapEntry('Total User Indexes', '${analytics.totalIndexes}'),
            MapEntry('Actively Scanned Indexes', '${analytics.usedIndexes}'),
            MapEntry('Zero Scans Recorded', '${analytics.unusedIndexes}'),
            MapEntry('Index Utilization Rate', '${analytics.utilizationRatePercent.toStringAsFixed(1)}%'),
            MapEntry('Billing Telemetry', health.billingCost),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),

        // Top 5 Most Used Indexes
        if (analytics.topUsedIndexes.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Top 5 Actively Scanned Indexes',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0A2540),
                  ),
                ),
                const SizedBox(height: 8),
                ...analytics.topUsedIndexes.map((idx) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            idx.indexName,
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 11.5,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF004E89),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '${idx.cumulativeScans} scans',
                          style: const TextStyle(
                            fontSize: 11.5,
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF059669),
                          ),
                        ),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildTechnicalCard({
    required String title,
    required List<MapEntry<String, String>> rows,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: Color(0xFF0A2540),
            ),
          ),
          const SizedBox(height: 8),
          ...rows.map((r) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      r.key,
                      style: TextStyle(
                        fontSize: 11.5,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    r.value,
                    style: const TextStyle(
                      fontSize: 11.5,
                      fontFamily: 'monospace',
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF0A2540),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
