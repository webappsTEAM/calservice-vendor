import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

/// The two onboarding-wizard write endpoints (backend/workforce_api/views.py
/// `WorkforceOnboardingDraftView` / `WorkforceOnboardingSubmitView`). Reading
/// the current draft reuses the existing `employeeProfileProvider` — GET
/// /workforce/profile/me/ and GET /workforce/onboarding/me/ return the
/// identical serializer, so there is no separate "fetch" method here.
class OnboardingApi {
  OnboardingApi(this._dio);

  final Dio _dio;

  /// `draftData` must contain only the section(s) being changed (e.g. just
  /// `{'personal': {...}}`) — the backend does a shallow top-level merge, so
  /// omitted sections are left untouched. It must always include every key
  /// already in that section's stored draft that should survive (the merge
  /// replaces the whole section value, not a deep merge within it).
  Future<Map<String, dynamic>> saveDraft({
    required int step,
    required Map<String, dynamic> draftData,
  }) async {
    final response = await _dio.patch(
      '/workforce/onboarding/draft/',
      data: {
        'step': step,
        'draft_data': draftData,
      },
    );
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> submit() async {
    final response = await _dio.post('/workforce/onboarding/submit/');
    return response.data as Map<String, dynamic>;
  }
}

final onboardingApiProvider = Provider<OnboardingApi>((ref) {
  return OnboardingApi(ref.watch(apiClientProvider));
});
