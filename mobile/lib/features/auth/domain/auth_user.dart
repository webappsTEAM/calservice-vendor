import '../../../core/config/app_config.dart';

/// Mirrors the user object returned by `/auth/login/` and `/auth/me/`.
class AuthUser {
  const AuthUser({
    required this.id,
    required this.username,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.role,
    required this.companyId,
    required this.companyName,
    required this.isSuperuser,
    required this.employeeId,
    required this.registrationStatus,
    this.avatar,
    this.isPlatformAdmin = false,
    this.isVendorAdmin = false,
    this.isTechnician = false,
    this.userType,
  });

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    final rawAvatar = (json['avatar'] as String?) ?? (json['avatar_url'] as String?);
    final role = (json['role'] as String? ?? 'employee').toLowerCase();
    final isSuper = json['is_superuser'] as bool? ?? false;
    final companyId = (json['company'] as num?)?.toInt();
    final userType = json['user_type'] as String?;
    final isPlatformRole = role == 'superadmin' ||
        role == 'platform_admin' ||
        userType == 'platform_admin' ||
        isSuper;
    final isPlatformAdmin = (json['is_platform_admin'] == true) ||
        isPlatformRole ||
        ((role == 'admin' || role == 'manager') && (companyId == 1 || companyId == null));
    final isVendorRole = role == 'admin' ||
        role == 'manager' ||
        role == 'vendor_admin' ||
        role == 'company_admin';
    final isVendorAdmin = !isPlatformAdmin &&
        ((json['is_vendor_admin'] == true) || isVendorRole);
    final isTech = (json['is_technician'] as bool?) ?? (!isPlatformAdmin && !isVendorAdmin);

    return AuthUser(
      id: json['id'] as int,
      username: json['username'] as String? ?? '',
      email: json['email'] as String? ?? '',
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      role: role,
      companyId: companyId,
      companyName: json['company_name'] as String?,
      isSuperuser: isSuper,
      isPlatformAdmin: isPlatformAdmin,
      isVendorAdmin: isVendorAdmin,
      isTechnician: isTech,
      userType: userType,
      employeeId: json['employee_id'] as String?,
      registrationStatus:
          (json['registration_status'] as String?) ?? 'not_started',
      avatar: AppConfig.resolveMediaUrl(rawAvatar),
    );
  }

  final int id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;
  final String role;
  final int? companyId;
  final String? companyName;
  final bool isSuperuser;
  final bool isPlatformAdmin;
  final bool isVendorAdmin;
  final bool isTechnician;
  final String? userType;
  final String? employeeId;
  final String registrationStatus;
  final String? avatar;

  /// True for Platform Super Admins.
  bool get isSuperAdmin =>
      isPlatformAdmin ||
      isSuperuser ||
      role == 'superadmin' ||
      role == 'platform_admin' ||
      userType == 'platform_admin';

  /// True for Platform Admins (superuser/staff) and Vendor Admins/Managers.
  bool get isAdmin =>
      isSuperAdmin ||
      isVendorAdmin ||
      isPlatformAdmin ||
      isSuperuser ||
      role == 'admin' ||
      role == 'manager' ||
      role == 'company_admin' ||
      role == 'vendor_admin' ||
      role == 'superadmin' ||
      role == 'platform_admin' ||
      userType == 'platform_admin';

  /// True for Employees / Technicians (mutually exclusive with Admin).
  bool get isEmployee => !isAdmin && (role == 'employee' || isTechnician);

  String get displayName {
    final full = '$firstName $lastName'.trim();
    if (full.isNotEmpty) return full;
    return username;
  }
}
