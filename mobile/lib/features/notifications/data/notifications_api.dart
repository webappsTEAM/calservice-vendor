import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

class NotificationsApi {
  NotificationsApi(this._dio);

  final Dio _dio;

  Future<Map<String, dynamic>> fetchNotifications() async {
    final response = await _dio.get('/workforce/notifications/');
    return response.data as Map<String, dynamic>;
  }

  Future<void> markAsRead(int id) async {
    await _dio.post('/workforce/notifications/$id/mark-read/');
  }

  Future<void> markAllAsRead() async {
    await _dio.post('/workforce/notifications/mark-read/');
  }

  Future<void> clearNotification(int id) async {
    await _dio.post('/workforce/notifications/$id/clear/');
  }

  Future<void> clearSelected(List<int> ids) async {
    await _dio.post('/workforce/notifications/clear/', data: {'ids': ids});
  }

  Future<void> clearAll() async {
    await _dio.post('/workforce/notifications/clear/', data: {'all': true});
  }
}

final notificationsApiProvider = Provider<NotificationsApi>((ref) {
  return NotificationsApi(ref.watch(apiClientProvider));
});
