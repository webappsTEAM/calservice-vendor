import '../../../core/utils/json_parsing.dart';

/// Represents a service requested or approved for a technician.
class AdminServiceItem {
  const AdminServiceItem({
    required this.id,
    required this.name,
    this.status = 'pending',
    this.category,
    this.requestType,
    this.rejectionReason,
    this.requestedAt,
    this.approvedAt,
    this.approvedBy,
  });

  factory AdminServiceItem.fromJson(Map<String, dynamic> json) {
    return AdminServiceItem(
      id: parseInt(json['id']) ?? parseInt(json['service_id']) ?? 0,
      name: parseString(json['name']) ?? parseString(json['service_name']) ?? 'Service',
      status: parseString(json['status'])?.toLowerCase() ?? 'pending',
      category: parseString(json['category_name']) ?? parseString(json['category']),
      requestType: parseString(json['request_type']),
      rejectionReason: parseString(json['rejection_reason']),
      requestedAt: parseDateTime(json['requested_at']) ?? parseDateTime(json['removal_requested_at']),
      approvedAt: parseDateTime(json['approved_at']),
      approvedBy: parseString(json['approved_by']),
    );
  }

  final int id;
  final String name;
  final String status;
  final String? category;
  final String? requestType;
  final String? rejectionReason;
  final DateTime? requestedAt;
  final DateTime? approvedAt;
  final String? approvedBy;

  bool get isApproved => status == 'approved';
  bool get isPending => status == 'pending' || status == 'requested';
  bool get isRejected => status == 'rejected';
}

/// Represents an uploaded identity or trade qualification document.
class AdminDocumentItem {
  const AdminDocumentItem({
    required this.category,
    required this.title,
    this.status = 'pending',
    this.fileUrl,
    this.documentNumber,
    this.issueDate,
    this.expiryDate,
    this.rejectionReason,
    this.uploadedAt,
    this.verifiedAt,
    this.verifiedBy,
  });

  factory AdminDocumentItem.fromJson(Map<String, dynamic> json, [String? fallbackCategory]) {
    final cat = parseString(json['category']) ?? fallbackCategory ?? 'document';
    final rawTitle = parseString(json['title']) ?? parseString(json['category']) ?? fallbackCategory;
    final formattedTitle = (rawTitle != null && rawTitle.isNotEmpty)
        ? rawTitle.replaceAll('_', ' ').split(' ').map((w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '').join(' ')
        : 'Document';

    return AdminDocumentItem(
      category: cat,
      title: formattedTitle,
      status: parseString(json['status'])?.toLowerCase() ?? 'pending',
      fileUrl: parseString(json['file_url']) ?? parseString(json['file']),
      documentNumber: parseString(json['document_number']),
      issueDate: parseString(json['issue_date']),
      expiryDate: parseString(json['expiry_date']),
      rejectionReason: parseString(json['rejection_reason']),
      uploadedAt: parseDateTime(json['uploaded_at']) ?? parseDateTime(json['created_at']),
      verifiedAt: parseDateTime(json['verified_at']),
      verifiedBy: parseString(json['verified_by']),
    );
  }

  final String category;
  final String title;
  final String status;
  final String? fileUrl;
  final String? documentNumber;
  final String? issueDate;
  final String? expiryDate;
  final String? rejectionReason;
  final DateTime? uploadedAt;
  final DateTime? verifiedAt;
  final String? verifiedBy;

  bool get isApproved => status == 'approved';
  bool get isPending => status == 'pending' || status == 'submitted';
  bool get isRejected => status == 'rejected';
}

/// Represents an applicant / technician dossier record returned by
/// `GET /workforce/admin/applications/` and `GET /workforce/admin/applications/:id/`.
class AdminApplication {
  const AdminApplication({
    required this.id,
    this.employeeId,
    this.name,
    this.firstName,
    this.lastName,
    this.email,
    this.phone,
    required this.registrationStatus,
    this.isOnline = false,
    this.allRequestedServices = const [],
    this.documentsList = const [],
    this.documentsStatus = const {},
    this.onboardingData = const {},
    this.createdAt,
    this.companyId,
    this.companyName,
    this.dateOfBirth,
  });

