import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/onboarding_storage.dart';

bool _isTestEnvironment() {
  return WidgetsBinding.instance.runtimeType.toString().contains('Test');
}

/// State represents whether the user has completed the intro onboarding walkthrough:
/// - `null`: Initial loading / restoring preference from storage
/// - `false`: Fresh user who hasn't completed onboarding yet
/// - `true`: User who has completed or skipped onboarding
class OnboardingController extends StateNotifier<bool?> {
  OnboardingController(
    this._storage, {
    this.autoPreviewInDebug = false,
  }) : super(null) {
    _loadState();
  }

  final OnboardingStorage _storage;
  final bool autoPreviewInDebug;

  Future<void> _loadState() async {
    final completed = await _storage.hasCompletedOnboarding();
    // In debug mode during live app execution (`flutter run`), always start with false in memory
    // so every app launch automatically opens Onboarding Page 1 for development preview,
    // without clearing the persistent storage flag.
    if (autoPreviewInDebug) {
      state = false;
    } else {
      state = completed;
    }
  }

  Future<void> completeOnboarding() async {
    await _storage.setOnboardingCompleted();
    state = true;
  }

  Future<void> resetOnboarding() async {
    await _storage.clear();
    state = false;
  }
}

final onboardingControllerProvider =
    StateNotifierProvider<OnboardingController, bool?>((ref) {
  final autoPreview = kDebugMode && !_isTestEnvironment();
  return OnboardingController(
    ref.watch(onboardingStorageProvider),
    autoPreviewInDebug: autoPreview,
  );
});
