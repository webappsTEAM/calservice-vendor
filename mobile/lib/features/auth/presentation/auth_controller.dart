import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/auth_events.dart';
import '../data/auth_repository.dart';
import '../domain/auth_user.dart';
import '../domain/provider_registration_result.dart';

enum AuthStatus { unknown, unauthenticated, authenticated }

/// The app's session state. `unknown` means "still checking for a stored
/// session" — routes should show a loading screen, not redirect yet.
class AuthState {
  const AuthState._(this.status, this.user);

  const AuthState.unknown() : this._(AuthStatus.unknown, null);

  const AuthState.unauthenticated() : this._(AuthStatus.unauthenticated, null);

  const AuthState.authenticated(AuthUser user)
    : this._(AuthStatus.authenticated, user);

  final AuthStatus status;
  final AuthUser? user;
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._repository, AuthEvents authEvents)
    : super(const AuthState.unknown()) {
    _sessionExpiredSub = authEvents.onSessionExpired.listen((_) {
      state = const AuthState.unauthenticated();
    });
    _restoreSession();
  }

  final AuthRepository _repository;
  late final StreamSubscription<void> _sessionExpiredSub;

  Future<void> _restoreSession() async {
    final user = await _repository.restoreSession();
    state = user != null
        ? AuthState.authenticated(user)
        : const AuthState.unauthenticated();
  }

  Future<void> login({
    required String identifier,
    required String password,
  }) async {
    final user = await _repository.login(
      identifier: identifier,
      password: password,
    );
    state = AuthState.authenticated(user);
  }

  Future<void> signup({
    required String firstName,
    String? lastName,
    required String mobileNumber,
    required String email,
    required String password,
    dynamic companyId,
  }) async {
    final user = await _repository.signup(
      firstName: firstName,
      lastName: lastName,
      mobileNumber: mobileNumber,
      email: email,
      password: password,
      companyId: companyId,
    );
    state = AuthState.authenticated(user);
  }

  Future<ProviderRegistrationResult> registerProvider({
    required String businessName,
    required String contactFirstName,
    String? contactLastName,
    required String mobileNumber,
    required String email,
    required String password,
    String? address,
    String? city,
  }) async {
    final result = await _repository.registerProvider(
      businessName: businessName,
      contactFirstName: contactFirstName,
      contactLastName: contactLastName,
      mobileNumber: mobileNumber,
      email: email,
      password: password,
      address: address,
      city: city,
    );
    // Tokens are already securely saved to TokenStorage by AuthRepository.
    // We defer setting AuthState.authenticated until the user taps "Go to Dashboard"
    // on the Provider Registration Success Screen.
    return result;
  }

  void completeProviderAuth(AuthUser user) {
    state = AuthState.authenticated(user);
  }

  Future<void> refreshUser() async {
    final user = await _repository.refreshUser();
    if (user != null) {
      state = AuthState.authenticated(user);
    }
  }

  Future<void> logout() async {
    await _repository.logout();
    state = const AuthState.unauthenticated();
  }

  @override
  void dispose() {
    _sessionExpiredSub.cancel();
    super.dispose();
  }
}

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>((
  ref,
) {
  return AuthController(
    ref.watch(authRepositoryProvider),
    ref.watch(authEventsProvider),
  );
});
