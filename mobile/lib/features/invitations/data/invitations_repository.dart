import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/technician_invitation.dart';

final invitationsRepositoryProvider = Provider<InvitationsRepository>((ref) {
  final dio = ref.watch(apiClientProvider);
  return InvitationsRepository(dio);
});

class InvitationsRepository {
  InvitationsRepository(this._dio);

  final Dio _dio;

  /// Fetches technician vendor invitations and active partnership.
  Future<InvitationsResponse> getInvitations({String? status}) async {
    final queryParams = <String, dynamic>{
      'status': status ?? 'ALL',
    };

    final response = await _dio.get(
      '/workforce/technician/invitations/',
      queryParameters: queryParams,
    );

    return InvitationsResponse.fromJson(response.data as Map<String, dynamic>);
  }

  /// Responds to an invitation with 'ACCEPT' or 'REJECT'.
  Future<Map<String, dynamic>> respondToInvitation({
    required int invitationId,
    required String decision,
  }) async {
    final response = await _dio.post(
      '/workforce/technician/invitations/$invitationId/respond/',
      data: {'decision': decision},
    );

    return response.data as Map<String, dynamic>;
  }
}
