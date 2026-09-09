import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/platform_vendor.dart';
import 'superadmin_vendor_api.dart';

/// Repository for managing Super Admin Vendor Directory operations.
class SuperAdminVendorRepository {
  SuperAdminVendorRepository(this._api);

  final SuperAdminVendorApi _api;

  /// Fetches the platform vendors list and total count.
  Future<PlatformVendorsResponse> fetchVendors() async {
    final raw = await _api.fetchVendors();
    return PlatformVendorsResponse.fromJson(raw);
  }
}

final superAdminVendorRepositoryProvider =
    Provider<SuperAdminVendorRepository>((ref) {
  return SuperAdminVendorRepository(ref.watch(superAdminVendorApiProvider));
});
