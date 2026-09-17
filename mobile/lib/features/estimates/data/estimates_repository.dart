import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/quote_estimate.dart';

final estimatesRepositoryProvider = Provider<EstimatesRepository>((ref) {
  final dio = ref.watch(apiClientProvider);
  return EstimatesRepository(dio);
});

class EstimatesRepository {
  EstimatesRepository(this._dio);

  final Dio _dio;

  /// Fetches quotes and estimates for the technician.
  Future<List<QuoteEstimate>> getQuotes({
    String? tab,
    String? status,
    String? search,
    String? date,
  }) async {
    final queryParams = <String, dynamic>{};
    if (tab != null && tab.isNotEmpty && tab.toLowerCase() != 'all') {
      queryParams['tab'] = tab;
    }
    if (status != null && status.isNotEmpty && status.toLowerCase() != 'all') {
      queryParams['status'] = status;
    }
    if (search != null && search.isNotEmpty) {
      queryParams['search'] = search;
    }
    if (date != null && date.isNotEmpty) {
      queryParams['date'] = date;
    }

    try {
      final response = await _dio.get(
        '/workforce/quotes/',
        queryParameters: queryParams,
      );

      final data = response.data;
      final List<dynamic> list;
      if (data is List) {
        list = data;
      } else if (data is Map<String, dynamic> && data['results'] is List) {
        list = data['results'] as List;
      } else if (data is Map<String, dynamic> && data['quotes'] is List) {
        list = data['quotes'] as List;
      } else {
        list = const [];
      }

      return list
          .map((item) => QuoteEstimate.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException {
      // Try fallback to vendor estimations endpoint if available
      try {
        final fallback = await _dio.get(
          '/vendor/estimations/',
          queryParameters: queryParams,
        );
        final data = fallback.data;
        final List<dynamic> list;
        if (data is List) {
          list = data;
        } else if (data is Map<String, dynamic> && data['results'] is List) {
          list = data['results'] as List;
        } else if (data is Map<String, dynamic> && data['estimations'] is List) {
          list = data['estimations'] as List;
        } else {
          list = const [];
        }
        return list
            .map((item) => QuoteEstimate.fromJson(item as Map<String, dynamic>))
            .toList();
      } catch (_) {
        rethrow;
      }
    }
  }

  /// Fetches detail for a single quote.
  Future<QuoteEstimate> getQuoteDetail(int quoteId) async {
    final response = await _dio.get('/workforce/quotes/$quoteId/');
    return QuoteEstimate.fromJson(response.data as Map<String, dynamic>);
  }
}
