import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'onboarding_api.dart';

class OnboardingRepository {
  OnboardingRepository(this._api);

  final OnboardingApi _api;

  Future<void> saveDraft({
    required int step,
    required Map<String, dynamic> draftData,
  }) {
    return _api.saveDraft(step: step, draftData: draftData);
  }

  Future<void> submit() {
    return _api.submit();
  }
}

final onboardingRepositoryProvider = Provider<OnboardingRepository>((ref) {
  return OnboardingRepository(ref.watch(onboardingApiProvider));
});
