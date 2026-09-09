import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/estimates_repository.dart';
import '../domain/quote_estimate.dart';

final estimatesFilterTabProvider = StateProvider<String>((ref) => 'all');
final estimatesSearchQueryProvider = StateProvider<String>((ref) => '');
final estimatesDateFilterProvider = StateProvider<String?>((ref) => null);

final quotesListProvider = FutureProvider.autoDispose<List<QuoteEstimate>>((ref) async {
  final repo = ref.watch(estimatesRepositoryProvider);
  final tab = ref.watch(estimatesFilterTabProvider);
  final search = ref.watch(estimatesSearchQueryProvider);
  final date = ref.watch(estimatesDateFilterProvider);

  final quotes = await repo.getQuotes(tab: tab, search: search, date: date);

  var filtered = quotes;

  // Filter by tab if client has raw/unfiltered dataset
  if (tab != 'all') {
    switch (tab) {
      case 'draft':
        filtered = filtered.where((q) => q.isDraft).toList();
        break;
      case 'assigned':
        filtered = filtered.where((q) => q.isAssigned).toList();
        break;
      case 'in_progress':
        filtered = filtered.where((q) => q.isInProgress).toList();
        break;
      case 'sent':
        filtered = filtered.where((q) => q.isSent).toList();
        break;
      case 'accepted':
        filtered = filtered.where((q) => q.isAccepted).toList();
        break;
    }
  }

  // Filter by search query (customer name, ID, AC brand, service)
  if (search.isNotEmpty) {
    final query = search.toLowerCase();
    filtered = filtered.where((q) {
      final nameMatches = q.customerName.toLowerCase().contains(query);
      final idMatches = q.quoteNumber.toLowerCase().contains(query) ||
          q.id.toString().contains(query) ||
          q.jobId.toString().contains(query);
      final brandMatches = q.brand.toLowerCase().contains(query);
      final serviceMatches = q.serviceName.toLowerCase().contains(query);
      return nameMatches || idMatches || brandMatches || serviceMatches;
    }).toList();
  }

  // Filter by date (dd/mm/yyyy)
  if (date != null && date.isNotEmpty) {
    filtered = filtered.where((q) {
      if (q.createdAt == null) return false;
      final day = q.createdAt!.day.toString().padLeft(2, '0');
      final month = q.createdAt!.month.toString().padLeft(2, '0');
      final year = q.createdAt!.year.toString();
      final formattedSlash = '$day/$month/$year';
      final formattedDash = '$year-$month-$day';
      return formattedSlash == date || formattedDash == date;
    }).toList();
  }

  return filtered;
});

/// Metrics summary provider computed from all quotes
final quotesMetricsProvider = Provider.autoDispose<Map<String, int>>((ref) {
  final quotesAsync = ref.watch(quotesListProvider);
  return quotesAsync.maybeWhen(
    data: (quotes) {
      return {
        'total': quotes.length,
        'drafts': quotes.filter((q) => q.isDraft).length,
        'sent': quotes.filter((q) => q.isSent).length,
        'accepted': quotes.filter((q) => q.isAccepted).length,
      };
    },
    orElse: () => {
      'total': 0,
      'drafts': 0,
      'sent': 0,
      'accepted': 0,
    },
  );
});

extension on List<QuoteEstimate> {
  Iterable<QuoteEstimate> filter(bool Function(QuoteEstimate) predicate) {
    return where(predicate);
  }
}
