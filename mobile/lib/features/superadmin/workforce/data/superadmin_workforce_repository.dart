import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/platform_relieving_request.dart';
import '../domain/platform_worker.dart';
import 'superadmin_workforce_api.dart';

/// Aggregated domain data container for the Super Admin Workforce Roster screen.
class PlatformWorkforceOverviewData {
  const PlatformWorkforceOverviewData({
    required this.workers,
    required this.counts,
    required this.relievingRequests,
    required this.pendingSevoAuditCount,
    required this.vendors,
  });

  final List<PlatformWorker> workers;
  final PlatformWorkforceCounts counts;
  final List<PlatformRelievingRequest> relievingRequests;
  final int pendingSevoAuditCount;
  final List<PlatformVendorSummary> vendors;

  int get totalTechnicians => counts.all;
  int get soloWorkersCount => counts.solo;
  int get tiedWorkersCount => counts.tied;

  PlatformWorkforceOverviewData copyWith({
    List<PlatformWorker>? workers,
    PlatformWorkforceCounts? counts,
    List<PlatformRelievingRequest>? relievingRequests,
    int? pendingSevoAuditCount,
    List<PlatformVendorSummary>? vendors,
  }) {
    return PlatformWorkforceOverviewData(
      workers: workers ?? this.workers,
      counts: counts ?? this.counts,
      relievingRequests: relievingRequests ?? this.relievingRequests,
      pendingSevoAuditCount: pendingSevoAuditCount ?? this.pendingSevoAuditCount,
      vendors: vendors ?? this.vendors,
    );
  }
}

/// Repository coordinating Super Admin Platform Workforce Roster live data and operations.
class SuperAdminWorkforceRepository {
  SuperAdminWorkforceRepository(this._api);

  final SuperAdminWorkforceApi _api;

  /// Fetches the complete workforce list and counts.
  Future<PlatformWorkforceResponse> fetchWorkforce({
    String? type,
    int? vendorId,
    String? search,
  }) async {
    final raw = await _api.fetchWorkforce(
      type: type,
      vendorId: vendorId,
      search: search,
    );
    return PlatformWorkforceResponse.fromJson(raw);
  }

  /// Fetches platform relieving and resignation audit requests.
  Future<PlatformRelievingResponse> fetchRelievingRequests() async {
    final raw = await _api.fetchRelievingRequests();
    return PlatformRelievingResponse.fromJson(raw);
  }

  /// Fetches registered vendor companies.
  Future<List<PlatformVendorSummary>> fetchVendors() async {
    final raw = await _api.fetchVendors();
    final list = raw['vendors'];
    if (list is List) {
      return list
          .whereType<Map<String, dynamic>>()
          .map(PlatformVendorSummary.fromJson)
          .toList();
    }
    return <PlatformVendorSummary>[];
  }

  /// Concurrently fetches live workforce, relieving audits, and vendor list.
  Future<PlatformWorkforceOverviewData> fetchOverview({
    String? type,
    int? vendorId,
    String? search,
  }) async {
    final results = await Future.wait([
      fetchWorkforce(type: type, vendorId: vendorId, search: search),
      fetchRelievingRequests().catchError(
        (_) => const PlatformRelievingResponse(
          relievingRequests: [],
          totalCount: 0,
          pendingSevoCount: 0,
        ),
      ),
      fetchVendors().catchError((_) => <PlatformVendorSummary>[]),
    ]);

    final workforceResp = results[0] as PlatformWorkforceResponse;
    final relievingResp = results[1] as PlatformRelievingResponse;
    final vendors = results[2] as List<PlatformVendorSummary>;

    return PlatformWorkforceOverviewData(
      workers: workforceResp.workers,
      counts: workforceResp.counts,
      relievingRequests: relievingResp.relievingRequests,
      pendingSevoAuditCount: relievingResp.pendingSevoCount,
      vendors: vendors,
    );
  }

  /// Directly ties/assigns a Solo Worker to a vendor company.
  Future<Map<String, dynamic>> tieWorker(
    int technicianId, {
    required int vendorId,
    String engagementType = 'PER_JOB',
    String? notes,
  }) async {
    return _api.tieWorker(
      technicianId,
      vendorId: vendorId,
      engagementType: engagementType,
      notes: notes,
    );
  }

  /// Relieves a tied technician and converts them to a Solo Worker.
  Future<Map<String, dynamic>> untieWorker(int technicianId) async {
    return _api.untieWorker(technicianId);
  }

  /// Issues official SEVO platform relieving clearance and approval.
  Future<Map<String, dynamic>> approveRelievingRequest(
    int requestId, {
    String auditNotes = 'Verified all platform job commissions and billings have settled.',
  }) async {
    return _api.approveRelievingRequest(requestId, auditNotes: auditNotes);
  }
}

final superAdminWorkforceRepositoryProvider =
    Provider<SuperAdminWorkforceRepository>((ref) {
  return SuperAdminWorkforceRepository(
    ref.watch(superAdminWorkforceApiProvider),
  );
});
