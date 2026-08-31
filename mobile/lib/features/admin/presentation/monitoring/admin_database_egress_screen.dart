import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/presentation/widgets/admin_drawer.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';
import 'admin_monitoring_providers.dart';
import 'widgets/executive_summary_section.dart';
import 'widgets/index_performance_section.dart';
import 'widgets/network_guardrails_section.dart';
import 'widgets/storage_analytics_section.dart';
import 'widgets/supabase_egress_section.dart';
import 'widgets/table_storage_section.dart';
import 'widgets/technical_sql_section.dart';

/// Admin Database & Egress Monitoring dashboard.
///
/// Features:
/// - Screen title: Database & Egress Monitoring
/// - Status indicator: Live Telemetry
/// - Subtitle: Plain-English performance analytics, search shortcut usage, storage health, and network egress optimizations.
/// - Two display modes: Plain English (default) & Technical SQL.
/// - Auto-refresh (60s) paused when screen is disposed or backgrounded.
/// - Last updated timestamp & manual refresh with duplicate prevention.
/// - Executive summary, storage breakdown, index scans, network guardrails, Supabase egress.
class AdminDatabaseEgressScreen extends ConsumerStatefulWidget {
  const AdminDatabaseEgressScreen({super.key});

  @override
  ConsumerState<AdminDatabaseEgressScreen> createState() => _AdminDatabaseEgressScreenState();
}

