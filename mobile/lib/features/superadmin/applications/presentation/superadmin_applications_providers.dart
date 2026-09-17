import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/superadmin_applications_repository.dart';
import '../domain/platform_application.dart';

/// Currently selected top-level section in Super Admin Applications Approval.
final superAdminSelectedSectionProvider =
    StateProvider<SuperAdminApplicationsSection>((ref) {
  return SuperAdminApplicationsSection.onboardingApplications;
});

/// Currently selected status filter tab on Super Admin Applications Approval screen.
final applicationStatusFilterProvider =
    StateProvider<PlatformApplicationStatusFilter>((ref) {
  return PlatformApplicationStatusFilter.all;
});

/// Search term filter for technician name, ID, email, or mobile number.
final applicationSearchQueryProvider = StateProvider<String>((ref) => '');

/// Fetches live platform applications from backend.
final superAdminApplicationsListProvider =
    FutureProvider<List<AdminApplication>>((ref) async {
  final repo = ref.watch(superAdminApplicationsRepositoryProvider);
  return repo.fetchApplications();
});

/// Fetches live platform employee change requests from backend.
final superAdminChangeRequestsListProvider =
    FutureProvider<List<AdminChangeRequest>>((ref) async {
  final repo = ref.watch(superAdminApplicationsRepositoryProvider);
  return repo.fetchChangeRequests();
});

/// Live count of pending employee change requests across the platform.
final superAdminPendingChangeRequestsCountProvider = Provider<int>((ref) {
  final crsAsync = ref.watch(superAdminChangeRequestsListProvider);
  final crs = crsAsync.valueOrNull ?? const <AdminChangeRequest>[];
  return crs.where((cr) => cr.isPending).length;
});

/// Live total count of onboarding applications across the platform.
final superAdminTotalApplicationsCountProvider = Provider<int>((ref) {
  final appsAsync = ref.watch(superAdminApplicationsListProvider);
  return appsAsync.valueOrNull?.length ?? 0;
});

/// Computes live application metrics across the platform.
final superAdminApplicationMetricsProvider =
    Provider<SuperAdminApplicationMetrics>((ref) {
  final appsAsync = ref.watch(superAdminApplicationsListProvider);
  final apps = appsAsync.valueOrNull ?? const <AdminApplication>[];
  return SuperAdminApplicationMetrics.fromApplications(apps);
});

/// Applies status filter and text search query to live applications data.
final filteredSuperAdminApplicationsProvider =
    Provider<List<AdminApplication>>((ref) {
  final appsAsync = ref.watch(superAdminApplicationsListProvider);
  final apps = appsAsync.valueOrNull ?? const <AdminApplication>[];
  final statusFilter = ref.watch(applicationStatusFilterProvider);
  final query = ref.watch(applicationSearchQueryProvider).toLowerCase().trim();

  return apps.where((app) {
    // 1. Status Filter matching backend states
    bool matchesStatus = true;
    switch (statusFilter) {
      case PlatformApplicationStatusFilter.all:
        matchesStatus = true;
        break;
      case PlatformApplicationStatusFilter.pending:
        matchesStatus = app.registrationStatus == 'submitted' ||
            app.registrationStatus == 'pending';
        break;
      case PlatformApplicationStatusFilter.underReview:
        matchesStatus = app.registrationStatus == 'under_review';
        break;
      case PlatformApplicationStatusFilter.approved:
        matchesStatus = app.registrationStatus == 'approved' ||
            app.registrationStatus == 'active';
        break;
      case PlatformApplicationStatusFilter.correctionsRequired:
        matchesStatus = app.registrationStatus == 'correction_required';
        break;
      case PlatformApplicationStatusFilter.rejected:
        matchesStatus = app.registrationStatus == 'rejected';
        break;
    }

    if (!matchesStatus) return false;

    // 2. Search Query matching name, employee ID, ID, email, or phone
    if (query.isNotEmpty) {
      final name = (app.name ?? '').toLowerCase();
      final empId = (app.employeeId ?? '').toLowerCase();
      final idStr = app.id.toString();
      final email = (app.email ?? '').toLowerCase();
      final phone = (app.phone ?? '').toLowerCase();
      final company = (app.companyName ?? '').toLowerCase();

      final matchesQuery = name.contains(query) ||
          empId.contains(query) ||
          idStr.contains(query) ||
          email.contains(query) ||
          phone.contains(query) ||
          company.contains(query);

      if (!matchesQuery) return false;
    }

    return true;
  }).toList();
});
