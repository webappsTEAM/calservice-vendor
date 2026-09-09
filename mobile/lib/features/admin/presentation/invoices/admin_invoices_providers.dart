import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/admin_dashboard_api.dart';
import '../../domain/admin_invoice.dart';

/// Search query string for commercial invoices.
final adminInvoicesSearchQueryProvider = StateProvider<String>((ref) => '');

/// Selected status filter for commercial invoices (e.g. '', 'ISSUED', 'PARTIALLY_PAID', 'PAID', etc.).
final adminInvoicesStatusFilterProvider = StateProvider<String>((ref) => '');

/// Fetches invoices list from `/workforce/invoices/` with active search and status filter.
final adminInvoicesListProvider =
    FutureProvider.autoDispose<List<AdminInvoice>>((ref) async {
  final api = ref.watch(adminDashboardApiProvider);
  final search = ref.watch(adminInvoicesSearchQueryProvider);
  final status = ref.watch(adminInvoicesStatusFilterProvider);

  final raw = await api.fetchInvoices(
    search: search.trim().isNotEmpty ? search.trim() : null,
    status: status.trim().isNotEmpty ? status.trim() : null,
  );
  return raw
      .whereType<Map<String, dynamic>>()
      .map(AdminInvoice.fromJson)
      .toList();
});

/// Fetches detailed invoice with line items and payment history by invoice ID.
final adminInvoiceDetailProvider =
    FutureProvider.autoDispose.family<AdminInvoice, int>((ref, id) async {
  final api = ref.watch(adminDashboardApiProvider);
  final raw = await api.fetchInvoiceDetail(id);
  return AdminInvoice.fromJson(raw);
});
