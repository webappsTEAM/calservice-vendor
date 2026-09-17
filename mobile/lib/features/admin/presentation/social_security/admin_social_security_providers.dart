import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/admin_dashboard_api.dart';
import '../../domain/admin_social_security_registration.dart';

/// Filter for Social Security registration status.
/// Options: '' (All statuses), 'NOT_YET_ELIGIBLE', 'ELIGIBLE_PENDING', 'REGISTERED'.
final adminSocialSecurityStatusFilterProvider =
    StateProvider.autoDispose<String>((ref) => '');

/// Fetches individual worker Social Security compliance registration records.
final adminSocialSecurityListProvider = FutureProvider.autoDispose<
    List<AdminSocialSecurityRegistration>>((ref) async {
  final api = ref.watch(adminDashboardApiProvider);
  final status = ref.watch(adminSocialSecurityStatusFilterProvider);
  final res = await api.fetchSocialSecurityRegistrations(
    status: status.isNotEmpty ? status : null,
  );
  final rawList = res['results'];
  if (rawList is! List) return [];
  return rawList
      .whereType<Map<String, dynamic>>()
      .map(AdminSocialSecurityRegistration.fromJson)
      .toList();
});
