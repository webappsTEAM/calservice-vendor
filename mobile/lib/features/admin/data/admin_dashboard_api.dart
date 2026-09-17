import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

/// Comprehensive API client for all Admin Operations & Workforce endpoints.
class AdminDashboardApi {
  AdminDashboardApi(this._dio);

  final Dio _dio;

  static final _adminReqOptions = Options(
    receiveTimeout: const Duration(seconds: 30),
    sendTimeout: const Duration(seconds: 30),
  );

  /// Admin list endpoints backed by `GET /workforce/jobs/` are measurably
  /// slower than the rest of the API: that view's admin branch serializes up
  /// to 50 ServiceRequests without the bulk-prefetch context its employee
  /// branch builds, so every computed field (payment, extensions, customer)
  /// falls back to per-row queries. Measured against production on-device:
  /// 39.3s for a 75 KB / 50-item response.
  ///
  /// This longer budget is a MITIGATION so the screen can complete at all —
  /// it is not a fix. The real fix is server-side (mirror the employee
  /// branch's select_related + bulk maps for admins, and/or paginate).
  static final _adminSlowListOptions = Options(
    receiveTimeout: const Duration(seconds: 60),
    sendTimeout: const Duration(seconds: 30),
  );

  /// Fetches applicant/technician dossiers.
  Future<List<dynamic>> fetchApplications({String? statusFilter}) async {
    final response = await _dio.get(
      '/workforce/admin/applications/',
      queryParameters: statusFilter != null && statusFilter.isNotEmpty
          ? {'status': statusFilter}
          : null,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Fetches application detailed dossier for a single applicant.
  Future<Map<String, dynamic>> fetchApplicationDetail(int id) async {
    final response = await _dio.get(
      '/workforce/admin/applications/$id/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Approves an applicant's dossier.
  Future<Map<String, dynamic>> approveApplication(int id) async {
    final response = await _dio.post(
      '/workforce/admin/applications/$id/approve/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Rejects an applicant's dossier.
  Future<Map<String, dynamic>> rejectApplication(int id, {String reason = ''}) async {
    final response = await _dio.post(
      '/workforce/admin/applications/$id/reject/',
      data: {'reason': reason},
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Requests correction for an applicant's dossier.
  Future<Map<String, dynamic>> requestCorrection(int id, {required String notes}) async {
    final response = await _dio.post(
      '/workforce/admin/applications/$id/request-correction/',
      data: {'notes': notes},
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Fetches pending profile change requests.
  Future<List<dynamic>> fetchChangeRequests() async {
    final response = await _dio.get(
      '/workforce/admin/change-requests/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Decides on an employee change request (approve / reject).
  Future<Map<String, dynamic>> decideChangeRequest({
    required int crId,
    required String action,
    String notes = '',
  }) async {
    final response = await _dio.post(
      '/workforce/admin/change-requests/$crId/decide/',
      data: {'action': action, 'notes': notes},
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Fetches master skills catalog.
  Future<List<dynamic>> fetchSkills() async {
    final response = await _dio.get(
      '/workforce/skills/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Creates a new skill in the catalog.
  Future<Map<String, dynamic>> createSkill({
    required String name,
    required String category,
    String? description,
  }) async {
    final response = await _dio.post(
      '/workforce/skills/',
      data: {
        'name': name,
        'category': category,
        if (description != null && description.isNotEmpty)
          'description': description,
      },
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Assigns a skill to an employee.
  Future<Map<String, dynamic>> assignSkill({
    required int employeeId,
    required int skillId,
    String proficiencyLevel = 'INTERMEDIATE',
  }) async {
    final response = await _dio.post(
      '/workforce/skills/employee/$employeeId/',
      data: {
        'skill_id': skillId,
        'proficiency_level': proficiencyLevel,
        'action': 'assign',
      },
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Fetches workforce operations jobs.
  Future<List<dynamic>> fetchJobs({String? statusFilter}) async {
    final response = await _dio.get(
      '/workforce/jobs/',
      queryParameters: statusFilter != null && statusFilter.isNotEmpty
          ? {'status': statusFilter}
          : null,
      options: _adminSlowListOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Fetches fleet presence and telemetry.
  Future<List<dynamic>> fetchFleetMap() async {
    final response = await _dio.get(
      '/workforce/presence/fleet-map/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Fetches eligible technicians for a given job.
  Future<List<dynamic>> fetchEligibleTechnicians({
    required int jobId,
    double? radiusKm,
    String? service,
  }) async {
    final params = <String, dynamic>{
      'job_id': jobId,
      'radius_km': ?radiusKm,
      if (service != null && service.isNotEmpty) 'service': service,
    };
    final response = await _dio.get(
      '/workforce/dispatch/eligible-technicians/',
      queryParameters: params,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Manually assigns a technician to a job.
  Future<Map<String, dynamic>> assignTechnician({
    required int jobId,
    required int employeeId,
  }) async {
    final response = await _dio.post(
      '/workforce/dispatch/assign/',
      data: {
        'job_id': jobId,
        'employee_id': employeeId,
      },
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Triggers automatic geo-dispatch for a job.
  Future<Map<String, dynamic>> triggerAutoDispatch(int jobId) async {
    final response = await _dio.post(
      '/workforce/dispatch/auto-dispatch/$jobId/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Fetches pending technician scope extensions awaiting admin review.
  Future<List<dynamic>> fetchPendingExtensions() async {
    final response = await _dio.get(
      '/workforce/admin/extensions/pending/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Decides on a pending work extension (APPROVED / REJECTED).
  Future<Map<String, dynamic>> decideExtension({
    required int jobId,
    required int extId,
    required String action,
    String reason = '',
    double? approvedAmount,
  }) async {
    final payload = <String, dynamic>{
      'action': action,
      'reason': reason,
      'approved_amount': ?approvedAmount,
    };
    final response = await _dio.post(
      '/workforce/admin/jobs/$jobId/extension/$extId/decide/',
      data: payload,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Fetches pending service authorization requests from technicians.
  Future<List<dynamic>> fetchPendingServices() async {
    final response = await _dio.get(
      '/workforce/admin/services/pending-requests/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Decides on a technician service request (approve / reject).
  Future<Map<String, dynamic>> decideService({
    required int employeeId,
    required int serviceId,
    required String action,
    String reason = '',
  }) async {
    final response = await _dio.post(
      '/workforce/admin/applications/$employeeId/service/$serviceId/decide/',
      data: {'action': action, 'reason': reason},
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Decides on multiple technician services in bulk (approve / reject).
  Future<Map<String, dynamic>> bulkDecideServices({
    required int applicationId,
    required List<int> serviceIds,
    required String action,
    String reason = '',
    bool allPending = false,
  }) async {
    final response = await _dio.post(
      '/workforce/admin/applications/$applicationId/services/bulk-decide/',
      data: {
        'service_ids': serviceIds,
        'action': action,
        'reason': reason,
        'all_pending': allPending,
      },
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Verifies or rejects a single uploaded document in an applicant's dossier.
  Future<Map<String, dynamic>> verifyDocument({
    required int applicationId,
    required String docCategory,
    required String action,
    String reason = '',
  }) async {
    final response = await _dio.post(
      '/workforce/admin/applications/$applicationId/document/$docCategory/verify/',
      data: {'action': action, 'reason': reason},
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Verifies or rejects multiple uploaded documents in bulk.
  Future<Map<String, dynamic>> bulkVerifyDocuments({
    required int applicationId,
    required List<String> categories,
    required String action,
    String reason = '',
    bool allPending = false,
  }) async {
    final response = await _dio.post(
      '/workforce/admin/applications/$applicationId/documents/bulk-verify/',
      data: {
        'categories': categories,
        'action': action,
        'reason': reason,
        'all_pending': allPending,
      },
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Fetches company authorized locations & geofences.
  Future<List<dynamic>> fetchLocations() async {
    final response = await _dio.get(
      '/workforce/time-tracking/locations/',
      options: _adminReqOptions,
    );
    final data = response.data;
    if (data is List) return data;
    if (data is Map<String, dynamic> && data['results'] is List) {
      return data['results'] as List;
    }
    return const [];
  }

  /// Creates a new authorized location.
  Future<Map<String, dynamic>> createLocation(Map<String, dynamic> payload) async {
    final response = await _dio.post(
      '/workforce/time-tracking/locations/',
      data: payload,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Updates an authorized location.
  Future<Map<String, dynamic>> updateLocation(
    int id,
    Map<String, dynamic> payload,
  ) async {
    final response = await _dio.patch(
      '/workforce/time-tracking/locations/$id/',
      data: payload,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Deletes an authorized location.
  Future<void> deleteLocation(int id) async {
    await _dio.delete(
      '/workforce/time-tracking/locations/$id/',
      options: _adminReqOptions,
    );
  }

  /// Toggles an authorized location active / inactive.
  Future<Map<String, dynamic>> toggleLocationActive(int id, bool isActive) async {
    return updateLocation(id, {'is_active': isActive});
  }

  /// Fetches observable correlated lifecycle timeline for a job.
  Future<Map<String, dynamic>> fetchJobTimeline(int jobId) async {
    final response = await _dio.get(
      '/workforce/jobs/$jobId/timeline/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Fetches dynamic aggregation reports.
  Future<Map<String, dynamic>> fetchReport({
    required String type,
    Map<String, dynamic>? queryParams,
  }) async {
    final params = <String, dynamic>{
      'type': type,
      ...?queryParams,
    };
    final response = await _dio.get(
      '/workforce/reports/',
      queryParameters: params,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  // ── Quotation Approvals & Pre-Send Review ───────────────────────────────────

  /// Fetches quotations awaiting SEVO approval after customer acceptance.
  Future<List<dynamic>> fetchQuotesPendingApproval({String? companyId}) async {
    final response = await _dio.get(
      '/workforce/quotes/pending-approval/',
      queryParameters: companyId != null && companyId.isNotEmpty
          ? {'company_id': companyId}
          : null,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Fetches quotations held for high-value / structural pre-send review.
  Future<List<dynamic>> fetchQuotesPendingReview() async {
    final response = await _dio.get(
      '/workforce/quotes/pending-review/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Decides on an accepted quotation awaiting SEVO admin approval.
  Future<Map<String, dynamic>> adminReviewQuote(
    int quoteId, {
    required String action,
    String notes = '',
    String reason = '',
  }) async {
    final response = await _dio.post(
      '/workforce/quotes/$quoteId/admin-review/',
      data: {
        'action': action,
        'notes': notes,
        'reason': reason,
      },
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Releases (and sends) or rejects a quote held before sending.
  Future<Map<String, dynamic>> preSendReviewQuote(
    int quoteId, {
    required String action,
    String notes = '',
    String reason = '',
  }) async {
    final response = await _dio.post(
      '/workforce/quotes/$quoteId/pre-send-review/',
      data: {
        'action': action,
        'notes': notes,
        'reason': reason,
      },
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  // ── Commercial Invoices ─────────────────────────────────────────────────────

  /// Fetches commercial invoices scoped to the caller.
  Future<List<dynamic>> fetchInvoices({
    String? search,
    String? status,
  }) async {
    final params = <String, dynamic>{
      if (search != null && search.isNotEmpty) 'search': search,
      if (status != null && status.isNotEmpty) 'status': status,
    };
    final response = await _dio.get(
      '/workforce/invoices/',
      queryParameters: params.isNotEmpty ? params : null,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Fetches detailed invoice breakdown by ID.
  Future<Map<String, dynamic>> fetchInvoiceDetail(int id) async {
    final response = await _dio.get(
      '/workforce/invoices/$id/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Records a manual or offline payment against an invoice.
  Future<Map<String, dynamic>> recordInvoicePayment(
    int id, {
    required double amount,
    required String method,
    String reference = '',
  }) async {
    final response = await _dio.post(
      '/workforce/invoices/$id/payments/',
      data: {
        'amount': amount,
        'method': method,
        'reference': reference,
      },
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  // ── Pricing Policies ────────────────────────────────────────────────────────

  /// Fetches service category commercial pricing & approval policies.
  Future<List<dynamic>> fetchPricingPolicies() async {
    final response = await _dio.get(
      '/workforce/settings/pricing-policies/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is List ? data : const [];
  }

  /// Updates an existing service category commercial pricing policy.
  Future<Map<String, dynamic>> updatePricingPolicy(
    int id,
    Map<String, dynamic> payload,
  ) async {
    final response = await _dio.patch(
      '/workforce/settings/pricing-policies/$id/',
      data: payload,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  // ── Workforce Scorecards ───────────────────────────────────────────────────

  /// Fetches worker & provider scorecards across the workforce.
  Future<Map<String, dynamic>> fetchAdminScorecards() async {
    final response = await _dio.get(
      '/workforce/admin/scorecards/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  // ── Social Security Code Registrations ─────────────────────────────────────

  /// Fetches individual worker Social Security compliance registration records.
  Future<Map<String, dynamic>> fetchSocialSecurityRegistrations({
    String? status,
  }) async {
    final params = <String, dynamic>{
      if (status != null && status.isNotEmpty) 'status': status,
    };
    final response = await _dio.get(
      '/workforce/admin/social-security/',
      queryParameters: params.isNotEmpty ? params : null,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Records that an administrator has manually completed the Shram Suvidha portal submission.
  Future<Map<String, dynamic>> markSocialSecurityRegistered({
    required int registrationId,
    required String portalReferenceId,
  }) async {
    final response = await _dio.post(
      '/workforce/admin/social-security/mark-registered/',
      data: {
        'registration_id': registrationId,
        'portal_reference_id': portalReferenceId,
      },
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Vendor Network: Lists and filters all technicians in this vendor's network.
  Future<Map<String, dynamic>> fetchVendorNetwork({
    String? status,
    String? search,
  }) async {
    final queryParams = <String, dynamic>{};
    if (status != null && status.isNotEmpty && status != 'ALL') {
      queryParams['status'] = status;
    }
    if (search != null && search.isNotEmpty) {
      queryParams['search'] = search;
    }

    final response = await _dio.get(
      '/workforce/vendor/network/',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Updates vendor-technician relationship status (e.g. SUSPEND, ACTIVATE, TERMINATE).
  Future<Map<String, dynamic>> updateVendorTechnicianStatus({
    required int relationshipId,
    required String action,
  }) async {
    final response = await _dio.post(
      '/workforce/vendor/network/$relationshipId/status/',
      data: {'action': action},
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Vendor Invitations: Lists sent invitations for this vendor.
  Future<Map<String, dynamic>> fetchVendorInvitations({String? status}) async {
    final queryParams = <String, dynamic>{};
    if (status != null && status.isNotEmpty && status != 'ALL') {
      queryParams['status'] = status;
    }

    final response = await _dio.get(
      '/workforce/vendor/invitations/',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Creates and sends a new invitation to a technician email.
  Future<Map<String, dynamic>> createVendorInvitation({
    required String invitedEmail,
    String message = '',
    String channel = 'DIRECT_EMAIL',
  }) async {
    final response = await _dio.post(
      '/workforce/vendor/invitations/',
      data: {
        'invited_email': invitedEmail,
        'message': message,
        'channel': channel,
      },
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Cancels a pending vendor invitation.
  Future<Map<String, dynamic>> cancelVendorInvitation(int invitationId) async {
    final response = await _dio.post(
      '/workforce/vendor/invitations/$invitationId/cancel/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }

  /// Provider Profile: Fetches authenticated service provider organization details.
  Future<Map<String, dynamic>> fetchProviderProfile() async {
    final response = await _dio.get(
      '/workforce/provider/profile/',
      options: _adminReqOptions,
    );
    final data = response.data;
    return data is Map<String, dynamic> ? data : const <String, dynamic>{};
  }
}

final adminDashboardApiProvider = Provider<AdminDashboardApi>((ref) {
  return AdminDashboardApi(ref.watch(apiClientProvider));
});


