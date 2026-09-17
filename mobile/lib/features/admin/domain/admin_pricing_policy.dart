import '../../../core/utils/json_parsing.dart';

/// Represents a service category commercial pricing & approval policy.
///
/// Backed by `/api/workforce/settings/pricing-policies/`.
class AdminPricingPolicy {
  const AdminPricingPolicy({
    required this.id,
    required this.serviceCategory,
    this.displayName = '',
    this.consultationFeeMode = 'FLAT',
    this.consultationFeeModeDisplay = 'Flat fee',
    this.consultationFeeAmount = 0.0,
    this.freeRadiusKm = 15.0,
    this.beyondRadiusAmount = 300.0,
    this.hubLatitude,
    this.hubLongitude,
    this.highValueReviewThreshold,
    this.requiresAdminApproval = true,
    this.advancePercent = 100.0,
    this.allowCustomerSuppliedMaterials = false,
    this.isActive = true,
    this.updatedById,
    this.updatedAt,
  });

  factory AdminPricingPolicy.fromJson(Map<String, dynamic> json) {
    return AdminPricingPolicy(
      id: parseInt(json['id']) ?? 0,
      serviceCategory: parseString(json['service_category']) ?? '',
      displayName: parseString(json['display_name']) ?? '',
      consultationFeeMode:
          parseString(json['consultation_fee_mode'])?.toUpperCase() ?? 'FLAT',
      consultationFeeModeDisplay:
          parseString(json['consultation_fee_mode_display']) ??
              parseString(json['consultation_fee_mode']) ??
              'Flat fee',
      consultationFeeAmount:
          parseDouble(json['consultation_fee_amount']) ?? 0.0,
      freeRadiusKm: parseDouble(json['free_radius_km']) ?? 15.0,
      beyondRadiusAmount: parseDouble(json['beyond_radius_amount']) ?? 300.0,
      hubLatitude: parseDouble(json['hub_latitude']),
      hubLongitude: parseDouble(json['hub_longitude']),
      highValueReviewThreshold:
          parseDouble(json['high_value_review_threshold']),
      requiresAdminApproval: json['requires_admin_approval'] == null
          ? true
          : parseBool(json['requires_admin_approval']),
      advancePercent: parseDouble(json['advance_percent']) ?? 100.0,
      allowCustomerSuppliedMaterials:
          parseBool(json['allow_customer_supplied_materials']),
      isActive: json['is_active'] == null
          ? true
          : parseBool(json['is_active']),
      updatedById: parseInt(json['updated_by_id']),
      updatedAt: parseDateTime(json['updated_at']),
    );
  }

  final int id;
  final String serviceCategory;
  final String displayName;
  final String consultationFeeMode;
  final String consultationFeeModeDisplay;
  final double consultationFeeAmount;
  final double freeRadiusKm;
  final double beyondRadiusAmount;
  final double? hubLatitude;
  final double? hubLongitude;
  final double? highValueReviewThreshold;
  final bool requiresAdminApproval;
  final double advancePercent;
  final bool allowCustomerSuppliedMaterials;
  final bool isActive;
  final int? updatedById;
  final DateTime? updatedAt;

  String get effectiveTitle {
    if (displayName.isNotEmpty) return displayName;
    final cat = serviceCategory.toLowerCase();
    if (cat == 'ac services' || cat == 'ac') {
      return 'AC Services';
    }
    if (cat == 'mason' || cat == 'masonry' || cat == 'masonry & civil') {
      return 'Masonry & Civil';
    }
    if (cat == 'painting' || cat == 'painting & waterproofing') {
      return 'Painting & Waterproofing';
    }
    return serviceCategory;
  }

  Map<String, dynamic> toJson() {
    return {
      'display_name': displayName,
      'consultation_fee_mode': consultationFeeMode,
      'consultation_fee_amount': consultationFeeAmount,
      'free_radius_km': freeRadiusKm,
      'beyond_radius_amount': beyondRadiusAmount,
      if (hubLatitude != null) 'hub_latitude': hubLatitude,
      if (hubLongitude != null) 'hub_longitude': hubLongitude,
      'high_value_review_threshold': highValueReviewThreshold,
      'requires_admin_approval': requiresAdminApproval,
      'advance_percent': advancePercent,
      'allow_customer_supplied_materials': allowCustomerSuppliedMaterials,
      'is_active': isActive,
    };
  }

  AdminPricingPolicy copyWith({
    String? displayName,
    String? consultationFeeMode,
    String? consultationFeeModeDisplay,
    double? consultationFeeAmount,
    double? freeRadiusKm,
    double? beyondRadiusAmount,
    double? hubLatitude,
    double? hubLongitude,
    double? highValueReviewThreshold,
    bool? requiresAdminApproval,
    double? advancePercent,
    bool? allowCustomerSuppliedMaterials,
    bool? isActive,
  }) {
    return AdminPricingPolicy(
      id: id,
      serviceCategory: serviceCategory,
      displayName: displayName ?? this.displayName,
      consultationFeeMode: consultationFeeMode ?? this.consultationFeeMode,
      consultationFeeModeDisplay:
          consultationFeeModeDisplay ?? this.consultationFeeModeDisplay,
      consultationFeeAmount:
          consultationFeeAmount ?? this.consultationFeeAmount,
      freeRadiusKm: freeRadiusKm ?? this.freeRadiusKm,
      beyondRadiusAmount: beyondRadiusAmount ?? this.beyondRadiusAmount,
      hubLatitude: hubLatitude ?? this.hubLatitude,
      hubLongitude: hubLongitude ?? this.hubLongitude,
      highValueReviewThreshold:
          highValueReviewThreshold ?? this.highValueReviewThreshold,
      requiresAdminApproval:
          requiresAdminApproval ?? this.requiresAdminApproval,
      advancePercent: advancePercent ?? this.advancePercent,
      allowCustomerSuppliedMaterials:
          allowCustomerSuppliedMaterials ?? this.allowCustomerSuppliedMaterials,
      isActive: isActive ?? this.isActive,
      updatedById: updatedById,
      updatedAt: updatedAt,
    );
  }
}
