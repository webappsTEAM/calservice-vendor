import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/location/navigation_launcher.dart';
import '../../../../core/network/api_error.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/loading_button.dart';
import '../../data/job_actions_repository.dart';
import '../../domain/job.dart';
import '../../domain/trip_stop.dart';
import '../jobs_providers.dart';
import '../providers/trip_stops_provider.dart';
import 'proof_submission_sheet.dart';

/// The driver's view of a Goods & Transport trip, and how they advance it.
///
/// Three rules shape this widget:
///
/// 1. **Every leg is an explicit tap.** LOADING, EN_ROUTE_DROP and
///    UNLOADING are never inferred from arrival, GPS proximity or elapsed
///    time. Only the driver knows when loading actually started, and the
///    customer's tracking screen and the fare reconciliation both depend on
///    these timestamps being real. The one leg the app does not offer as a
///    button is DELIVERED: the backend sets it when proof of delivery is
///    accepted, so there is no way to claim a delivery without evidence.
///
/// 2. **The server owns the state.** The leg and the stop timestamps are
///    read back from `GET /workforce/jobs/{id}/stops/` on every open and
///    after every action. Nothing about trip progress is cached locally, so
///    killing the app mid-trip and reopening it lands the driver exactly
///    where they were.
///
/// 3. **Retrying is safe.** Both endpoints are idempotent server-side: a
///    repeated leg returns `changed: false` without a duplicate history
///    entry or a duplicate customer event, and a repeated stop update never
///    rewrites a timestamp already recorded. So a request that fails on a
///    patchy mobile connection is simply offered again -- including the
///    case where it actually succeeded and only the response was lost.
class LogisticsTripSection extends ConsumerStatefulWidget {
  const LogisticsTripSection({super.key, required this.job});

  final Job job;

  @override
  ConsumerState<LogisticsTripSection> createState() => _LogisticsTripSectionState();
}

class _LogisticsTripSectionState extends ConsumerState<LogisticsTripSection> {
  /// Which action is in flight, so two taps can't race each other. Null
  /// when idle. Keyed by action so the right button shows the spinner.
  String? _busy;
  String? _error;
  String? _info;

  void _setError(String message) {
    if (!mounted) return;
    setState(() {
      _error = message;
      _info = null;
    });
  }

  void _setInfo(String message) {
    if (!mounted) return;
    setState(() {
      _info = message;
      _error = null;
    });
  }

  /// Re-read trip state from the server. Called after every action rather
  /// than patching local state from the response, so what the driver sees
  /// is always what the backend actually recorded.
  Future<void> _refresh() async {
    ref.invalidate(tripStopsProvider(widget.job.id));
    ref.invalidate(activeJobsProvider);
    try {
      await ref.read(tripStopsProvider(widget.job.id).future);
    } catch (_) {
      // A failed refresh must not look like a failed action -- the action
      // itself already succeeded. The provider surfaces its own error.
    }
  }

  Future<void> _advanceLeg(String leg, String? currentLeg) async {
    if (_busy != null) return;
    setState(() {
      _busy = 'leg:$leg';
      _error = null;
      _info = null;
    });
    try {
      final result = await ref
          .read(jobActionsRepositoryProvider)
          .setLogisticsLeg(widget.job.id, leg, currentLeg: currentLeg);
      await _refresh();
      if (!mounted) return;
      if (result.changed) {
        _setInfo('Trip updated: ${logisticsLegLabel(result.logisticsLeg)}.');
      } else {
        // Idempotent repeat -- the common outcome of retrying a request
        // whose response was lost. Confirm rather than warn.
        _setInfo('Already recorded: ${logisticsLegLabel(result.logisticsLeg)}.');
      }
    } on ArgumentError catch (e) {
      _setError('${e.message}');
      await _refresh();
    } on DioException catch (e) {
      _setError(describeDioError(e, fallback: 'Could not update the trip. Tap to try again.'));
    } catch (_) {
      _setError('Could not update the trip. Tap to try again.');
    } finally {
      if (mounted) setState(() => _busy = null);
    }
  }