  factory AdminApplication.fromJson(Map<String, dynamic> json) {
    final userJson = json['user'] is Map<String, dynamic>
        ? json['user'] as Map<String, dynamic>
        : null;

    final firstName = parseString(json['first_name']) ?? parseString(userJson?['first_name']);
    final lastName = parseString(json['last_name']) ?? parseString(userJson?['last_name']);

    final nameFromJson = parseString(json['name']) ??
        parseString(json['full_name']) ??
        ((firstName != null || lastName != null)
            ? '${firstName ?? ''} ${lastName ?? ''}'.trim()
            : null);

    final resolvedName = (nameFromJson != null && nameFromJson.isNotEmpty)
        ? nameFromJson
        : parseString(userJson?['username']) ?? 'Technician #${json['id']}';

    final emailFromJson = parseString(json['email']) ?? parseString(userJson?['email']);
    final phoneFromJson = parseString(json['phone']) ??
        parseString(json['mobile_number']) ??
        parseString(userJson?['mobile_number']) ??
        parseString(userJson?['phone']);

    final onboarding = json['onboarding_data'] is Map<String, dynamic>
        ? json['onboarding_data'] as Map<String, dynamic>
        : const <String, dynamic>{};
    final draft = onboarding['draft'] is Map<String, dynamic>
        ? onboarding['draft'] as Map<String, dynamic>
        : const <String, dynamic>{};

    // Parse services
    final servicesRaw = json['all_requested_services'] ??
        json['services'] ??
        json['requested_services'] ??
        onboarding['services'] ??
        draft['services'];
    final List<AdminServiceItem> parsedServices = [];
    if (servicesRaw is List) {
      for (final s in servicesRaw) {
        if (s is Map<String, dynamic>) {
          parsedServices.add(AdminServiceItem.fromJson(s));
        }
      }
    }

    // Parse documents
    final docsRaw = json['documents'];
    final List<AdminDocumentItem> parsedDocs = [];
    if (docsRaw is List) {
      for (final d in docsRaw) {
        if (d is Map<String, dynamic>) {
          parsedDocs.add(AdminDocumentItem.fromJson(d));
        }
      }
    } else if (docsRaw is Map<String, dynamic>) {
      for (final entry in docsRaw.entries) {
        if (entry.value is Map<String, dynamic>) {
          parsedDocs.add(AdminDocumentItem.fromJson(entry.value as Map<String, dynamic>, entry.key));
        }
      }
    }

    if (parsedDocs.isEmpty) {
      final docStatusMap = json['documents_status'] is Map<String, dynamic>
          ? json['documents_status'] as Map<String, dynamic>
          : (onboarding['documents'] is Map<String, dynamic>
              ? onboarding['documents'] as Map<String, dynamic>
              : (draft['documents'] is Map<String, dynamic>
                  ? draft['documents'] as Map<String, dynamic>
                  : const <String, dynamic>{}));

      for (final entry in docStatusMap.entries) {
        if (entry.value is Map<String, dynamic>) {
          parsedDocs.add(AdminDocumentItem.fromJson(entry.value as Map<String, dynamic>, entry.key));
        }
      }
    }

    final isOnlineVal = parseBool(json['is_online']) ||
        (userJson != null && parseBool(userJson['is_online']));

    return AdminApplication(
      id: parseInt(json['id']) ?? 0,
      employeeId: parseString(json['employee_id']),
      name: resolvedName,
      firstName: firstName,
      lastName: lastName,
      email: emailFromJson,
      phone: phoneFromJson,
      registrationStatus:
          parseString(json['registration_status'])?.toLowerCase() ?? 'not_started',
      isOnline: isOnlineVal,
      allRequestedServices: parsedServices,
      documentsList: parsedDocs,
      documentsStatus: json['documents_status'] is Map<String, dynamic>
          ? json['documents_status'] as Map<String, dynamic>
          : const {},
      onboardingData: onboarding,
      createdAt: parseDateTime(json['created_at']) ?? parseDateTime(json['applied_date']),
      companyId: parseInt(json['company']),
      companyName: parseString(json['company_name']),
      dateOfBirth: parseString(json['date_of_birth']),
    );
  }

  final int id;
  final String? employeeId;
  final String? name;
  final String? firstName;
  final String? lastName;
  final String? email;
  final String? phone;
  final String registrationStatus;
  final bool isOnline;
  final List<AdminServiceItem> allRequestedServices;
  final List<AdminDocumentItem> documentsList;
  final Map<String, dynamic> documentsStatus;
  final Map<String, dynamic> onboardingData;
  final DateTime? createdAt;
  final int? companyId;
  final String? companyName;
  final String? dateOfBirth;

  bool get isPending =>
      registrationStatus == 'submitted' || registrationStatus == 'under_review';

  bool get isApproved => registrationStatus == 'approved';

  bool get isCorrectionRequired => registrationStatus == 'correction_required';

  bool get isRejected => registrationStatus == 'rejected';

  String get initial {
    final n = (name ?? '').trim();
    return n.isNotEmpty ? n[0].toUpperCase() : 'T';
  }

  // ── Dossier Section Getters ───────────────────────────────────────────────

  Map<String, dynamic> get draft =>
      onboardingData['draft'] is Map<String, dynamic>
          ? onboardingData['draft'] as Map<String, dynamic>
          : const {};

  Map<String, dynamic> get personal =>
      draft['personal'] is Map<String, dynamic>
          ? draft['personal'] as Map<String, dynamic>
          : const {};

  Map<String, dynamic> get address =>
      draft['address'] is Map<String, dynamic>
          ? draft['address'] as Map<String, dynamic>
          : const {};

