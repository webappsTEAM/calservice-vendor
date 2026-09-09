import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/admin_dashboard_api.dart';
import '../../domain/admin_quotation.dart';

/// Active tab on the Quotation Approvals screen:
/// - 'acceptance': Awaiting SEVO approval (after customer accepts)
/// - 'presend': Held before sending (high-value threshold / structural clearance)
final adminQuotationTabProvider = StateProvider<String>((ref) => 'acceptance');

/// Quotations awaiting SEVO authorization after customer acceptance.
final adminQuotesPendingApprovalProvider =
    FutureProvider.autoDispose<List<AdminQuotation>>((ref) async {
  final api = ref.watch(adminDashboardApiProvider);
  final raw = await api.fetchQuotesPendingApproval();
  return raw
      .whereType<Map<String, dynamic>>()
      .map(AdminQuotation.fromJson)
      .toList();
});

/// Quotations held before sending to customer (pre-send review queue).
final adminQuotesPendingReviewProvider =
    FutureProvider.autoDispose<List<AdminQuotation>>((ref) async {
  final api = ref.watch(adminDashboardApiProvider);
  final raw = await api.fetchQuotesPendingReview();
  return raw
      .whereType<Map<String, dynamic>>()
      .map(AdminQuotation.fromJson)
      .toList();
});
