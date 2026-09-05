import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/job_payment.dart';
import '../domain/pre_service_status.dart';
import '../domain/trip_stop.dart';
import 'job_actions_api.dart';

class JobActionsRepository {
  JobActionsRepository(this._api);

  final JobActionsApi _api;

  Future<String> acceptOffer(int jobId) async {
    final json = await _api.acceptOffer(jobId);
    return _message(json, 'Job offer accepted.');
  }

  Future<String> rejectOffer(int jobId, String reason) async {
    final json = await _api.rejectOffer(jobId, reason);
    return _message(json, 'Job offer declined.');
  }

  Future<String> cancelJob(int jobId, {required String reasonCode, String reasonDetail = ''}) async {
    final json = await _api.cancelJob(jobId, reasonCode: reasonCode, reasonDetail: reasonDetail);
    return _message(json, 'Job assignment cancelled.');
  }

  Future<String> verifyArrival(int jobId, {required double lat, required double lon}) async {
    final json = await _api.verifyArrival(jobId, lat: lat, lon: lon);
    return _message(json, 'Arrival verified.');
  }

  Future<PreServiceStatus> fetchPreServiceStatus(int jobId) async {
    final json = await _api.fetchPreServiceStatus(jobId);
    return PreServiceStatus.fromJson(json);
  }

  Future<String> verifyOtp(int jobId, String otp) async {
    final json = await _api.verifyOtp(jobId, otp);
    return _message(json, 'OTP verified.');
  }

  Future<String> resendOtp(int jobId) async {
    final json = await _api.resendOtp(jobId);
    return _message(json, 'A fresh OTP has been sent to the customer.');
  }

  Future<String> uploadPreServicePhoto(
    int jobId, {
    required PreServicePhotoType photoType,
    required String filePath,
  }) async {
    final json = await _api.uploadPreServicePhoto(
      jobId,
      photoType: photoType.apiValue,
      filePath: filePath,
    );
    return _message(json, 'Photo uploaded.');
  }

  Future<String> uploadProof(
    int jobId, {
    required String afterPresencePhotoPath,
    String? afterAppliancePhotoPath,
    String? afterWorkAreaPhotoPath,
    String? notes,
    String? recipientName,
    String? recipientPhone,
    int? stopId,
    double? latitude,
    double? longitude,
  }) async {
    final json = await _api.uploadProof(
      jobId,
      afterPresencePhotoPath: afterPresencePhotoPath,
      afterAppliancePhotoPath: afterAppliancePhotoPath,
      afterWorkAreaPhotoPath: afterWorkAreaPhotoPath,
      notes: notes,
      recipientName: recipientName,
      recipientPhone: recipientPhone,
      stopId: stopId,
      latitude: latitude,
      longitude: longitude,
    );
    return _message(json, 'Completion proof submitted.');
  }

  // ---------------------------------------------------------------------
  // Goods & Transport trip
  // ---------------------------------------------------------------------

  Future<TripStopsSnapshot> fetchTripStops(int jobId) async {
    final json = await _api.fetchTripStops(jobId);
    return TripStopsSnapshot.fromJson(json);
  }

  /// Advance the trip to [leg].
  ///
  /// Refuses locally, without a request, any move the backend would reject
  /// as backwards. That is not a substitute for the server rule -- the
  /// server stays the authority and the UI never offers such a button
  /// anyway -- it just stops a stale screen from firing a request that can
  /// only fail.
  Future<LogisticsLegResult> setLogisticsLeg(
    int jobId,
    String leg, {
    String? currentLeg,
  }) async {
    if (currentLeg != null && !canAdvanceLeg(currentLeg, leg)) {
      throw ArgumentError(
        'Cannot move the trip backwards from $currentLeg to $leg.',
      );
    }
    final json = await _api.setLogisticsLeg(jobId, leg);
    return LogisticsLegResult.fromJson(json);
  }

  Future<TripStopProgressResult> updateTripStop(
    int jobId, {
    required int stopId,
    required bool completed,
  }) async {
    final json = await _api.updateTripStop(jobId, stopId: stopId, completed: completed);
    return TripStopProgressResult.fromJson(json);
  }

  Future<JobPaymentInfo> fetchPayment(int jobId) async {
    final json = await _api.fetchPayment(jobId);
    final paymentJson = json['payment'];
    return JobPaymentInfo.fromJson(
      paymentJson is Map<String, dynamic> ? paymentJson : json,
    );
  }

  Future<String> collectCash(int jobId, double amountReceived) async {
    final json = await _api.collectCash(jobId, amountReceived);
    return _message(json, 'Cash collection recorded.');
  }

  Future<String> verifyPaymentOtp(int jobId, String otp) async {
    final json = await _api.verifyPaymentOtp(jobId, otp);
    return _message(json, 'Payment verified.');
  }

  String _message(Map<String, dynamic> json, String fallback) {
    return json['message'] as String? ?? fallback;
  }
}

final jobActionsRepositoryProvider = Provider<JobActionsRepository>((ref) {
  return JobActionsRepository(ref.watch(jobActionsApiProvider));
});
