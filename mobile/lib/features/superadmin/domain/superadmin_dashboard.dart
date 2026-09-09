import '../../admin/domain/admin_application.dart';
import '../../admin/domain/fleet_member.dart';
import '../../jobs/domain/job.dart';

/// Aggregated state and live metrics for the Superadmin Workforce Operations Center.
class SuperAdminDashboardData {
  const SuperAdminDashboardData({
    this.applications = const [],
    this.jobs = const [],
    this.fleet = const [],
  });

  final List<AdminApplication> applications;
  final List<Job> jobs;
  final List<FleetMember> fleet;

  // ── Action Center Metrics (Items requiring immediate operational attention) ──

  /// Technician registrations requiring document review (submitted / under_review).
  int get pendingApplicationsCount =>
      applications.where((a) => a.isPending).length;

  /// Approved workforce field technicians.
  int get activeTechniciansCount =>
      applications.where((a) => a.isApproved || a.isActive).length;

  /// Customer bookings requiring technician dispatch (unassigned / unassigned confirmed).
  int get jobsAwaitingAssignmentCount => jobs.where((j) {
        final st = j.status.toLowerCase();
        return st == 'unassigned' ||
            (st == 'assigned' && !j.isAssignedToCurrentEmployee) ||
            st == 'new_request' ||
            (st == 'confirmed' && !j.isAssignedToCurrentEmployee);
      }).length;

  /// Technicians notified to re-upload flagged files (correction_required).
  int get correctionsPendingCount =>
      applications.where((a) => a.isCorrectionRequired).length;

  // ── Workforce Overview Metrics ─────────────────────────────────────────────

  /// Total registered technicians on roster.
  int get totalRegisteredCount => applications.length;

  /// Technicians approved and authorized for jobs.
  int get approvedAndActiveCount =>
      applications.where((a) => a.isApproved).length;

  /// Technicians approved/active, currently online and ready for dispatch.
  int get onlineAndAvailableCount =>
      fleet.where((f) => f.isAvailable).length;

  /// Technicians currently active on jobs in the field.
  int get onActiveJobsCount =>
      fleet.where((f) => f.isOnActiveJob).length;

  /// Applications awaiting dossier check.
  int get pendingReviewCount => pendingApplicationsCount;

  // ── Recent Operations & Service Bookings ───────────────────────────────────

  /// Recent service operations sorted newest first.
  List<Job> get recentJobs {
    final list = List<Job>.from(jobs);
    list.sort((a, b) {
      if (b.createdAt != null && a.createdAt != null) {
        return b.createdAt!.compareTo(a.createdAt!);
      }
      return b.id.compareTo(a.id);
    });
    return list;
  }
}
