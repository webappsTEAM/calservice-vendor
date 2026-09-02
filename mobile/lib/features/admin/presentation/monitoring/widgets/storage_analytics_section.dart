import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/admin_monitoring.dart';

/// Storage Analytics breakdown showing where database disk space is allocated.
class StorageAnalyticsSection extends StatelessWidget {
  const StorageAnalyticsSection({
    super.key,
    required this.data,
  });

  final AdminMonitoringData data;

  String _formatBytes(int bytes) {
    if (bytes <= 0) return '0 B';
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
  }

  @override
  Widget build(BuildContext context) {
    final analytics = data.analytics;
    final totalBytes = analytics.totalCategoryBytes;
    final dbSize = data.databaseHealth.databaseSize.isNotEmpty
        ? data.databaseHealth.databaseSize
        : (totalBytes > 0 ? _formatBytes(totalBytes) : '170 MB');

    final categories = [
      _StorageCategoryItem(
        label: 'Audit Logs',
        rawKey: 'Logs & Audit History',
        color: const Color(0xFF004E89),
        icon: Icons.history_edu_rounded,
        bytes: analytics.categoryStorageBytes['Logs & Audit History'] ?? 0,
        totalBytes: totalBytes,
      ),
      _StorageCategoryItem(
        label: 'Notifications',
        rawKey: 'Notifications & Messaging',
        color: const Color(0xFF0284C7),
        icon: Icons.notifications_active_rounded,
        bytes: analytics.categoryStorageBytes['Notifications & Messaging'] ?? 0,
        totalBytes: totalBytes,
      ),
      _StorageCategoryItem(
        label: 'Workforce',
        rawKey: 'Core Workforce & Personnel',
        color: const Color(0xFF059669),
        icon: Icons.badge_rounded,
        bytes: analytics.categoryStorageBytes['Core Workforce & Personnel'] ?? 0,
        totalBytes: totalBytes,
      ),
      _StorageCategoryItem(
        label: 'Job Requests',
        rawKey: 'Jobs & Service Requests',
        color: const Color(0xFFD97706),
        icon: Icons.handyman_rounded,
        bytes: analytics.categoryStorageBytes['Jobs & Service Requests'] ?? 0,
        totalBytes: totalBytes,
      ),
      _StorageCategoryItem(
        label: 'Financials',
        rawKey: 'Financial & Billing',
        color: const Color(0xFF6366F1),
        icon: Icons.payments_rounded,
        bytes: analytics.categoryStorageBytes['Financial & Billing'] ?? 0,
        totalBytes: totalBytes,
      ),
      _StorageCategoryItem(
        label: 'System Tables',
        rawKey: 'Other System Tables',
        color: const Color(0xFF64748B),
        icon: Icons.table_chart_rounded,
        bytes: analytics.categoryStorageBytes['Other System Tables'] ?? 0,
        totalBytes: totalBytes,
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section Header
        const Text(
          'Where is my Database Space Being Used?',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w900,
            color: Color(0xFF0A2540),
            letterSpacing: -0.3,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          'Storage Analytics',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: AppColors.textMuted,
          ),
        ),
        const SizedBox(height: AppSpacing.md),

        // Total Database Footprint Card
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF004E89).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.pie_chart_rounded, size: 20, color: Color(0xFF004E89)),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Total Database Footprint',
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      dbSize,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w900,
                        color: Color(0xFF0A2540),
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFF059669).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: const Text(
                  'PostgreSQL',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF059669),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.sm),

        // Category Cards List
        if (analytics.categoryStorageBytes.isEmpty)
          Container(
            padding: const EdgeInsets.all(AppSpacing.lg),
            alignment: Alignment.center,
            child: Text(
              'No storage telemetry available.',
              style: TextStyle(fontSize: 13, color: AppColors.textMuted),
            ),
          )
        else
          ...categories.map((cat) {
            final pct = totalBytes > 0 ? (cat.bytes / totalBytes * 100).round() : 0;
            final formattedSize = _formatBytes(cat.bytes);

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
                      Icon(cat.icon, size: 16, color: cat.color),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          cat.label,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF0A2540),
                          ),
                        ),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        formattedSize,
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w900,
                          fontFamily: 'monospace',
                          color: Color(0xFF0A2540),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '$pct% storage',
                        style: TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(999),
                    child: LinearProgressIndicator(
                      value: totalBytes > 0 ? (cat.bytes / totalBytes).clamp(0.0, 1.0) : 0.0,
                      backgroundColor: const Color(0xFFF1F5F9),
                      color: cat.color,
                      minHeight: 5,
                    ),
                  ),
                ],
              ),
            );
          }),
      ],
    );
  }
}

class _StorageCategoryItem {
  const _StorageCategoryItem({
    required this.label,
    required this.rawKey,
    required this.color,
    required this.icon,
    required this.bytes,
    required this.totalBytes,
  });

  final String label;
  final String rawKey;
  final Color color;
  final IconData icon;
  final int bytes;
  final int totalBytes;
}
