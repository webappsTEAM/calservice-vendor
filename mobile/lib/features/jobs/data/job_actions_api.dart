import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

/// Every job-lifecycle action endpoint, verified against the web app's
/// api/workforceService.js and the backend views directly — no invented
/// paths or bodies. See job_actions_repository.dart for the typed layer on
/// top of this.
class JobActionsApi {
  JobActionsApi(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> acceptOffer(int jobId) async {
    final response = await _dio.post('/workforce/jobs/$jobId/accept-offer/');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> rejectOffer(int jobId, String reason) async {
    final response = await _dio.post(
      '/workforce/jobs/$jobId/reject-offer/',
      data: {'reason': reason},
    );
    return response.data as Map<String, dynamic>;
  }

  /// Matches the endpoint the web UI's cancel-assignment modal actually
  /// calls (`apiCancelJob` → `/cancel/`) — NOT `/cancel-assignment/`, which
  /// exists in the backend but is dead code on web.
  Future<Map<String, dynamic>> cancelJob(
    int jobId, {
    required String reasonCode,
    String reasonDetail = '',
  }) async {
    final response = await _dio.post(
      '/workforce/jobs/$jobId/cancel/',
      data: {'reason_code': reasonCode, 'reason_detail': reasonDetail},
    );
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> verifyArrival(
    int jobId, {
    required double lat,
    required double lon,
  }) async {
    final response = await _dio.post(
      '/workforce/jobs/$jobId/arrive/',
      data: {'lat': lat, 'lon': lon},
    );
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> fetchPreServiceStatus(int jobId) async {
    final response = await _dio.get('/workforce/jobs/$jobId/pre-service-status/');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> verifyOtp(int jobId, String otp) async {
    final response = await _dio.post(
      '/workforce/jobs/$jobId/verify-otp/',
      data: {'otp': otp},
    );
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> resendOtp(int jobId) async {
    final response = await _dio.post('/workforce/jobs/$jobId/resend-otp/');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> uploadPreServicePhoto(
    int jobId, {
    required String photoType,
    required String filePath,
  }) async {
    final formData = FormData.fromMap({
      'photo_type': photoType,
      'file': await MultipartFile.fromFile(filePath),
    });
    final response = await _dio.post(
      '/workforce/jobs/$jobId/pre-service-photo/',
      data: formData,
    );
    return response.data as Map<String, dynamic>;
  }

  /// Completion proof. The optional trailing arguments are the Goods &
  /// Transport half: WorkforceJobProofView reads `recipient_name`,
  /// `recipient_phone`, `stop_id` and `latitude`/`longitude` and turns them
  /// into the rich `job.completion_proof_submitted` event the Customer app
  /// stores as a DeliveryProof. They are ignored for non-logistics jobs, so
  /// there is one proof endpoint and one call site rather than two.
  Future<Map<String, dynamic>> uploadProof(
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
    final formData = FormData.fromMap({
      'after_presence_photo': await MultipartFile.fromFile(afterPresencePhotoPath),
      if (afterAppliancePhotoPath != null)
        'after_appliance_photo': await MultipartFile.fromFile(afterAppliancePhotoPath),
      if (afterWorkAreaPhotoPath != null)
        'after_work_area_photo': await MultipartFile.fromFile(afterWorkAreaPhotoPath),
      if (notes != null && notes.isNotEmpty) 'notes': notes,
      if (recipientName != null && recipientName.isNotEmpty) 'recipient_name': recipientName,
      if (recipientPhone != null && recipientPhone.isNotEmpty) 'recipient_phone': recipientPhone,
      if (stopId != null) 'stop_id': stopId,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
    });
    final response = await _dio.post('/workforce/jobs/$jobId/proof/', data: formData);
    return response.data as Map<String, dynamic>;
  }

  // ---------------------------------------------------------------------
  // Goods & Transport trip actions
  //
  // These three endpoints already existed on the vendor backend but nothing
  // in the driver app called them, so a logistics job was indistinguishable
  // from a repair job on the phone: no drop point, no legs, no stops. They
  // live here alongside every other job-lifecycle action rather than in a
  // parallel client, so they share this app's Dio instance, auth
  // interceptor, base URL and error handling.
  // ---------------------------------------------------------------------

  /// Advance the trip. `leg` is one of LEG_SEQUENCE
  /// (EN_ROUTE_PICKUP, LOADING, EN_ROUTE_DROP, UNLOADING, DELIVERED).
  ///
  /// Safe to retry: the backend is forward-only and idempotent, so a repeat
  /// of the leg already recorded returns `changed: false` without adding a
  /// second history entry or re-firing a duplicate customer event.
  Future<Map<String, dynamic>> setLogisticsLeg(int jobId, String leg) async {
    final response = await _dio.post(
      '/workforce/jobs/$jobId/logistics-leg/',
      data: {'leg': leg},
    );
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> fetchTripStops(int jobId) async {
    final response = await _dio.get('/workforce/jobs/$jobId/stops/');
    return response.data as Map<String, dynamic>;
  }

  /// Mark a stop arrived, and completed once the driver is done there.
  ///
  /// Also safe to retry: the backend never rewrites a timestamp it has
  /// already recorded, so a retry cannot drag the trip timeline forward.
  Future<Map<String, dynamic>> updateTripStop(
    int jobId, {
    required int stopId,
    required bool completed,
  }) async {
    final response = await _dio.post(
      '/workforce/jobs/$jobId/stops/',
      data: {'stop_id': stopId, 'completed': completed},
    );
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> fetchPayment(int jobId) async {
    final response = await _dio.get('/workforce/jobs/$jobId/payment/');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> collectCash(int jobId, double amountReceived) async {
    final response = await _dio.post(
      '/workforce/jobs/$jobId/payment/collect/',
      data: {'amount_received': amountReceived},
    );
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> verifyPaymentOtp(int jobId, String otp) async {
    final response = await _dio.post(
      '/workforce/jobs/$jobId/payment/verify-otp/',
      data: {'otp': otp},
    );
    return response.data as Map<String, dynamic>;
  }
}

final jobActionsApiProvider = Provider<JobActionsApi>((ref) {
  return JobActionsApi(ref.watch(apiClientProvider));
});
