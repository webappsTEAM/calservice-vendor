import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/presentation/auth_controller.dart';
import '../../profile/presentation/profile_providers.dart';
import '../data/onboarding_repository.dart';

class OnboardingWizardController extends StateNotifier<AsyncValue<void>> {
  OnboardingWizardController(this._ref) : super(const AsyncValue.data(null));

  final Ref _ref;

  /// Saves one section of the draft and advances (or retreats) the
  /// server-side step cursor. Returns true on success.
  Future<bool> saveStep({
    required int step,
    required Map<String, dynamic> draftData,
  }) async {
    state = const AsyncValue.loading();
    try {
      await _ref.read(onboardingRepositoryProvider).saveDraft(step: step, draftData: draftData);
      _ref.invalidate(employeeProfileProvider);
      await _ref.read(employeeProfileProvider.future);
      state = const AsyncValue.data(null);
      return true;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return false;
    }
  }

  /// Final submit. Refreshes the authenticated user's registrationStatus so
  /// the router's redirect gate immediately routes to PendingReviewScreen
  /// instead of requiring a fresh login.
  Future<bool> submit() async {
    state = const AsyncValue.loading();
    try {
      await _ref.read(onboardingRepositoryProvider).submit();
      await _ref.read(authControllerProvider.notifier).refreshUser();
      state = const AsyncValue.data(null);
      return true;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return false;
    }
  }
}

final onboardingWizardControllerProvider =
    StateNotifierProvider<OnboardingWizardController, AsyncValue<void>>((ref) {
  return OnboardingWizardController(ref);
});
