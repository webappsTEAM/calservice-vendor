import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile/features/admin/data/admin_dashboard_api.dart';
import 'package:mobile/features/admin/domain/admin_application.dart';
import 'package:mobile/features/admin/domain/admin_change_request.dart';

/// Repository for Super Admin Applications Approval and review actions.
class SuperAdminApplicationsRepository {
  SuperAdminApplicationsRepository(this._api);

  final AdminDashboardApi _api;

  /// Fetches all platform-wide applications (for Super Admin, returns all tenants).
  Future<List<AdminApplication>> fetchApplications({String? statusFilter}) async {
    final rawList = await _api.fetchApplications(statusFilter: statusFilter);
    return rawList
        .whereType<Map<String, dynamic>>()
        .map(AdminApplication.fromJson)
        .toList();
  }

  /// Fetches full dossier for a specific applicant.
  Future<AdminApplication> fetchApplicationDetail(int id) async {
    final rawJson = await _api.fetchApplicationDetail(id);
    return AdminApplication.fromJson(rawJson);
  }

  /// Approves an application for platform onboarding.
  Future<Map<String, dynamic>> approveApplication(int id) async {
    return _api.approveApplication(id);
  }

  /// Rejects an application with required reason.
  Future<Map<String, dynamic>> rejectApplication(int id, {required String reason}) async {
    return _api.rejectApplication(id, reason: reason);
  }

  /// Requests document/field corrections with required notes.
  Future<Map<String, dynamic>> requestCorrection(int id, {required String notes}) async {
    return _api.requestCorrection(id, notes: notes);
  }

  /// Verifies or rejects a single uploaded document.
  Future<Map<String, dynamic>> verifyDocument({
    required int applicationId,
    required String docCategory,
    required String action,
    String reason = '',
  }) async {
    return _api.verifyDocument(
      applicationId: applicationId,
      docCategory: docCategory,
      action: action,
      reason: reason,
    );
  }

  /// Verifies or rejects multiple uploaded documents in bulk.
  Future<Map<String, dynamic>> bulkVerifyDocuments({
    required int applicationId,
    required List<String> categories,
    required String action,
    String reason = '',
    bool allPending = false,
  }) async {
    return _api.bulkVerifyDocuments(
      applicationId: applicationId,
      categories: categories,
      action: action,
      reason: reason,
      allPending: allPending,
    );
  }

  /// Decides on an individual service authorization.
  Future<Map<String, dynamic>> decideService({
    required int employeeId,
    required int serviceId,
    required String action,
    String reason = '',
  }) async {
    return _api.decideService(
      employeeId: employeeId,
      serviceId: serviceId,
      action: action,
      reason: reason,
    );
  }

  /// Decides on multiple technician services in bulk.
  Future<Map<String, dynamic>> bulkDecideServices({
    required int applicationId,
    required List<int> serviceIds,
    required String action,
    String reason = '',
    bool allPending = false,
  }) async {
    return _api.bulkDecideServices(
      applicationId: applicationId,
      serviceIds: serviceIds,
      action: action,
      reason: reason,
      allPending: allPending,
    );
  }

  /// Fetches pending employee profile change requests across all platform tenants.
  Future<List<AdminChangeRequest>> fetchChangeRequests() async {
    final rawList = await _api.fetchChangeRequests();
    return rawList
        .whereType<Map<String, dynamic>>()
        .map(AdminChangeRequest.fromJson)
        .toList();
  }

  /// Decides on an employee change request (APPROVE / REJECT) with optional admin notes.
  Future<Map<String, dynamic>> decideChangeRequest({
    required int crId,
    required String action,
    String notes = '',
  }) async {
    return _api.decideChangeRequest(
      crId: crId,
      action: action,
      notes: notes,
    );
  }
}

final superAdminApplicationsRepositoryProvider =
    Provider<SuperAdminApplicationsRepository>((ref) {
  return SuperAdminApplicationsRepository(ref.watch(adminDashboardApiProvider));
});
