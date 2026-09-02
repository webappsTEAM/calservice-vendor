import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/profile_repository.dart';
import '../domain/employee_profile.dart';
import '../domain/shift_status.dart';

/// Shared across Home, Profile, and Documents — cached and refreshable.
final employeeProfileProvider = FutureProvider.autoDispose<EmployeeProfile>((ref) async {
  return ref.watch(profileRepositoryProvider).fetchProfile();
});

final changeRequestsProvider = FutureProvider.autoDispose<List<EmployeeChangeRequest>>((ref) async {
  return ref.watch(profileRepositoryProvider).fetchChangeRequests();
});

final shiftStatusProvider = FutureProvider.autoDispose<ShiftStatus?>((ref) async {
  return ref.watch(profileRepositoryProvider).fetchShiftStatus();
});

class ProfileController extends StateNotifier<AsyncValue<void>> {
  ProfileController(this._ref) : super(const AsyncValue.data(null));

  final Ref _ref;

  Future<bool> savePreferences(Map<String, dynamic> data) async {
    state = const AsyncValue.loading();
    try {
      await _ref.read(profileRepositoryProvider).updateProfile(data);
      _ref.invalidate(employeeProfileProvider);
      state = const AsyncValue.data(null);
      return true;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return false;
    }
  }

  Future<bool> uploadAvatar(String filePath) async {
    state = const AsyncValue.loading();
    try {
      await _ref.read(profileRepositoryProvider).uploadAvatar(filePath);
      _ref.invalidate(employeeProfileProvider);
      state = const AsyncValue.data(null);
      return true;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return false;
    }
  }

  Future<bool> submitChangeRequest({
    required String fieldName,
    required String fieldLabel,
    required String newValue,
    required String reason,
  }) async {
    state = const AsyncValue.loading();
    try {
      await _ref.read(profileRepositoryProvider).submitChangeRequest(
            fieldName: fieldName,
            fieldLabel: fieldLabel,
            newValue: newValue,
            reason: reason,
          );
      _ref.invalidate(changeRequestsProvider);
      state = const AsyncValue.data(null);
      return true;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return false;
    }
  }
}

final profileControllerProvider = StateNotifierProvider<ProfileController, AsyncValue<void>>((ref) {
  return ProfileController(ref);
});

class AvailabilityState {
  const AvailabilityState({
    this.isLoading = false,
    this.errorMessage,
  });

  final bool isLoading;
  final String? errorMessage;

  AvailabilityState copyWith({
    bool? isLoading,
    String? errorMessage,
  }) {
    return AvailabilityState(
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
    );
  }
}

class AvailabilityController extends StateNotifier<AvailabilityState> {
  AvailabilityController(this._ref) : super(const AvailabilityState());

  final Ref _ref;

  /// Toggles technician availability between ONLINE and OFFLINE.
  ///
  /// Strictly enforces:
  /// 1. An employee who is actively working on a job (`hasActiveJob == true`)
  ///    CANNOT switch to OFFLINE, matching web & backend validation rules.
  /// 2. Disables the control and shows loading while API runs.
  /// 3. Updates state upon confirmed response.
  /// 4. Reverts and exposes error on failure.
  Future<bool?> toggleAvailability({
    required bool currentOnline,
    required bool hasActiveJob,
    String? activeJobRef,
  }) async {
    if (state.isLoading) return null;

    // Check restriction: cannot go offline while on active job
    if (currentOnline && hasActiveJob) {
      final jobLabel = activeJobRef != null && activeJobRef.isNotEmpty
          ? activeJobRef
          : 'your active assignment';
      state = state.copyWith(
        errorMessage: 'Cannot go offline while actively working on $jobLabel. Please complete or cancel the active job first.',
      );
      return null;
    }

    state = state.copyWith(isLoading: true, errorMessage: null);

    final desiredOnline = !currentOnline;

    try {
      final res = await _ref.read(profileRepositoryProvider).togglePresence(isOnline: desiredOnline);
      final newOnline = res['is_online'] is bool ? (res['is_online'] as bool) : desiredOnline;

      // Invalidate profile and active jobs so all widgets reflect fresh DB state
      _ref.invalidate(employeeProfileProvider);

      state = const AvailabilityState(isLoading: false, errorMessage: null);
      return newOnline;
    } catch (e) {
      String msg = 'Unable to update availability. Please try again.';
      if (e is Exception) {
        // Check for specific backend error messages if available
        msg = e.toString().replaceAll('Exception: ', '');
      }
      state = AvailabilityState(isLoading: false, errorMessage: msg);
      return null;
    }
  }

  void clearError() {
    if (state.errorMessage != null) {
      state = state.copyWith(errorMessage: null);
    }
  }
}

final availabilityControllerProvider =
    StateNotifierProvider<AvailabilityController, AvailabilityState>((ref) {
  return AvailabilityController(ref);
});
