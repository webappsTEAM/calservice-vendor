import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/superadmin_repository.dart';
import '../domain/superadmin_dashboard.dart';

/// Provider for live Super Admin platform dashboard metrics and operations feed.
final superAdminDashboardDataProvider =
    FutureProvider.autoDispose<SuperAdminDashboardData>((ref) async {
  final repository = ref.watch(superAdminRepositoryProvider);
  return repository.fetchDashboardData();
});
