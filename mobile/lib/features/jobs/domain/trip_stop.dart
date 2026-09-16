import '../../../core/utils/json_parsing.dart';

/// The five legs of a Goods & Transport trip, in order.
///
/// This list is a deliberate mirror of `LEG_SEQUENCE` in the vendor
/// backend's `workforce_api/services/logistics_events.py` (and of
/// `ServiceRequest.LEG_SEQUENCE` in the Customer app). The ordering is not
/// decoration: the backend refuses any move that would take a trip
/// backwards, so the app must know the same order to avoid offering the
/// driver a button the server will reject.
///
/// Legs are NOT job statuses. `job.status` still moves
/// accepted -> in_progress -> proof_submitted -> completed; the leg is the
/// finer-grained "where is the truck right now" that only logistics jobs
/// have.
const List<String> kLogisticsLegSequence = [
  'EN_ROUTE_PICKUP',
  'LOADING',
  'EN_ROUTE_DROP',
  'UNLOADING',
  'DELIVERED',
];

/// Position of [leg] in the trip, or -1 for a blank/unknown value —
/// matches `leg_rank()` on the backend.
int logisticsLegRank(String? leg) {
  if (leg == null || leg.isEmpty) return -1;
  return kLogisticsLegSequence.indexOf(leg.trim().toUpperCase());
}

/// Whether the backend would accept moving from [current] to [target].
/// Repeats are allowed (the server treats them as idempotent no-ops); only
/// backwards moves are refused.
bool canAdvanceLeg(String? current, String target) {
  final targetRank = logisticsLegRank(target);
  if (targetRank < 0) return false;
  final currentRank = logisticsLegRank(current);
  if (currentRank < 0) return true;
  return targetRank >= currentRank;
}

/// Driver-facing name for a leg.
String logisticsLegLabel(String? leg) {
  switch ((leg ?? '').trim().toUpperCase()) {
    case 'EN_ROUTE_PICKUP':
      return 'On the way to pickup';
    case 'LOADING':
      return 'Loading goods';
    case 'EN_ROUTE_DROP':
      return 'On the way to drop';
    case 'UNLOADING':
      return 'Unloading goods';
    case 'DELIVERED':
      return 'Delivered';
    default:
      return 'Trip not started';
  }
}

/// The label on the button that MOVES the trip into a leg. Every one of
/// these is an explicit driver tap — the app never infers LOADING,
/// EN_ROUTE_DROP or UNLOADING from arrival, GPS or elapsed time, because
/// only the driver knows when loading actually began.
String logisticsLegActionLabel(String leg) {
  switch (leg.trim().toUpperCase()) {
    case 'EN_ROUTE_PICKUP':
      return 'START TRIP TO PICKUP';
    case 'LOADING':
      return 'START LOADING';
    case 'EN_ROUTE_DROP':
      return 'START TRIP TO DROP';
    case 'UNLOADING':
      return 'START UNLOADING';
    case 'DELIVERED':
      return 'MARK DELIVERED';
    default:
      return leg;
  }
}

/// One stop on a multi-stop trip.
///
/// Mirrors an entry of `results` from `GET /workforce/jobs/{id}/stops/`
/// (WorkforceJobTripStopsView).
class TripStop {
  const TripStop({
    required this.id,
    required this.sequence,
    required this.stopType,
    this.address,
    this.contactName,
    this.contactPhone,
    this.latitude,
    this.longitude,
    this.notes,
    this.arrivedAt,
    this.completedAt,
  });

  factory TripStop.fromJson(Map<String, dynamic> json) {
    return TripStop(
      id: parseInt(json['id']) ?? 0,
      sequence: parseInt(json['sequence']) ?? 0,
      stopType: parseString(json['stop_type']) ?? 'stop',
      address: parseString(json['address']),
      contactName: parseString(json['contact_name']),
      contactPhone: parseString(json['contact_phone']),
      latitude: parseDouble(json['latitude']),
      longitude: parseDouble(json['longitude']),
      notes: parseString(json['notes']),
      arrivedAt: parseDateTime(json['arrived_at']),
      completedAt: parseDateTime(json['completed_at']),
    );
  }