  Future<void> _markStop(TripStop stop, {required bool completed}) async {
    if (_busy != null) return;
    final key = 'stop:${stop.id}:$completed';
    setState(() {
      _busy = key;
      _error = null;
      _info = null;
    });
    try {
      final result = await ref
          .read(jobActionsRepositoryProvider)
          .updateTripStop(widget.job.id, stopId: stop.id, completed: completed);
      await _refresh();
      if (!mounted) return;
      final what = completed ? 'completed' : 'arrival';
      if (result.changed) {
        _setInfo('Stop ${stop.sequence} $what recorded.');
      } else {
        _setInfo('Stop ${stop.sequence} $what was already recorded.');
      }
    } on DioException catch (e) {
      _setError(describeDioError(e, fallback: 'Could not update the stop. Tap to try again.'));
    } catch (_) {
      _setError('Could not update the stop. Tap to try again.');
    } finally {
      if (mounted) setState(() => _busy = null);
    }
  }

  Future<void> _navigate(double lat, double lon) async {
    final launched = await launchNavigation(destinationLat: lat, destinationLon: lon);
    if (!launched && mounted) {
      _setError('Could not open a maps app for navigation.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final job = widget.job;
    final snapshotAsync = ref.watch(tripStopsProvider(job.id));
    final snapshot = snapshotAsync.valueOrNull;

    // The stops response carries the leg too and is refreshed on every
    // action, so prefer it over the copy on the job -- which is only as
    // fresh as the last job-list fetch.
    final leg = snapshot?.logisticsLeg ?? job.logisticsLeg;
    final stops = snapshot?.stops ?? const <TripStop>[];

    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.local_shipping_rounded, size: 18, color: AppColors.primary),
              const SizedBox(width: AppSpacing.sm),
              const Expanded(
                child: Text(
                  'TRIP PROGRESS',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.5,
                    color: Color(0xFF475569),
                  ),
                ),
              ),
              if (snapshotAsync.isLoading)
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              else
                IconButton(
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                  icon: const Icon(Icons.refresh_rounded, size: 18),
                  tooltip: 'Refresh trip state',
                  onPressed: _busy != null ? null : _refresh,
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),

          _LegTimeline(currentLeg: leg),

          if (snapshotAsync.hasError) ...[
            const SizedBox(height: AppSpacing.sm),
            const _Notice(
              message:
                  'Could not load the latest trip state. The steps below still work — '
                  'they are checked on the server.',
              tone: _NoticeTone.warning,
            ),
          ],

          const SizedBox(height: AppSpacing.md),

          // Pickup and drop, always shown: on a logistics job the drop is
          // half the assignment, and before this existed the app showed
          // only the pickup address.
          _LocationCard(
            label: 'PICKUP',
            icon: Icons.trip_origin_rounded,
            color: const Color(0xFF2563EB),
            address: job.address,
            contactName: job.customerName,
            contactPhone: job.phone,
            onNavigate: job.hasCoordinates
                ? () => _navigate(job.latitude!, job.longitude!)
                : null,
          ),
          const SizedBox(height: AppSpacing.sm),
          _LocationCard(
            label: 'DROP',
            icon: Icons.place_rounded,
            color: const Color(0xFF059669),
            address: job.dropAddress,
            contactName: job.dropContactName,
            contactPhone: job.dropContactPhone,
            onNavigate: job.hasDropCoordinates
                ? () => _navigate(job.dropLatitude!, job.dropLongitude!)
                : null,
          ),

          if (stops.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            const Text(
              'STOPS ON THIS TRIP',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w900,
                letterSpacing: 0.5,
                color: Color(0xFF475569),
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            for (final stop in stops) ...[
              _StopTile(
                stop: stop,
                busyKey: _busy,
                onNavigate: stop.hasCoordinates
                    ? () => _navigate(stop.latitude!, stop.longitude!)
                    : null,
                onArrived: () => _markStop(stop, completed: false),
                onCompleted: () => _markStop(stop, completed: true),
              ),
              const SizedBox(height: AppSpacing.xs),
            ],
          ],

          const SizedBox(height: AppSpacing.md),

          if (_error != null)
            _Notice(message: _error!, tone: _NoticeTone.error)
          else if (_info != null)
            _Notice(message: _info!, tone: _NoticeTone.info),

          if (_error != null || _info != null) const SizedBox(height: AppSpacing.sm),

          ..._buildLegActions(context, job, leg),
        ],
      ),
    );
  }

  /// The next trip step, as an explicit button.
  ///
  /// Only ever the single immediate next leg: offering a driver "skip to
  /// unloading" invites a tap that records loading and driving that never
  /// happened. The backend tolerates a forward skip (a driver who never
  /// signalled LOADING should not be stuck), but the app does not encourage
  /// one.
  List<Widget> _buildLegActions(BuildContext context, Job job, String? leg) {
    final currentRank = logisticsLegRank(leg);
    final deliveredRank = kLogisticsLegSequence.indexOf('DELIVERED');

    if (currentRank >= deliveredRank) {
      return [
        const _Notice(
          message: 'This trip is delivered. Proof of delivery has been recorded.',
          tone: _NoticeTone.success,
        ),
      ];
    }

    final nextRank = currentRank + 1;

    // Past UNLOADING the next step is not a leg at all -- it is proof of
    // delivery, which is what sets DELIVERED on the server.
    if (nextRank >= deliveredRank) {
      return [
        const _Notice(
          message:
              'Unloading in progress. Capture proof of delivery to finish the trip — '
              'the delivery is marked complete only once proof is accepted.',
          tone: _NoticeTone.info,
        ),
        const SizedBox(height: AppSpacing.sm),
        LoadingButton(
          label: 'CAPTURE PROOF OF DELIVERY',
          icon: Icons.assignment_turned_in_rounded,
          isLoading: false,
          onPressed: _busy != null
              ? null
              : () async {
                  final submitted = await ProofSubmissionSheet.show(context, job);
                  if (submitted == true) await _refresh();
                },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.emerald,
            foregroundColor: Colors.white,
            minimumSize: const Size.fromHeight(46),
            textStyle: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.5,
            ),
          ),
        ),
      ];
    }

    final nextLeg = kLogisticsLegSequence[nextRank];
    return [
      LoadingButton(
        label: logisticsLegActionLabel(nextLeg),
        icon: Icons.arrow_forward_rounded,
        isLoading: _busy == 'leg:$nextLeg',
        onPressed: _busy != null ? null : () => _advanceLeg(nextLeg, leg),
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(46),
          textStyle: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
      ),
      const SizedBox(height: AppSpacing.xs),
      Text(
        'Tap when you actually start this step — the customer sees it live.',
        textAlign: TextAlign.center,
        style: TextStyle(fontSize: 10.5, color: AppColors.textSecondary),
      ),
    ];
  }
}

