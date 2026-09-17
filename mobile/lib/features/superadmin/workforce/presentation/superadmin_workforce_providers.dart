import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/superadmin_workforce_repository.dart';

/// Available filter tabs on the Workforce Roster screen.
enum WorkforceFilterType {
  all,
  solo,
  tied,
  relievingAudits;

  String get label {
    switch (this) {
      case WorkforceFilterType.all:
        return 'All Workforce';
      case WorkforceFilterType.solo:
        return 'Solo Workers';
      case WorkforceFilterType.tied:
        return 'Tied Workers';
      case WorkforceFilterType.relievingAudits:
        return 'Resignation Audits';
    }
  }

  String? get backendTypeParam {
    switch (this) {
      case WorkforceFilterType.all:
        return 'ALL';
      case WorkforceFilterType.solo:
        return 'SOLO';
      case WorkforceFilterType.tied:
        return 'TIED';
      case WorkforceFilterType.relievingAudits:
        return null;
    }
  }
}

/// Currently active filter tab.
final workforceFilterTypeProvider =
    StateProvider<WorkforceFilterType>((ref) => WorkforceFilterType.all);

/// Search query string.
final workforceSearchQueryProvider = StateProvider<String>((ref) => '');

/// Selected target vendor filter (null = all vendors).
final workforceSelectedVendorIdProvider = StateProvider<int?>((ref) => null);

/// Live aggregated workforce overview data provider.
final platformWorkforceDataProvider =
    FutureProvider.autoDispose<PlatformWorkforceOverviewData>((ref) async {
  final repository = ref.watch(superAdminWorkforceRepositoryProvider);
  final filterType = ref.watch(workforceFilterTypeProvider);
  final search = ref.watch(workforceSearchQueryProvider);
  final vendorId = ref.watch(workforceSelectedVendorIdProvider);

  return repository.fetchOverview(
    type: filterType.backendTypeParam,
    vendorId: vendorId,
    search: search,
  );
});

/// Controller for executing Super Admin workforce operations (Tie, Untie, Approve Relieving).
class SuperAdminWorkforceActionController extends StateNotifier<AsyncValue<String?>> {
  SuperAdminWorkforceActionController(this._ref) : super(const AsyncValue.data(null));

  final Ref _ref;

  SuperAdminWorkforceRepository get _repo =>
      _ref.read(superAdminWorkforceRepositoryProvider);

  /// Directly ties a technician to a vendor company.
  Future<bool> tieWorker({
    required int technicianId,
    required int vendorId,
    String engagementType = 'PER_JOB',
    String? notes,
  }) async {
    state = const AsyncValue.loading();
    try {
      final res = await _repo.tieWorker(
        technicianId,
        vendorId: vendorId,
        engagementType: engagementType,
        notes: notes,
      );
      final message = res['message'] as String? ?? 'Technician successfully tied to vendor.';
      state = AsyncValue.data(message);
      _ref.invalidate(platformWorkforceDataProvider);
      return true;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return false;
    }
  }

  /// Relieves a tied technician and restores them as a Solo Worker.
  Future<bool> untieWorker(int technicianId) async {
    state = const AsyncValue.loading();
    try {
      final res = await _repo.untieWorker(technicianId);
      final message = res['message'] as String? ?? 'Technician relieved and converted to Solo Worker.';
      state = AsyncValue.data(message);
      _ref.invalidate(platformWorkforceDataProvider);
      return true;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return false;
    }
  }

  /// Approves a pending SEVO platform relieving audit.
  Future<bool> approveRelievingRequest(
    int requestId, {
    required String auditNotes,
  }) async {
    state = const AsyncValue.loading();
    try {
      final res = await _repo.approveRelievingRequest(
        requestId,
        auditNotes: auditNotes,
      );
      final message = res['message'] as String? ?? 'Platform relieving audit approved. Clearance issued.';
      state = AsyncValue.data(message);
      _ref.invalidate(platformWorkforceDataProvider);
      return true;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return false;
    }
  }

  void clearState() {
    state = const AsyncValue.data(null);
  }
}

final superAdminWorkforceActionControllerProvider = StateNotifierProvider<
    SuperAdminWorkforceActionController, AsyncValue<String?>>((ref) {
  return SuperAdminWorkforceActionController(ref);
});
