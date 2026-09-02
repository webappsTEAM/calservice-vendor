import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/features/admin/data/admin_monitoring_api.dart';
import 'package:mobile/features/admin/domain/admin_monitoring.dart';

/// Repository responsible for fetching and parsing database & egress telemetry.
class AdminMonitoringRepository {
  AdminMonitoringRepository(this._api);

  final AdminMonitoringApi _api;

  /// Fetches authoritative database telemetry from the server.
  Future<AdminMonitoringData> getDatabaseTelemetry({
    int page = 1,
    int pageSize = 15,
    String? table,
    String? search,
    String? status,
  }) async {
    final json = await _api.fetchDatabaseTelemetry(
      page: page,
      pageSize: pageSize,
      table: table,
      search: search,
      status: status,
    );
    return AdminMonitoringData.fromJson(json);
  }
}

final adminMonitoringRepositoryProvider = Provider<AdminMonitoringRepository>((ref) {
  final api = ref.watch(adminMonitoringApiProvider);
  return AdminMonitoringRepository(api);
});