/// The five legs as a compact progress strip.
class _LegTimeline extends StatelessWidget {
  const _LegTimeline({required this.currentLeg});

  final String? currentLeg;

  @override
  Widget build(BuildContext context) {
    final currentRank = logisticsLegRank(currentLeg);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            for (var i = 0; i < kLogisticsLegSequence.length; i++) ...[
              Expanded(
                child: Container(
                  height: 6,
                  decoration: BoxDecoration(
                    color: i <= currentRank ? AppColors.primary : const Color(0xFFE2E8F0),
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
              ),
              if (i < kLogisticsLegSequence.length - 1) const SizedBox(width: 3),
            ],
          ],
        ),
        const SizedBox(height: 6),
        Text(
          currentRank < 0
              ? 'Trip not started'
              : 'Step ${currentRank + 1} of ${kLogisticsLegSequence.length} — '
                  '${logisticsLegLabel(currentLeg)}',
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFF334155)),
        ),
      ],
    );
  }
}

class _LocationCard extends StatelessWidget {
  const _LocationCard({
    required this.label,
    required this.icon,
    required this.color,
    required this.address,
    required this.contactName,
    required this.contactPhone,
    required this.onNavigate,
  });

  final String label;
  final IconData icon;
  final Color color;
  final String? address;
  final String? contactName;
  final String? contactPhone;
  final VoidCallback? onNavigate;

  @override
  Widget build(BuildContext context) {
    final hasAddress = address != null && address!.trim().isNotEmpty;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(AppRadius.chip),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.6,
                    color: color,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  // Never invent an address. If the booking has no drop
                  // address the driver is told so plainly rather than shown
                  // a blank line they might read as "same as pickup".
                  hasAddress ? address!.trim() : 'Not provided on this booking',
                  style: TextStyle(
                    fontSize: 12.5,
                    height: 1.3,
                    fontStyle: hasAddress ? FontStyle.normal : FontStyle.italic,
                    color: hasAddress ? const Color(0xFF1E293B) : AppColors.textSecondary,
                  ),
                ),
                if ((contactName != null && contactName!.trim().isNotEmpty) ||
                    (contactPhone != null && contactPhone!.trim().isNotEmpty)) ...[
                  const SizedBox(height: 3),
                  Text(
                    [
                      if (contactName != null && contactName!.trim().isNotEmpty) contactName!.trim(),
                      if (contactPhone != null && contactPhone!.trim().isNotEmpty) contactPhone!.trim(),
                    ].join(' · '),
                    style: TextStyle(fontSize: 11.5, color: AppColors.textSecondary),
                  ),
                ],
              ],
            ),
          ),
          if (onNavigate != null)
            IconButton(
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
              icon: const Icon(Icons.directions_rounded, size: 20),
              tooltip: 'Navigate',
              onPressed: onNavigate,
            ),
        ],
      ),
    );
  }
}

