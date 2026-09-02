import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/network/api_client.dart';

/// Low-level HTTP client for Admin Database & Egress Telemetry operations.
class AdminMonitoringApi {
  AdminMonitoringApi(this._dio);

  final Dio _dio;

  static final _options = Options(
    receiveTimeout: const Duration(seconds: 60),
    sendTimeout: const Duration(seconds: 30),
  );

  /// `GET /workforce/admin/database-telemetry/`
  /// Fetches comprehensive live PostgreSQL telemetry, storage analytics,
  /// index scan statistics, active network guardrails, and Supabase WAN egress.
  Future<Map<String, dynamic>> fetchDatabaseTelemetry({
    int page = 1,
    int pageSize = 15,
    String? table,
    String? search,
    String? status,
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
    };
    if (table != null && table.isNotEmpty && table != 'ALL') {
      queryParams['table'] = table;
    }
    if (search != null && search.trim().isNotEmpty) {
      queryParams['search'] = search.trim();
    }
    if (status != null && status.isNotEmpty && status != 'ALL') {
      queryParams['status'] = status;
    }

    final response = await _dio.get(
      '/workforce/admin/database-telemetry/',
      queryParameters: queryParams,
      options: _options,
    );

    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }
}

final adminMonitoringApiProvider = Provider<AdminMonitoringApi>((ref) {
  final dio = ref.watch(apiClientProvider);
  return AdminMonitoringApi(dio);
});
