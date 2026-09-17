import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/invitations_repository.dart';
import '../domain/technician_invitation.dart';

final invitationsFilterTabProvider = StateProvider<String>((ref) => 'PENDING');

final technicianInvitationsProvider = FutureProvider.autoDispose<InvitationsResponse>((ref) async {
  final repo = ref.watch(invitationsRepositoryProvider);
  return repo.getInvitations(status: 'ALL');
});
