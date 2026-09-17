import 'package:mobile/features/admin/domain/admin_application.dart';

export 'package:mobile/features/admin/domain/admin_application.dart';
export 'package:mobile/features/admin/domain/admin_change_request.dart';

/// Top-level sections for the Super Admin Applications Approval module.
enum SuperAdminApplicationsSection {
  onboardingApplications,
  profileChangeRequests,
}

extension SuperAdminApplicationsSectionX on SuperAdminApplicationsSection {
  String get label {
    switch (this) {
      case SuperAdminApplicationsSection.onboardingApplications:
        return 'Onboarding Applications';
      case SuperAdminApplicationsSection.profileChangeRequests:
        return 'Profile Change Requests';
    }
  }
}

/// Available status filters for the Super Admin Applications Approval module.
enum PlatformApplicationStatusFilter {
  all,
  pending,
  underReview,
  approved,
  correctionsRequired,
  rejected,
}

extension PlatformApplicationStatusFilterX on PlatformApplicationStatusFilter {
  String get label {
    switch (this) {
      case PlatformApplicationStatusFilter.all:
        return 'All Applications';
      case PlatformApplicationStatusFilter.pending:
        return 'Pending';
      case PlatformApplicationStatusFilter.underReview:
        return 'Under Review';
      case PlatformApplicationStatusFilter.approved:
        return 'Approved';
      case PlatformApplicationStatusFilter.correctionsRequired:
        return 'Corrections Required';
      case PlatformApplicationStatusFilter.rejected:
        return 'Rejected';
    }
  }

  String get shortLabel {
    switch (this) {
      case PlatformApplicationStatusFilter.all:
        return 'All';
      case PlatformApplicationStatusFilter.pending:
        return 'Pending';
      case PlatformApplicationStatusFilter.underReview:
        return 'Under Review';
      case PlatformApplicationStatusFilter.approved:
        return 'Approved';
      case PlatformApplicationStatusFilter.correctionsRequired:
        return 'Corrections';
      case PlatformApplicationStatusFilter.rejected:
        return 'Rejected';
    }
  }
}

/// Metrics summary for Super Admin platform applications.
class SuperAdminApplicationMetrics {
  const SuperAdminApplicationMetrics({
    required this.totalCount,
    required this.pendingCount,
    required this.underReviewCount,
    required this.approvedCount,
    required this.correctionsRequiredCount,
    required this.rejectedCount,
  });

  factory SuperAdminApplicationMetrics.fromApplications(List<AdminApplication> apps) {
    int pending = 0;
    int underReview = 0;
    int approved = 0;
    int corrections = 0;
    int rejected = 0;

    for (final app in apps) {
      final st = app.registrationStatus.toLowerCase();
      if (st == 'under_review') {
        underReview++;
      } else if (st == 'submitted' || st == 'pending') {
        pending++;
      } else if (st == 'approved' || st == 'active') {
        approved++;
      } else if (st == 'correction_required') {
        corrections++;
      } else if (st == 'rejected') {
        rejected++;
      }
    }

    return SuperAdminApplicationMetrics(
      totalCount: apps.length,
      pendingCount: pending,
      underReviewCount: underReview,
      approvedCount: approved,
      correctionsRequiredCount: corrections,
      rejectedCount: rejected,
    );
  }

  final int totalCount;
  final int pendingCount;
  final int underReviewCount;
  final int approvedCount;
  final int correctionsRequiredCount;
  final int rejectedCount;
}
