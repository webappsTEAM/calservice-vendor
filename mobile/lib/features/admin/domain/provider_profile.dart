/// Domain model representing the authenticated Service Provider / Vendor profile.
class ProviderProfile {
  const ProviderProfile({
    required this.id,
    required this.companyName,
    this.companyCode,
    this.registrationNumber,
    this.email,
    this.phone,
    this.address,
    this.city,
    this.state,
    this.postalCode,
    this.isActive = true,
    this.isVerified = true,
    this.tiedTechniciansCount = 0,
    this.primaryAdmin,
    this.createdAt,
    this.isSuperadmin = false,
  });

  final int id;
  final String companyName;
  final String? companyCode;
  final String? registrationNumber;
  final String? email;
  final String? phone;
  final String? address;
  final String? city;
  final String? state;
  final String? postalCode;
  final bool isActive;
  final bool isVerified;
  final int tiedTechniciansCount;
  final Map<String, dynamic>? primaryAdmin;
  final String? createdAt;
  final bool isSuperadmin;

  String get fullAddress {
    final parts = [address, city, state, postalCode]
        .where((p) => p != null && p.trim().isNotEmpty)
        .toList();
    return parts.isEmpty ? 'Address not specified' : parts.join(', ');
  }

  factory ProviderProfile.fromJson(Map<String, dynamic> json) {
    return ProviderProfile(
      id: json['id'] as int? ?? 0,
      companyName: json['company_name'] as String? ?? json['name'] as String? ?? 'Vendor Business',
      companyCode: json['company_code'] as String?,
      registrationNumber: json['registration_number'] as String? ?? json['business_registration_number'] as String?,
      email: json['email'] as String? ?? json['contact_email'] as String?,
      phone: json['phone'] as String? ?? json['contact_phone'] as String?,
      address: json['address'] as String?,
      city: json['city'] as String?,
      state: json['state'] as String?,
      postalCode: json['postal_code'] as String? ?? json['pincode'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      isVerified: json['is_verified'] as bool? ?? true,
      tiedTechniciansCount: json['tied_technicians_count'] as int? ?? json['technicians_count'] as int? ?? 0,
      primaryAdmin: json['primary_admin'] as Map<String, dynamic>?,
      createdAt: json['created_at'] as String?,
      isSuperadmin: json['is_superadmin'] as bool? ?? false,
    );
  }
}
