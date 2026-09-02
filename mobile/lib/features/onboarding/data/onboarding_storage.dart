import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persistent storage for the intro onboarding walkthrough completion flag.
/// Uses Android Keystore / SharedPreferences via FlutterSecureStorage.
class OnboardingStorage {
  OnboardingStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  static const _completedKey = 'sevo_onboarding_intro_completed_v1';

  /// Returns true if the user has completed or skipped the intro onboarding.
  Future<bool> hasCompletedOnboarding() async {
    try {
      final value = await _storage.read(key: _completedKey);
      return value == 'true';
    } catch (_) {
      return false;
    }
  }

  /// Marks the intro onboarding as completed so it does not show again on launch.
  Future<void> setOnboardingCompleted() async {
    try {
      await _storage.write(key: _completedKey, value: 'true');
    } catch (_) {}
  }

  /// Clears the onboarding completion flag (e.g. for testing or fresh first launch).
  Future<void> clear() async {
    try {
      await _storage.delete(key: _completedKey);
    } catch (_) {}
  }
}

final onboardingStorageProvider =
    Provider<OnboardingStorage>((ref) => OnboardingStorage());
