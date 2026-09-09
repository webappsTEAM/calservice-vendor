import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/admin_dashboard_api.dart';
import '../../domain/admin_scorecard.dart';

/// Fetches worker & provider scorecards from live backend.
final adminScorecardsListProvider =
    FutureProvider.autoDispose<List<AdminScorecardItem>>((ref) async {
  final api = ref.watch(adminDashboardApiProvider);
  final res = await api.fetchAdminScorecards();
  final rawList = res['results'];
  if (rawList is! List) return [];
  return rawList
      .whereType<Map<String, dynamic>>()
      .map(AdminScorecardItem.fromJson)
      .toList();
});

/// Search query filter for Scorecards.
final adminScorecardsSearchQueryProvider =
    StateProvider.autoDispose<String>((ref) => '');

/// Selected tier filter ('ALL', 'GOLD', 'SILVER', 'BRONZE', 'UNRATED').
final adminScorecardsTierFilterProvider =
    StateProvider.autoDispose<String>((ref) => 'ALL');

/// Filtered scorecards list.
final filteredAdminScorecardsProvider =
    Provider.autoDispose<AsyncValue<List<AdminScorecardItem>>>((ref) {
  final asyncList = ref.watch(adminScorecardsListProvider);
  final query = ref.watch(adminScorecardsSearchQueryProvider).trim().toLowerCase();
  final tierFilter = ref.watch(adminScorecardsTierFilterProvider);

  return asyncList.whenData((list) {
    return list.where((item) {
      if (tierFilter != 'ALL' && item.tier != tierFilter) {
        return false;
      }
      if (query.isNotEmpty) {
        final nameMatch = item.employeeName.toLowerCase().contains(query);
        final idMatch = item.employeeId.toString().contains(query);
        if (!nameMatch && !idMatch) return false;
      }
      return true;
    }).toList();
  });
});
