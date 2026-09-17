import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../admin/data/admin_dashboard_api.dart';
import '../../admin/domain/admin_application.dart';
import '../../admin/domain/fleet_member.dart';
import '../../jobs/domain/job.dart';
import '../domain/superadmin_dashboard.dart';

/// Repository coordinating Superadmin Operations Center live telemetry and data fetching.
class SuperAdminRepository {
  SuperAdminRepository(this._api);

  final AdminDashboardApi _api;

  /// Concurrently fetches live applications, service operations, and fleet presence telemetry.
  Future<SuperAdminDashboardData> fetchDashboardData() async {
    final results = await Future.wait([
      _api.fetchApplications().then(
            (raw) => raw
                .whereType<Map<String, dynamic>>()
                .map(AdminApplication.fromJson)
                .toList(),
            onError: (_) => <AdminApplication>[],
          ),
      _api.fetchJobs(statusFilter: 'active').then(
            (raw) => raw
                .whereType<Map<String, dynamic>>()
                .map(Job.fromJson)
                .toList(),
            onError: (_) => <Job>[],
          ),
      _api.fetchFleetMap().then(
            (raw) => raw
                .whereType<Map<String, dynamic>>()
                .map(FleetMember.fromJson)
                .toList(),
            onError: (_) => <FleetMember>[],
          ),
    ]);

    return SuperAdminDashboardData(
      applications: results[0] as List<AdminApplication>,
      jobs: results[1] as List<Job>,
      fleet: results[2] as List<FleetMember>,
    );
  }
}

final superAdminRepositoryProvider = Provider<SuperAdminRepository>((ref) {
  return SuperAdminRepository(ref.watch(adminDashboardApiProvider));
});
