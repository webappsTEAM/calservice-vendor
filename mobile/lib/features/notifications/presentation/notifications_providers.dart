import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/notifications_repository.dart';
import '../domain/app_notification.dart';

class NotificationsNotifier extends AutoDisposeAsyncNotifier<NotificationsResult> {
  @override
  Future<NotificationsResult> build() {
    return ref.watch(notificationsRepositoryProvider).fetchNotifications();
  }

  /// Optimistically marks one notification read, then confirms with the
  /// server; reverts on failure so the UI never shows a state the backend
  /// didn't actually accept.
  Future<void> markAsRead(int id) async {
    final current = state.valueOrNull;
    if (current == null) return;

    AppNotification? target;
    for (final n in current.items) {
      if (n.id == id) {
        target = n;
        break;
      }
    }
    if (target == null || target.isRead) return;

    final optimistic = NotificationsResult(
      unreadCount: current.unreadCount > 0 ? current.unreadCount - 1 : 0,
      items: [for (final n in current.items) n.id == id ? n.copyWith(isRead: true) : n],
    );
    state = AsyncData(optimistic);

    try {
      await ref.read(notificationsRepositoryProvider).markAsRead(id);
    } catch (_) {
      state = AsyncData(current);
      rethrow;
    }
  }

  /// Optimistically marks all notifications as read.
  Future<void> markAllAsRead() async {
    final current = state.valueOrNull;
    if (current == null || current.items.isEmpty) return;

    final optimistic = NotificationsResult(
      unreadCount: 0,
      items: [for (final n in current.items) n.copyWith(isRead: true)],
    );
    state = AsyncData(optimistic);

    try {
      await ref.read(notificationsRepositoryProvider).markAllAsRead();
    } catch (_) {
      state = AsyncData(current);
      rethrow;
    }
  }

  /// Optimistically clears a single notification by id.
  Future<void> clearNotification(int id) async {
    final current = state.valueOrNull;
    if (current == null) return;

    final target = current.items.where((n) => n.id == id).firstOrNull;
    if (target == null) return;

    final wasUnread = !target.isRead;
    final newUnreadCount = wasUnread && current.unreadCount > 0
        ? current.unreadCount - 1
        : current.unreadCount;

    final optimistic = NotificationsResult(
      unreadCount: newUnreadCount,
      items: current.items.where((n) => n.id != id).toList(),
    );
    state = AsyncData(optimistic);

    try {
      await ref.read(notificationsRepositoryProvider).clearNotification(id);
    } catch (_) {
      state = AsyncData(current);
      rethrow;
    }
  }

  /// Optimistically clears multiple selected notifications.
  Future<void> clearSelected(List<int> ids) async {
    final current = state.valueOrNull;
    if (current == null || ids.isEmpty) return;

    final idSet = ids.toSet();
    final unreadCleared = current.items
        .where((n) => idSet.contains(n.id) && !n.isRead)
        .length;
    final newUnreadCount = (current.unreadCount - unreadCleared).clamp(0, double.infinity).toInt();

    final optimistic = NotificationsResult(
      unreadCount: newUnreadCount,
      items: current.items.where((n) => !idSet.contains(n.id)).toList(),
    );
    state = AsyncData(optimistic);

    try {
      await ref.read(notificationsRepositoryProvider).clearSelected(ids);
    } catch (_) {
      state = AsyncData(current);
      rethrow;
    }
  }

  /// Optimistically clears all notifications.
  Future<void> clearAll() async {
    final current = state.valueOrNull;
    if (current == null || current.items.isEmpty) return;

    const optimistic = NotificationsResult(
      unreadCount: 0,
      items: [],
    );
    state = const AsyncData(optimistic);

    try {
      await ref.read(notificationsRepositoryProvider).clearAll();
    } catch (_) {
      state = AsyncData(current);
      rethrow;
    }
  }
}

final notificationsProvider =
    AutoDisposeAsyncNotifierProvider<NotificationsNotifier, NotificationsResult>(
      NotificationsNotifier.new,
    );

/// Watched by the bottom-nav shell to badge the Notifications tab, without
/// needing its own separate fetch.
final unreadNotificationsCountProvider = Provider.autoDispose<int>((ref) {
  return ref.watch(notificationsProvider).valueOrNull?.unreadCount ?? 0;
});