  Map<String, dynamic> get skills =>
      draft['skills'] is Map<String, dynamic>
          ? draft['skills'] as Map<String, dynamic>
          : const {};

  Map<String, dynamic> get bank =>
      draft['bank'] is Map<String, dynamic>
          ? draft['bank'] as Map<String, dynamic>
          : const {};

  // Personal info
  String get dob =>
      dateOfBirth ?? parseString(personal['dob']) ?? 'Not specified';
  String get gender => parseString(personal['gender']) ?? 'Not specified';
  String get emergencyName => parseString(personal['emergencyName']) ?? 'None';
  String get emergencyPhone => parseString(personal['emergencyPhone']) ?? 'None';

  // Address info
  String get streetAddress => parseString(address['street']) ?? 'Not provided';
  String get city => parseString(address['city']) ?? '—';
  String get state => parseString(address['state']) ?? '—';
  String get pincode => parseString(address['pincode']) ?? '—';
  String get serviceRadius => address['serviceRadius'] != null ? '${address['serviceRadius']} km' : '—';

  // Skills & Experience info
  String get experienceYears => skills['experienceYears'] != null ? '${skills['experienceYears']} Years' : '—';
  String get vehicleType => parseString(skills['vehicleType'])?.replaceAll('_', ' ') ?? '—';
  String get licenseNumber => parseString(skills['licenseNumber']) ?? 'Not specified';

  // Bank details
  String get bankAccountHolder => parseString(bank['accountHolder']) ?? 'N/A';
  String get bankAccountNumber => parseString(bank['accountNumber']) ?? '';
  String get maskedBankAccount {
    final num = bankAccountNumber;
    if (num.isEmpty) return 'N/A';
    if (num.length <= 4) return num;
    return '••••${num.substring(num.length - 4)}';
  }
  String get bankIfsc => parseString(bank['ifsc']) ?? 'N/A';
  String get bankUpiId => parseString(bank['upiId']) ?? 'N/A';

  // Audit notes
  String get correctionNotes => parseString(onboardingData['correction_notes']) ?? '';
  String get rejectionNotes => parseString(onboardingData['rejection_reason']) ?? '';
  String? get approvedBy => parseString(onboardingData['approved_by']);
  DateTime? get approvedAt => parseDateTime(onboardingData['approved_at']);

  // Counts
  List<AdminServiceItem> get approvedServices =>
      allRequestedServices.where((s) => s.isApproved).toList();

  int get approvedServicesCount => approvedServices.length;

  int get requestedServicesCount => allRequestedServices.length;

  int get pendingServicesCount =>
      allRequestedServices.where((s) => s.isPending).length;

  int get rejectedServicesCount =>
      allRequestedServices.where((s) => s.isRejected).length;

  int get uploadedDocumentsCount {
    if (documentsList.isNotEmpty) return documentsList.length;
    final docs = documentsStatus.isNotEmpty
        ? documentsStatus
        : (onboardingData['documents'] is Map<String, dynamic>
            ? onboardingData['documents'] as Map<String, dynamic>
            : const <String, dynamic>{});
    return docs.length;
  }

  int get verifiedDocumentsCount {
    if (documentsList.isNotEmpty) {
      return documentsList.where((d) => d.isApproved).length;
    }
    var count = 0;
    final docs = documentsStatus.isNotEmpty
        ? documentsStatus
        : (onboardingData['documents'] is Map<String, dynamic>
            ? onboardingData['documents'] as Map<String, dynamic>
            : const <String, dynamic>{});

    for (final doc in docs.values) {
      if (doc is Map<String, dynamic>) {
        final st = parseString(doc['status'])?.toLowerCase();
        if (st == 'approved') count++;
      }
    }
    return count;
  }

  int get pendingDocumentsCount {
    if (documentsList.isNotEmpty) {
      return documentsList.where((d) => d.isPending).length;
    }
    var count = 0;
    final docs = documentsStatus.isNotEmpty
        ? documentsStatus
        : (onboardingData['documents'] is Map<String, dynamic>
            ? onboardingData['documents'] as Map<String, dynamic>
            : const <String, dynamic>{});

    for (final doc in docs.values) {
      if (doc is Map<String, dynamic>) {
        final st = parseString(doc['status'])?.toLowerCase();
        if (st == 'pending' || st == 'submitted') count++;
      }
    }
    return count;
  }

  int get rejectedDocumentsCount {
    if (documentsList.isNotEmpty) {
      return documentsList.where((d) => d.isRejected).length;
    }
    var count = 0;
    final docs = documentsStatus.isNotEmpty
        ? documentsStatus
        : (onboardingData['documents'] is Map<String, dynamic>
            ? onboardingData['documents'] as Map<String, dynamic>
            : const <String, dynamic>{});

    for (final doc in docs.values) {
      if (doc is Map<String, dynamic>) {
        final st = parseString(doc['status'])?.toLowerCase();
        if (st == 'rejected') count++;
      }
    }
    return count;
  }
}
