import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';

/// API client for Super Admin Platform Governance Vendor Directory endpoints.
class SuperAdminVendorApi {
  SuperAdminVendorApi(this._dio);

  final Dio _dio;

  static final _reqOptions = Options(
    receiveTimeout: const Duration(seconds: 30),
    sendTimeout: const Duration(seconds: 30),
  );

  /// Fetches all registered vendor companies on the SEVO platform.
  Future<Map<String, dynamic>> fetchVendors() async {
    final response = await _dio.get(
      '/workforce/platform/vendors/',
      options: _reqOptions,
    );

    final data = response.data;
    return data is Map<String, dynamic> ? data : <String, dynamic>{};
  }
}

final superAdminVendorApiProvider = Provider<SuperAdminVendorApi>((ref) {
  return SuperAdminVendorApi(ref.watch(apiClientProvider));
});
