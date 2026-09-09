import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/admin_dashboard_api.dart';
import '../../domain/admin_pricing_policy.dart';

/// Fetches all service category commercial pricing policies from the live backend.
final adminPricingPoliciesProvider =
    FutureProvider.autoDispose<List<AdminPricingPolicy>>((ref) async {
  final api = ref.watch(adminDashboardApiProvider);
  final rawList = await api.fetchPricingPolicies();
  return rawList
      .whereType<Map<String, dynamic>>()
      .map(AdminPricingPolicy.fromJson)
      .toList();
});
