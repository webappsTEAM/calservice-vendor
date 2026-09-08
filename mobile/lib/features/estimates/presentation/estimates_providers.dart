import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/estimates_repository.dart';
import '../domain/quote_estimate.dart';

final estimatesFilterTabProvider = StateProvider<String>((ref) => 'all');
final estimatesSearchQueryProvider = StateProvider<String>((ref) => '');

final quotesListProvider = FutureProvider.autoDispose<List<QuoteEstimate>>((ref) async {
  final repo = ref.watch(estimatesRepositoryProvider);
  final tab = ref.watch(estimatesFilterTabProvider);
  final search = ref.watch(estimatesSearchQueryProvider);

  return repo.getQuotes(tab: tab, search: search);
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
