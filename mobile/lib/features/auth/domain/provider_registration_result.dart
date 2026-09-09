import '../../../core/utils/json_parsing.dart';
import 'auth_user.dart';

/// Represents company information returned after service provider business registration.
class ProviderCompanyInfo {
  const ProviderCompanyInfo({
    required this.id,
    required this.slug,
    required this.companyName,
  });

  factory ProviderCompanyInfo.fromJson(Map<String, dynamic> json) {
    return ProviderCompanyInfo(
      id: parseInt(json['id']) ?? 0,
      slug: parseString(json['slug']) ?? '',
      companyName: parseString(json['company_name']) ?? 'Business',
    );
  }

  final int id;
  final String slug;
  final String companyName;

  Map<String, dynamic> toJson() => {
        'id': id,
        'slug': slug,
        'company_name': companyName,
      };
}

/// Typed model representing the response from `POST /workforce/provider/signup/`.
class ProviderRegistrationResult {
  const ProviderRegistrationResult({
    required this.message,
    required this.accessToken,
    required this.refreshToken,
    required this.token,
    required this.company,
    required this.user,
  });

  factory ProviderRegistrationResult.fromJson(Map<String, dynamic> json) {
    final companyJson = json['company'] is Map<String, dynamic>
        ? json['company'] as Map<String, dynamic>
        : <String, dynamic>{};

    final userJson = json['user'] is Map<String, dynamic>
        ? json['user'] as Map<String, dynamic>
        : <String, dynamic>{};

    final companyInfo = ProviderCompanyInfo.fromJson(companyJson);

    // Merge company context into user object so AuthUser has correct companyId and companyName
    final mergedUserMap = Map<String, dynamic>.from(userJson);
    mergedUserMap['company'] ??= companyInfo.id;
    mergedUserMap['company_name'] ??= companyInfo.companyName;
    mergedUserMap['is_vendor_admin'] ??= true;
    mergedUserMap['registration_status'] ??= 'approved';

    final authUser = AuthUser.fromJson(mergedUserMap);

    return ProviderRegistrationResult(
      message: parseString(json['message']) ?? 'Provider business account created successfully.',
      accessToken: parseString(json['access_token']) ?? parseString(json['token']) ?? '',
      refreshToken: parseString(json['refresh_token']) ?? '',
      token: parseString(json['token']) ?? parseString(json['access_token']) ?? '',
      company: companyInfo,
      user: authUser,
    );
  }

  final String message;
  final String accessToken;
  final String refreshToken;
  final String token;
  final ProviderCompanyInfo company;
  final AuthUser user;
}
