import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/superadmin_vendor_repository.dart';
import '../domain/platform_vendor.dart';

/// Live platform vendor companies list.
final platformVendorsDataProvider =
    FutureProvider.autoDispose<PlatformVendorsResponse>((ref) async {
  final repository = ref.watch(superAdminVendorRepositoryProvider);
  return repository.fetchVendors();
});

/// Search query string for filtering the vendor directory list.
final vendorSearchQueryProvider = StateProvider.autoDispose<String>((ref) => '');

/// Filtered list of vendor companies based on active search query.
final filteredPlatformVendorsProvider =
    Provider.autoDispose<List<PlatformVendor>>((ref) {
  final vendorsAsync = ref.watch(platformVendorsDataProvider);
  final query = ref.watch(vendorSearchQueryProvider).trim().toLowerCase();

  return vendorsAsync.when(
    data: (response) {
      if (query.isEmpty) return response.vendors;

      return response.vendors.where((v) {
        final nameMatches = v.companyName.toLowerCase().contains(query);
        final ownerMatches = v.ownerName.toLowerCase().contains(query);
        final emailMatches = v.ownerEmail.toLowerCase().contains(query);
        final cityMatches = v.city.toLowerCase().contains(query);
        final slugMatches = v.slug.toLowerCase().contains(query);
        final idMatches = v.id.toString().contains(query);

        return nameMatches ||
            ownerMatches ||
            emailMatches ||
            cityMatches ||
            slugMatches ||
            idMatches;
      }).toList();
    },
    loading: () => [],
    error: (error, stack) => [],
  );
});

/// Aggregate summary metrics for the Vendor Directory header cards.
class VendorDirectoryMetrics {
  const VendorDirectoryMetrics({
    required this.registeredVendors,
    required this.totalTiedWorkforce,
  });

  final int registeredVendors;
  final int totalTiedWorkforce;
}

final vendorDirectoryMetricsProvider =
    Provider.autoDispose<VendorDirectoryMetrics>((ref) {
  final vendorsAsync = ref.watch(platformVendorsDataProvider);

  return vendorsAsync.when(
    data: (response) {
      final tiedSum = response.vendors.fold<int>(
        0,
        (sum, v) => sum + v.tiedWorkersCount,
      );
      return VendorDirectoryMetrics(
        registeredVendors: response.vendors.length,
        totalTiedWorkforce: tiedSum,
      );
    },
    loading: () => const VendorDirectoryMetrics(
      registeredVendors: 0,
      totalTiedWorkforce: 0,
    ),
    error: (error, stack) => const VendorDirectoryMetrics(
      registeredVendors: 0,
      totalTiedWorkforce: 0,
    ),
  );
});
