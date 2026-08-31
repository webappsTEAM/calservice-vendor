import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/features/admin/data/admin_monitoring_repository.dart';
import 'package:mobile/features/admin/domain/admin_monitoring.dart';

/// Display mode for the monitoring screen.
enum MonitoringViewMode {
  plainEnglish,
  technicalSql,
}

/// Filter state for database index querying.
@immutable
class AdminMonitoringFilter {
  const AdminMonitoringFilter({
    this.page = 1,
    this.pageSize = 15,
    this.table = 'ALL',
    this.search = '',
    this.status = 'ALL',
  });

  final int page;
  final int pageSize;
  final String table;
  final String search;
  final String status;

  AdminMonitoringFilter copyWith({
    int? page,
    int? pageSize,
    String? table,
    String? search,
    String? status,
  }) {
    return AdminMonitoringFilter(
      page: page ?? this.page,
      pageSize: pageSize ?? this.pageSize,
      table: table ?? this.table,
      search: search ?? this.search,
      status: status ?? this.status,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AdminMonitoringFilter &&
          runtimeType == other.runtimeType &&
          page == other.page &&
          pageSize == other.pageSize &&
          table == other.table &&
          search == other.search &&
          status == other.status;

  @override
  int get hashCode => Object.hash(page, pageSize, table, search, status);
}

/// Filter state provider.
final adminMonitoringFilterProvider = StateProvider<AdminMonitoringFilter>((ref) {
  return const AdminMonitoringFilter();
});

/// Current view mode provider (Plain English vs Technical SQL).
final adminMonitoringViewModeProvider = StateProvider<MonitoringViewMode>((ref) {
  return MonitoringViewMode.plainEnglish;
});

/// Auto-refresh enabled provider (60s timer).
final adminMonitoringAutoRefreshProvider = StateProvider<bool>((ref) {
  return true;
});

/// Last updated timestamp provider.
final adminMonitoringLastUpdatedProvider = StateProvider<DateTime?>((ref) {
  return null;
});

/// Primary future provider delivering live database & egress telemetry.
final adminMonitoringDataProvider = FutureProvider<AdminMonitoringData>((ref) async {
  final repo = ref.watch(adminMonitoringRepositoryProvider);
  final filter = ref.watch(adminMonitoringFilterProvider);

  final data = await repo.getDatabaseTelemetry(
    page: filter.page,
    pageSize: filter.pageSize,
    table: filter.table,
    search: filter.search,
    status: filter.status,
  );

  // Update last updated timestamp
  ref.read(adminMonitoringLastUpdatedProvider.notifier).state = DateTime.now();

  return data;
});
