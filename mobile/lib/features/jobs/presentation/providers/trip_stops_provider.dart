import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/job_actions_repository.dart';
import '../../domain/trip_stop.dart';

/// The stop list and current leg for one logistics job, straight from
/// `GET /workforce/jobs/{id}/stops/`.
///
/// Deliberately server-sourced rather than kept in app state: a driver's
/// phone dies mid-trip, or the app is killed by the OS between LOADING and
/// EN_ROUTE_DROP, far more often than anyone would like. Rebuilding the
/// whole trip view from this provider on every open means a restart lands
/// the driver exactly where they were, with no local snapshot to go stale
/// or disagree with the customer's tracking screen.
///
/// `autoDispose` + `family` matches preServiceStatusProvider: one entry per
/// job, released when the detail screen is popped. Callers invalidate it
/// after any action that could have moved the trip.
final tripStopsProvider =
    FutureProvider.autoDispose.family<TripStopsSnapshot, int>((ref, jobId) async {
  return ref.watch(jobActionsRepositoryProvider).fetchTripStops(jobId);
});