class _StopTile extends StatelessWidget {
  const _StopTile({
    required this.stop,
    required this.busyKey,
    required this.onNavigate,
    required this.onArrived,
    required this.onCompleted,
  });

  final TripStop stop;
  final String? busyKey;
  final VoidCallback? onNavigate;
  final VoidCallback onArrived;
  final VoidCallback onCompleted;

  @override
  Widget build(BuildContext context) {
    final done = stop.isCompleted;
    final arrived = stop.hasArrived;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: done ? const Color(0xFFF0FDF4) : AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(AppRadius.chip),
        border: Border.all(color: done ? const Color(0xFFBBF7D0) : AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 22,
                height: 22,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: done
                      ? AppColors.emerald
                      : (arrived ? AppColors.primary : const Color(0xFFCBD5E1)),
                  shape: BoxShape.circle,
                ),
                child: done
                    ? const Icon(Icons.check, size: 13, color: Colors.white)
                    : Text(
                        '${stop.sequence}',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w900,
                          color: Colors.white,
                        ),
                      ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      stop.typeLabel,
                      style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800),
                    ),
                    if (stop.address != null && stop.address!.trim().isNotEmpty)
                      Text(
                        stop.address!.trim(),
                        style: TextStyle(fontSize: 11.5, color: AppColors.textSecondary, height: 1.3),
                      ),
                    if (stop.contactName != null || stop.contactPhone != null)
                      Text(
                        [
                          if (stop.contactName != null) stop.contactName!,
                          if (stop.contactPhone != null) stop.contactPhone!,
                        ].join(' · '),
                        style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
                      ),
                  ],
                ),
              ),
              if (onNavigate != null)
                IconButton(
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 34, minHeight: 34),
                  icon: const Icon(Icons.directions_rounded, size: 18),
                  tooltip: 'Navigate to stop',
                  onPressed: onNavigate,
                ),
            ],
          ),
          if (!done) ...[
            const SizedBox(height: AppSpacing.xs),
            Row(
              children: [
                Expanded(
                  child: LoadingButton(
                    label: arrived ? 'ARRIVED ✓' : 'MARK ARRIVED',
                    filled: false,
                    isLoading: busyKey == 'stop:${stop.id}:false',
                    // Still tappable once arrived: the server keeps the
                    // first timestamp, so a driver who is unsure whether
                    // their tap registered can safely tap again.
                    onPressed: busyKey != null ? null : onArrived,
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(38),
                      textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.xs),
                Expanded(
                  child: LoadingButton(
                    label: 'MARK DONE',
                    isLoading: busyKey == 'stop:${stop.id}:true',
                    onPressed: busyKey != null ? null : onCompleted,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.emerald,
                      foregroundColor: Colors.white,
                      minimumSize: const Size.fromHeight(38),
                      textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

enum _NoticeTone { info, success, warning, error }

class _Notice extends StatelessWidget {
  const _Notice({required this.message, required this.tone});

  final String message;
  final _NoticeTone tone;

  @override
  Widget build(BuildContext context) {
    late final Color bg;
    late final Color fg;
    late final Color line;
    switch (tone) {
      case _NoticeTone.error:
        bg = const Color(0xFFFEE2E2);
        fg = const Color(0xFFB91C1C);
        line = const Color(0xFFFECDD3);
        break;
      case _NoticeTone.success:
        bg = const Color(0xFFECFDF5);
        fg = const Color(0xFF065F46);
        line = const Color(0xFFA7F3D0);
        break;
      case _NoticeTone.warning:
        bg = const Color(0xFFFEF3C7);
        fg = const Color(0xFF92400E);
        line = const Color(0xFFFDE68A);
        break;
      case _NoticeTone.info:
        bg = const Color(0xFFEFF6FF);
        fg = const Color(0xFF1E40AF);
        line = const Color(0xFFBFDBFE);
        break;
    }
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 8),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(AppRadius.chip),
        border: Border.all(color: line),
      ),
      child: Text(
        message,
        style: TextStyle(fontSize: 11.5, color: fg, fontWeight: FontWeight.w600, height: 1.35),
      ),
    );
  }
}
