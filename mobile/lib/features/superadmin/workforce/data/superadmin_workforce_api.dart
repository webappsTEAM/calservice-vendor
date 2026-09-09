import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';

/// API Client for Super Admin Platform Governance Workforce Roster endpoints.
class SuperAdminWorkforceApi {
  SuperAdminWorkforceApi(this._dio);

  final Dio _dio;

  static final _reqOptions = Options(
    receiveTimeout: const Duration(seconds: 30),
    sendTimeout: const Duration(seconds: 30),
  );

  /// Fetches platform-wide workforce list (Solo & Tied workers) with real aggregated counts.
  Future<Map<String, dynamic>> fetchWorkforce({
    String? type,
    int? vendorId,
    String? search,
  }) async {
    final queryParams = <String, dynamic>{};
    if (type != null && type.isNotEmpty && type != 'ALL') {
      queryParams['type'] = type;
    }
    if (vendorId != null && vendorId > 0) {
      queryParams['vendor_id'] = vendorId;
    }
    if (search != null && search.trim().isNotEmpty) {
      queryParams['search'] = search.trim();
    }

    final response = await _dio.get(
      '/workforce/platform/workforce/',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
      options: _reqOptions,
    );

    final data = response.data;
    return data is Map<String, dynamic> ? data : <String, dynamic>{};
  }

  /// Fetches platform-wide technician resignation and relieving requests queue.
  Future<Map<String, dynamic>> fetchRelievingRequests() async {
    final response = await _dio.get(
      '/workforce/platform/relieving-requests/',
      options: _reqOptions,
    );

    final data = response.data;
    return data is Map<String, dynamic> ? data : <String, dynamic>{};
  }

  /// Fetches vendor companies list for vendor filtering and technician assignment.
  Future<Map<String, dynamic>> fetchVendors() async {
    final response = await _dio.get(
      '/workforce/platform/vendors/',
      options: _reqOptions,
    );

    final data = response.data;
    return data is Map<String, dynamic> ? data : <String, dynamic>{};
  }

  /// Directly ties/assigns a Solo Worker to a vendor business.
  Future<Map<String, dynamic>> tieWorker(
    int technicianId, {
    required int vendorId,
    String engagementType = 'PER_JOB',
    String? notes,
  }) async {
    final response = await _dio.post(
      '/workforce/platform/workforce/$technicianId/tie-vendor/',
      data: {
        'vendor_id': vendorId,
        'engagement_type': engagementType,
        if (notes != null && notes.isNotEmpty) 'notes': notes,
      },
      options: _reqOptions,
    );

    final data = response.data;
    return data is Map<String, dynamic> ? data : <String, dynamic>{};
  }

  /// Relieves a tied technician and converts them to an independent Solo Worker.
  Future<Map<String, dynamic>> untieWorker(int technicianId) async {
    final response = await _dio.post(
      '/workforce/platform/workforce/$technicianId/untie-vendor/',
      options: _reqOptions,
    );

    final data = response.data;
    return data is Map<String, dynamic> ? data : <String, dynamic>{};
  }

  /// SEVO Platform Superadmin verifies general job settlement and issues official audit clearance.
  Future<Map<String, dynamic>> approveRelievingRequest(
    int requestId, {
    String auditNotes = 'Verified all platform job commissions and billings have settled.',
  }) async {
    final response = await _dio.post(
      '/workforce/platform/relieving-requests/$requestId/approve/',
      data: {'audit_notes': auditNotes},
      options: _reqOptions,
    );

    final data = response.data;
    return data is Map<String, dynamic> ? data : <String, dynamic>{};
  }
}

final superAdminWorkforceApiProvider = Provider<SuperAdminWorkforceApi>((ref) {
  return SuperAdminWorkforceApi(ref.watch(apiClientProvider));
});
