import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

bool _isTestEnvironment() {
  return WidgetsBinding.instance.runtimeType.toString().contains('Test');
}

/// Tracks whether the initial animated splash screen has completed its reveal
/// animation and is ready to let GoRouter redirect to the destination screen.
class SplashController extends StateNotifier<bool> {
  SplashController({this.autoCompleteInTest = false})
      : super(autoCompleteInTest) {
    if (autoCompleteInTest) {
      state = true;
    }
  }

  final bool autoCompleteInTest;

  void complete() {
    if (!state) {
      state = true;
    }
  }
}

final splashControllerProvider =
    StateNotifierProvider<SplashController, bool>((ref) {
  final isTest = _isTestEnvironment();
  return SplashController(autoCompleteInTest: isTest);
});
