import '../../../core/utils/json_parsing.dart';

/// Mirrors `active_offer` inside a job, from WorkforceJobSerializer.
class JobOffer {
  const JobOffer({this.status, this.offeredAt, this.expiresAt, required this.isExpired});

  factory JobOffer.fromJson(Map<String, dynamic> json) {
    return JobOffer(
      status: parseString(json['status']),
      offeredAt: parseDateTime(json['offered_at']),
      expiresAt: parseDateTime(json['expires_at']),
      isExpired: parseBool(json['is_expired']),
    );
  }

  final String? status;
  final DateTime? offeredAt;
  final DateTime? expiresAt;
  final bool isExpired;
}

/// Mirrors `cancellation_info` inside a job.
class JobCancellationInfo {
  const JobCancellationInfo({
    required this.canCancel,
    this.acceptedAt,
    this.cancellationDeadline,
    this.remainingSeconds,
  });

  factory JobCancellationInfo.fromJson(Map<String, dynamic> json) {
    return JobCancellationInfo(
      canCancel: parseBool(json['can_cancel']),
      acceptedAt: parseDateTime(json['accepted_at']),
      cancellationDeadline: parseDateTime(json['cancellation_deadline']),
      remainingSeconds: parseInt(json['remaining_seconds']),
    );
  }

  final bool canCancel;
  final DateTime? acceptedAt;
  final DateTime? cancellationDeadline;
  final int? remainingSeconds;
}

/// One booked service / item from `cart_data` in ServiceRequest.
class JobCartItem {
  const JobCartItem({
    required this.name,
    this.description,
    this.selectedOption,
    this.quantity,
  });

  factory JobCartItem.fromJson(Map<String, dynamic> json) {
    return JobCartItem(
      name: parseString(json['name']) ??
          parseString(json['title']) ??
          parseString(json['service_name']) ??
          'Service Item',
      description: parseString(json['description']),
      selectedOption: parseString(json['selectedOption']) ??
          parseString(json['option']) ??
          parseString(json['variant']),
      quantity: parseInt(json['quantity']),
    );
  }

  final String name;
  final String? description;
  final String? selectedOption;
  final int? quantity;
}

/// Mirrors the fields WorkforceJobSerializer returns for
/// `GET /workforce/jobs/?status=active|completed` (backend/workforce_api/serializers.py).
class Job {
  const Job({
    required this.id,
    required this.requestId,
    this.customerName,
    this.phone,
    this.email,
    this.serviceCategory,
    this.issueTitle,
    this.serviceTitle,
    this.description,
    required this.status,
    this.priority,
    this.address,
    this.latitude,
    this.longitude,
    this.distanceKm,
    this.preferredDate,
    this.preferredTime,
    this.totalAmount,
    this.paymentStatus,
    this.paymentMethod,
    this.activeOffer,
    this.cancellationInfo,
    this.cartData = const [],
    this.createdAt,
    required this.isOffer,
    required this.isAcceptedByCurrentEmployee,
    required this.isAssignedToCurrentEmployee,
    this.acceptedAt,
    this.cancellationDeadline,
    this.offerExpiresAt,
    required this.canCancel,
    this.isLogistics = false,
    this.dropAddress,
    this.dropLatitude,
    this.dropLongitude,
    this.dropContactName,
    this.dropContactPhone,
    this.logisticsLeg,
    this.logisticsLegUpdatedAt,
    this.tripStopCount = 0,
  });