class _AdminDatabaseEgressScreenState extends ConsumerState<AdminDatabaseEgressScreen>
    with WidgetsBindingObserver {
  Timer? _autoRefreshTimer;
  bool _isRefreshing = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _startAutoRefreshTimer();
  }

  @override
  void dispose() {
    _stopAutoRefreshTimer();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _startAutoRefreshTimer();
    } else {
      _stopAutoRefreshTimer();
    }
  }

  void _startAutoRefreshTimer() {
    _autoRefreshTimer?.cancel();
    _autoRefreshTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      final autoRefreshEnabled = ref.read(adminMonitoringAutoRefreshProvider);
      if (autoRefreshEnabled && mounted && !_isRefreshing) {
        _handleRefresh(silent: true);
      }
    });
  }

  void _stopAutoRefreshTimer() {
    _autoRefreshTimer?.cancel();
    _autoRefreshTimer = null;
  }

  Future<void> _handleRefresh({bool silent = false}) async {
    if (_isRefreshing) return;

    if (!silent) {
      setState(() => _isRefreshing = true);
    }

    try {
      ref.invalidate(adminMonitoringDataProvider);
      await ref.read(adminMonitoringDataProvider.future);
    } catch (_) {
    } finally {
      if (mounted && !silent) {
        setState(() => _isRefreshing = false);
      }
    }
  }

  String _formatLastUpdated(DateTime? dt) {
    if (dt == null) return 'Never';
    final hour = dt.hour > 12 ? dt.hour - 12 : (dt.hour == 0 ? 12 : dt.hour);
    final min = dt.minute.toString().padLeft(2, '0');
    final ampm = dt.hour >= 12 ? 'PM' : 'AM';
    return '$hour:$min $ampm';
  }

  @override
  Widget build(BuildContext context) {
    final telemetryAsync = ref.watch(adminMonitoringDataProvider);
    final viewMode = ref.watch(adminMonitoringViewModeProvider);
    final autoRefresh = ref.watch(adminMonitoringAutoRefreshProvider);
    final lastUpdated = ref.watch(adminMonitoringLastUpdatedProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: const WorkforceAppBar(
        titleText: 'Database & Egress Monitoring',
        showBrand: false,
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: RefreshIndicator(
        onRefresh: () => _handleRefresh(silent: false),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.md,
            AppSpacing.md,
            AppSpacing.md,
            AppSpacing.xxl,
          ),
          children: [
            // ── Screen Header Card ──────────────────────────────────────────
            Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE2E8F0)),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x040A2540),
                    blurRadius: 4,
                    offset: Offset(0, 1.5),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title Row with Live Status Indicator
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        child: const Text(
                          'Database & Egress Monitoring',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                            color: Color(0xFF0A2540),
                            letterSpacing: -0.4,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      // Live Telemetry Badge
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3.5),
                        decoration: BoxDecoration(
                          color: const Color(0xFFECFDF5),
                          borderRadius: BorderRadius.circular(999),
                          border: Border.all(color: const Color(0xFFA7F3D0)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 6,
                              height: 6,
                              decoration: const BoxDecoration(
                                color: Color(0xFF059669),
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 5),
                            const Text(
                              'Live Telemetry',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF065F46),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),

                  // Subtitle
                  Text(
                    'Plain-English performance analytics, search shortcut usage, storage health, and network egress optimizations.',
                    style: TextStyle(
                      fontSize: 12,
                      color: AppColors.textMuted,
                      height: 1.35,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  const Divider(height: 1, color: Color(0xFFE2E8F0)),
                  const SizedBox(height: AppSpacing.sm),

                  // Metadata & Actions Bar: Last updated, Auto-refresh toggle, Manual refresh
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Last updated & auto-refresh label
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.schedule_rounded, size: 12, color: Color(0xFF64748B)),
                                const SizedBox(width: 4),
                                Expanded(
                                  child: Text(
                                    'Updated ${_formatLastUpdated(lastUpdated)}',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w600,
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            InkWell(
                              onTap: () {
                                ref.read(adminMonitoringAutoRefreshProvider.notifier).state =
                                    !autoRefresh;
                              },
                              borderRadius: BorderRadius.circular(4),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    autoRefresh ? Icons.sync_rounded : Icons.sync_disabled_rounded,
                                    size: 12,
                                    color: autoRefresh ? const Color(0xFF059669) : const Color(0xFF94A3B8),
                                  ),
                                  const SizedBox(width: 4),
                                  Flexible(
                                    child: Text(
                                      autoRefresh ? 'Auto-refresh (60s)' : 'Auto-refresh off',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontSize: 10.5,
                                        fontWeight: FontWeight.w700,
                                        color: autoRefresh ? const Color(0xFF059669) : const Color(0xFF94A3B8),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),

                      // Manual Refresh Button
                      OutlinedButton.icon(
                        onPressed: _isRefreshing ? null : () => _handleRefresh(silent: false),
                        icon: _isRefreshing
                            ? const SizedBox(
                                width: 12,
                                height: 12,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.refresh_rounded, size: 14),
                        label: const Text('Refresh', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.sm),

                  // ── Display Mode Selector ──────────────────────────────
                  SegmentedButton<MonitoringViewMode>(
                    segments: const [
                      ButtonSegment(
                        value: MonitoringViewMode.plainEnglish,
                        label: Text('Plain English'),
                        icon: Icon(Icons.translate_rounded, size: 16),
                      ),
                      ButtonSegment(
                        value: MonitoringViewMode.technicalSql,
                        label: Text('Technical SQL'),
                        icon: Icon(Icons.terminal_rounded, size: 16),
                      ),
                    ],
                    selected: {viewMode},
                    onSelectionChanged: (set) {
                      ref.read(adminMonitoringViewModeProvider.notifier).state = set.first;
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            // ── Async Content Section ───────────────────────────────────────
            telemetryAsync.when(
              loading: () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(AppSpacing.xxl),
                  child: CircularProgressIndicator(),
                ),
              ),
              error: (err, stack) {
                debugPrint('DatabaseEgressScreen Telemetry Error: $err\n$stack');
                String detail = err.toString();
                if (err is DioException) {
                  final status = err.response?.statusCode;
                  final data = err.response?.data;
                  detail = 'HTTP ${status ?? err.type}: ${data ?? err.message}';
                }

                return Container(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFFECDD3)),
                  ),
                  child: Column(
                    children: [
                      const Icon(Icons.error_outline_rounded, size: 40, color: Color(0xFFE11D48)),
                      const SizedBox(height: AppSpacing.md),
                      const Text(
                        'Monitoring data unavailable',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Live database telemetry is not currently accessible to the mobile application or the service is temporarily offline.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: SelectableText(
                          detail,
                          style: const TextStyle(
                            fontSize: 11,
                            fontFamily: 'monospace',
                            color: Color(0xFFE11D48),
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.md),
                      FilledButton.icon(
                        onPressed: () => _handleRefresh(silent: false),
                        icon: const Icon(Icons.refresh_rounded, size: 16),
                        label: const Text('Retry'),
                        style: FilledButton.styleFrom(backgroundColor: const Color(0xFF004E89)),
                      ),
                    ],
                  ),
                );
              },
              data: (data) {
                if (viewMode == MonitoringViewMode.plainEnglish) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // 1. Executive System Summary (5 Responsive Cards)
                      ExecutiveSummarySection(data: data),
                      const SizedBox(height: AppSpacing.xl),

                      // 2. Storage Analytics Breakdown
                      StorageAnalyticsSection(data: data),
                      const SizedBox(height: AppSpacing.xl),

                      // 3. Database Search Shortcuts (Index scans, search, filters)
                      IndexPerformanceSection(data: data),
                      const SizedBox(height: AppSpacing.xl),

                      // 4. Detailed Table Storage Ranked
                      TableStorageSection(data: data),
                      const SizedBox(height: AppSpacing.xl),

                      // 5. Network Guardrails & Optimizations
                      NetworkGuardrailsSection(data: data),
                      const SizedBox(height: AppSpacing.xl),

                      // 6. Supabase Platform Egress
                      SupabaseEgressSection(data: data),
                    ],
                  );
                } else {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Technical SQL View
                      TechnicalSqlSection(data: data),
                      const SizedBox(height: AppSpacing.xl),

                      // Index Scans with Technical Columns
                      IndexPerformanceSection(data: data),
                      const SizedBox(height: AppSpacing.xl),

                      // Detailed Table Storage
                      TableStorageSection(data: data),
                    ],
                  );
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}