  final int id;
  final int sequence;
  final String stopType;
  final String? address;
  final String? contactName;
  final String? contactPhone;
  final double? latitude;
  final double? longitude;
  final String? notes;
  final DateTime? arrivedAt;
  final DateTime? completedAt;

  bool get hasArrived => arrivedAt != null;
  bool get isCompleted => completedAt != null;
  bool get hasCoordinates => latitude != null && longitude != null;

  bool get isPickup => stopType.toLowerCase().contains('pickup');
  bool get isDrop =>
      stopType.toLowerCase().contains('drop') ||
      stopType.toLowerCase().contains('delivery');

  String get typeLabel {
    if (isPickup) return 'Pickup';
    if (isDrop) return 'Drop';
    return 'Stop';
  }
}

/// What `GET /workforce/jobs/{id}/stops/` returns as a whole: the stop list
/// plus the trip's current leg.
///
/// The leg is carried here as well as on the job so a screen that has just
/// refreshed the stops does not also have to refresh the whole job list to
/// notice the trip moved — and, more importantly, so that after an app
/// restart the driver's view is rebuilt entirely from the server rather
/// than from anything the app remembered locally.
class TripStopsSnapshot {
  const TripStopsSnapshot({required this.logisticsLeg, required this.stops});

  factory TripStopsSnapshot.fromJson(Map<String, dynamic> json) {
    final results = json['results'];
    return TripStopsSnapshot(
      logisticsLeg: parseString(json['logistics_leg']),
      stops: results is List
          ? results.whereType<Map<String, dynamic>>().map(TripStop.fromJson).toList()
          : const <TripStop>[],
    );
  }

  static const empty = TripStopsSnapshot(logisticsLeg: null, stops: <TripStop>[]);

  final String? logisticsLeg;
  final List<TripStop> stops;

  bool get isEmpty => stops.isEmpty;

  /// The stop the driver should be working on next: the first one not yet
  /// completed. Null once every stop is done.
  TripStop? get nextStop {
    for (final stop in stops) {
      if (!stop.isCompleted) return stop;
    }
    return null;
  }
}

/// Result of `POST /workforce/jobs/{id}/logistics-leg/`.
///
/// [changed] is false when the server treated the request as an idempotent
/// repeat of the leg the trip is already on — which is exactly what happens
/// when the driver retries after a request that actually succeeded but
/// whose response was lost. Not an error, and specifically not something to
/// surface as one.
class LogisticsLegResult {
  const LogisticsLegResult({
    required this.logisticsLeg,
    required this.changed,
    this.updatedAt,
  });

  factory LogisticsLegResult.fromJson(Map<String, dynamic> json) {
    return LogisticsLegResult(
      logisticsLeg: parseString(json['logistics_leg']),
      changed: parseBool(json['changed']),
      updatedAt: parseDateTime(json['logistics_leg_updated_at']),
    );
  }

  final String? logisticsLeg;
  final bool changed;
  final DateTime? updatedAt;
}

/// Result of `POST /workforce/jobs/{id}/stops/`.
///
/// Same idempotency contract as [LogisticsLegResult]: the backend never
/// rewrites a timestamp it already recorded, so [changed] being false means
/// "already recorded", not "failed".
class TripStopProgressResult {
  const TripStopProgressResult({
    required this.stopId,
    required this.sequence,
    required this.changed,
    this.arrivedAt,
    this.completedAt,
  });

  factory TripStopProgressResult.fromJson(Map<String, dynamic> json) {
    return TripStopProgressResult(
      stopId: parseInt(json['stop_id']) ?? 0,
      sequence: parseInt(json['sequence']) ?? 0,
      changed: parseBool(json['changed']),
      arrivedAt: parseDateTime(json['arrived_at']),
      completedAt: parseDateTime(json['completed_at']),
    );
  }

  final int stopId;
  final int sequence;
  final bool changed;
  final DateTime? arrivedAt;
  final DateTime? completedAt;
}