  factory Job.fromJson(Map<String, dynamic> json) {
    final activeOfferJson = json['active_offer'];
    final cancellationJson = json['cancellation_info'];
    final cartJson = json['cart_data'];

    return Job(
      id: parseInt(json['id']) ?? 0,
      requestId: parseString(json['request_id']) ?? '#${json['id']}',
      customerName: parseString(json['customer_name']) ??
          parseString(json['customer_display_name']),
      phone: parseString(json['phone']),
      email: parseString(json['email']),
      serviceCategory: parseString(json['service_category']),
      issueTitle: parseString(json['issue_title']),
      serviceTitle: parseString(json['service_title']),
      description: parseString(json['description']),
      status: parseString(json['status']) ?? 'unknown',
      priority: parseString(json['priority']),
      address: parseString(json['address']),
      latitude: parseDouble(json['latitude']),
      longitude: parseDouble(json['longitude']),
      distanceKm: parseDouble(json['distance_km']),
      preferredDate: parseString(json['preferred_date']),
      preferredTime: parseString(json['preferred_time']),
      totalAmount: parseDouble(json['total_amount']),
      paymentStatus: parseString(json['payment_status']),
      paymentMethod: parseString(json['payment_method']),
      activeOffer: activeOfferJson is Map<String, dynamic>
          ? JobOffer.fromJson(activeOfferJson)
          : null,
      cancellationInfo: cancellationJson is Map<String, dynamic>
          ? JobCancellationInfo.fromJson(cancellationJson)
          : null,
      cartData: cartJson is List
          ? cartJson.whereType<Map<String, dynamic>>().map(JobCartItem.fromJson).toList()
          : const [],
      createdAt: parseDateTime(json['created_at']),
      isOffer: parseBool(json['is_offer']),
      isAcceptedByCurrentEmployee: parseBool(json['is_accepted_by_current_employee']),
      isAssignedToCurrentEmployee: parseBool(json['is_assigned_to_current_employee']),
      acceptedAt: parseDateTime(json['accepted_at']),
      cancellationDeadline: parseDateTime(json['cancellation_deadline']),
      offerExpiresAt: parseDateTime(json['offer_expires_at']),
      canCancel: parseBool(json['can_cancel']),
      isLogistics: parseBool(json['is_logistics']),
      dropAddress: parseString(json['drop_address']),
      dropLatitude: parseDouble(json['drop_latitude']),
      dropLongitude: parseDouble(json['drop_longitude']),
      dropContactName: parseString(json['drop_contact_name']),
      dropContactPhone: parseString(json['drop_contact_phone']),
      logisticsLeg: parseString(json['logistics_leg']),
      logisticsLegUpdatedAt: parseDateTime(json['logistics_leg_updated_at']),
      tripStopCount: parseInt(json['trip_stop_count']) ?? 0,
    );
  }

  final int id;
  final String requestId;
  final String? customerName;
  final String? phone;
  final String? email;
  final String? serviceCategory;
  final String? issueTitle;
  final String? serviceTitle;
  final String? description;
  final String status;
  final String? priority;
  final String? address;
  final double? latitude;
  final double? longitude;
  final double? distanceKm;
  final String? preferredDate;
  final String? preferredTime;
  final double? totalAmount;
  final String? paymentStatus;
  final String? paymentMethod;
  final JobOffer? activeOffer;
  final JobCancellationInfo? cancellationInfo;
  final List<JobCartItem> cartData;
  final DateTime? createdAt;
  final bool isOffer;
  final bool isAcceptedByCurrentEmployee;
  final bool isAssignedToCurrentEmployee;
  final DateTime? acceptedAt;
  final DateTime? cancellationDeadline;
  final DateTime? offerExpiresAt;
  final bool canCancel;

  // ── Goods & Transport ────────────────────────────────────────────────
  // A logistics job has a second location. Until these were added the
  // driver app could show where to collect from but not where to deliver
  // to, and had no idea which leg of the trip it was on -- the leg and
  // stop endpoints existed on the backend but nothing in the job payload
  // told the app they applied.

  /// True when the backend classifies this job's service category as
  /// logistics (mini truck / two wheeler / packers & movers). Comes from
  /// the server so the app never has to keep its own copy of the category
  /// list and drift out of step with dispatch.
  final bool isLogistics;
  final String? dropAddress;
  final double? dropLatitude;
  final double? dropLongitude;
  final String? dropContactName;
  final String? dropContactPhone;

  /// Current trip leg -- one of kLogisticsLegSequence, or null before the
  /// trip starts. Server-owned: the app displays it and asks the server to
  /// change it, and never advances it locally.
  final String? logisticsLeg;
  final DateTime? logisticsLegUpdatedAt;

  /// How many stops the trip has. 0 means a plain pickup -> drop run with
  /// no intermediate stops, in which case the app shows the pickup/drop
  /// pair instead of a stop list.
  final int tripStopCount;

  /// The service name shown in the UI — falls back through the fields the
  /// backend may leave blank depending on how the request was created.
  String get displayTitle => serviceTitle ?? issueTitle ?? serviceCategory ?? 'Service Request';

  bool get hasCoordinates => latitude != null && longitude != null;

  bool get hasDropCoordinates => dropLatitude != null && dropLongitude != null;

  bool get hasMultipleStops => tripStopCount > 0;
}

/// Statuses that count as "an active workload" — a job the technician is
/// actively assigned to and working through. Mirrors
/// ACTIVE_QUEUE_STATUSES in the web app's EmployeeRuntimeContext.jsx.
const List<String> kActiveQueueStatuses = [
  'assigned',
  'accepted',
  'on_the_way',
  'en_route',
  'arrived',
  'in_progress',
  'proof_submitted',
];

