import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/onboarding/data/onboarding_storage.dart';
import 'package:mobile/features/onboarding/presentation/onboarding_controller.dart';

class InMemoryOnboardingStorage extends OnboardingStorage {
  String? _value;

  @override
  Future<bool> hasCompletedOnboarding() async => _value == 'true';

  @override
  Future<void> setOnboardingCompleted() async => _value = 'true';

  @override
  Future<void> clear() async => _value = null;
}

void main() {
  group('OnboardingStorage & Controller Persistence Tests', () {
    test('fresh storage reports onboarding not completed', () async {
      final storage = InMemoryOnboardingStorage();
      final isCompleted = await storage.hasCompletedOnboarding();
      expect(isCompleted, isFalse);
    });

    test('setting completed persists true', () async {
      final storage = InMemoryOnboardingStorage();
      await storage.setOnboardingCompleted();
      final isCompleted = await storage.hasCompletedOnboarding();
      expect(isCompleted, isTrue);
    });

    test('clearing storage resets to not completed', () async {
      final storage = InMemoryOnboardingStorage();
      await storage.setOnboardingCompleted();
      expect(await storage.hasCompletedOnboarding(), isTrue);

      await storage.clear();
      expect(await storage.hasCompletedOnboarding(), isFalse);
    });

    test('OnboardingController loads initial false, updates to true on completeOnboarding', () async {
      final storage = InMemoryOnboardingStorage();
      final controller = OnboardingController(storage);

      // Initial state is null while loading
      expect(controller.state, isNull);

      // Allow _loadState to complete
      await Future.delayed(const Duration(milliseconds: 10));
      expect(controller.state, isFalse);

      // Complete onboarding
      await controller.completeOnboarding();
      expect(controller.state, isTrue);
      expect(await storage.hasCompletedOnboarding(), isTrue);

      // Reset
      await controller.resetOnboarding();
      expect(controller.state, isFalse);
      expect(await storage.hasCompletedOnboarding(), isFalse);
    });
  });
}
