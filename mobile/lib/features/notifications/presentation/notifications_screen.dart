import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/async_value_view.dart';
import '../../../shared/widgets/empty_state.dart';
import '../../../shared/widgets/workforce_app_bar.dart';
import '../domain/app_notification.dart';
import 'notifications_providers.dart';

class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  bool _isSelectionMode = false;
  final Set<int> _selectedIds = <int>{};
  bool _isProcessing = false;

  void _toggleSelectMode(List<AppNotification> items) {
    setState(() {
      _isSelectionMode = !_isSelectionMode;
      _selectedIds.clear();
    });
  }

  void _toggleSelectAll(List<AppNotification> items) {
    setState(() {
      if (_selectedIds.length == items.length && items.isNotEmpty) {
        _selectedIds.clear();
      } else {
        _selectedIds.addAll(items.map((n) => n.id));
      }
    });
  }

  void _toggleSelectItem(int id) {
    setState(() {
      if (_selectedIds.contains(id)) {
        _selectedIds.remove(id);
      } else {
        _selectedIds.add(id);
      }
    });
  }

  Future<void> _markAllAsRead() async {
    if (_isProcessing) return;
    setState(() => _isProcessing = true);
    try {
      await ref.read(notificationsProvider.notifier).markAllAsRead();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('All notifications marked as read')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not mark all as read. Please try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Future<void> _deleteSelected() async {
    if (_isProcessing || _selectedIds.isEmpty) return;
    final idsToDelete = _selectedIds.toList();
    final count = idsToDelete.length;

    setState(() => _isProcessing = true);
    try {
      await ref.read(notificationsProvider.notifier).clearSelected(idsToDelete);
      setState(() {
        _selectedIds.clear();
        _isSelectionMode = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Deleted $count ${count == 1 ? 'notification' : 'notifications'}')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not delete selected notifications.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Future<void> _deleteSingle(int id) async {
    if (_isProcessing) return;
    setState(() => _isProcessing = true);
    try {
      await ref.read(notificationsProvider.notifier).clearNotification(id);
      setState(() {
        _selectedIds.remove(id);
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Notification removed')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not remove notification.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Future<void> _showClearAllConfirmation() async {
    if (_isProcessing) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: const Text('Clear All Notifications?'),
        content: const Text('Are you sure you want to clear all notifications?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogCtx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.error.base,
            ),
            onPressed: () => Navigator.of(dialogCtx).pop(true),
            child: const Text('Clear All'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      setState(() => _isProcessing = true);
      try {
        await ref.read(notificationsProvider.notifier).clearAll();
        setState(() {
          _isSelectionMode = false;
          _selectedIds.clear();
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('All notifications cleared')),
          );
        }
      } catch (_) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not clear notifications. Please try again.')),
          );
        }
      } finally {
        if (mounted) setState(() => _isProcessing = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncNotifications = ref.watch(notificationsProvider);

    return Scaffold(
      appBar: const WorkforceAppBar(
        titleText: 'Notifications',
        showBrand: false,
        showNotifications: false,
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(notificationsProvider.future),
        child: AsyncValueView<NotificationsResult>(
          value: asyncNotifications,
          onRetry: () => ref.invalidate(notificationsProvider),
          builder: (context, result) {
            final items = result.items;
            final count = items.length;

            if (items.isEmpty) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
                  _NotificationHeader(
                    title: 'Notifications',
                    countText: '0 notifications',
                    actions: [],
                  ),
                  SizedBox(height: AppSpacing.xxl),
                  EmptyState(
                    icon: Icons.notifications_none_rounded,
                    title: 'No notifications',
                    message: "You're all caught up.",
                  ),
                ],
              );
            }

            final unreadCount = items.where((n) => !n.isRead).length;
            final isAllSelected = _selectedIds.length == count;

            return Column(
              children: [
                // Top notification header matching design
                _NotificationHeader(
                  title: _isSelectionMode ? 'Select Notifications' : 'Notifications',
                  countText: _isSelectionMode
                      ? '${_selectedIds.length} of $count selected'
                      : '$count ${count == 1 ? 'notification' : 'notifications'}',
                  actions: _isSelectionMode
                      ? [
                          TextButton(
                            key: const Key('toggle_select_all_button'),
                            onPressed: () => _toggleSelectAll(items),
                            style: TextButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
                              minimumSize: Size.zero,
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                            child: Text(
                              isAllSelected ? 'Deselect All' : 'Select All',
                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                            ),
                          ),
                          const SizedBox(width: AppSpacing.xs),
                          TextButton(
                            key: const Key('cancel_selection_button'),
                            onPressed: () => _toggleSelectMode(items),
                            style: TextButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
                              minimumSize: Size.zero,
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                            child: const Text(
                              'Cancel',
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                            ),
                          ),
                        ]
                      : [
                          TextButton.icon(
                            key: const Key('select_mode_button'),
                            onPressed: () => _toggleSelectMode(items),
                            icon: const Icon(Icons.check_box_outlined, size: 15),
                            label: const Text('Select', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                            style: TextButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs, vertical: AppSpacing.xs),
                              minimumSize: Size.zero,
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                          ),
                          PopupMenuButton<_HeaderMenuAction>(
                            key: const Key('notification_header_menu'),
                            icon: Icon(Icons.more_vert, size: 20, color: AppColors.textSecondary),
                            padding: EdgeInsets.zero,
                            onSelected: (action) {
                              switch (action) {
                                case _HeaderMenuAction.markAllRead:
                                  _markAllAsRead();
                                  break;
                                case _HeaderMenuAction.clearAll:
                                  _showClearAllConfirmation();
                                  break;
                              }
                            },
                            itemBuilder: (ctx) => [
                              PopupMenuItem(
                                key: const Key('mark_all_read_menu_item'),
                                value: _HeaderMenuAction.markAllRead,
                                enabled: unreadCount > 0,
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.done_all_rounded, size: 18, color: AppColors.primary),
                                    const SizedBox(width: AppSpacing.sm),
                                    const Text('Mark All as Read', style: TextStyle(fontSize: 13)),
                                  ],
                                ),
                              ),
                              PopupMenuItem(
                                key: const Key('clear_all_menu_item'),
                                value: _HeaderMenuAction.clearAll,
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.delete_sweep_outlined, size: 18, color: AppColors.error.base),
                                    const SizedBox(width: AppSpacing.sm),
                                    Text('Clear All', style: TextStyle(fontSize: 13, color: AppColors.error.base)),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ],
                ),

                // Quick Action Bar in Selection Mode
                if (_isSelectionMode)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceMuted,
                      border: Border(bottom: BorderSide(color: AppColors.border)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            '${_selectedIds.length} selected',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ),
                        FilledButton.icon(
                          key: const Key('delete_selected_button'),
                          onPressed: _selectedIds.isEmpty ? null : _deleteSelected,
                          icon: const Icon(Icons.delete_outline_rounded, size: 15),
                          label: Text(
                            _selectedIds.isEmpty ? 'Delete Selected' : 'Delete Selected (${_selectedIds.length})',
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                          ),
                          style: FilledButton.styleFrom(
                            backgroundColor: AppColors.error.base,
                            foregroundColor: Colors.white,
                            disabledBackgroundColor: AppColors.border,
                            disabledForegroundColor: AppColors.textMuted,
                            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
                            minimumSize: Size.zero,
                          ),
                        ),
                      ],
                    ),
                  ),

                // Notification items list
                Expanded(
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                    itemCount: count,
                    separatorBuilder: (context, index) => const SizedBox(height: AppSpacing.sm),
                    itemBuilder: (context, index) {
                      final notification = items[index];
                      final isSelected = _selectedIds.contains(notification.id);

                      return _NotificationCard(
                        key: ValueKey('notification_card_${notification.id}'),
                        notification: notification,
                        isSelectionMode: _isSelectionMode,
                        isSelected: isSelected,
                        onToggleSelect: () => _toggleSelectItem(notification.id),
                        onTap: () async {
                          if (_isSelectionMode) {
                            _toggleSelectItem(notification.id);
                          } else if (!notification.isRead) {
                            try {
                              await ref.read(notificationsProvider.notifier).markAsRead(notification.id);
                            } catch (_) {
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('Could not mark as read. Please try again.')),
                                );
                              }
                            }
                          }
                        },
                        onDelete: () => _deleteSingle(notification.id),
                      );
                    },
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

enum _HeaderMenuAction {
  markAllRead,
  clearAll,
}

class _NotificationHeader extends StatelessWidget {
  const _NotificationHeader({
    required this.title,
    required this.countText,
    required this.actions,
  });

  final String title;
  final String countText;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.sm, AppSpacing.sm),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  countText,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          if (actions.isNotEmpty)
            Row(
              mainAxisSize: MainAxisSize.min,
              children: actions,
            ),
        ],
      ),
    );
  }
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({
    super.key,
    required this.notification,
    required this.isSelectionMode,
    required this.isSelected,
    required this.onToggleSelect,
    required this.onTap,
    required this.onDelete,
  });

  final AppNotification notification;
  final bool isSelectionMode;
  final bool isSelected;
  final VoidCallback onToggleSelect;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  IconData _getIconForType(String? type, String title) {
    final t = (type ?? '').toLowerCase();
    final lowerTitle = title.toLowerCase();

    if (t.contains('job') || t.contains('dispatch') || lowerTitle.contains('job')) {
      return Icons.work_outline_rounded;
    }
    if (t.contains('schedule') || lowerTitle.contains('schedule')) {
      return Icons.calendar_today_outlined;
    }
    if (t.contains('document') || t.contains('compliance') || lowerTitle.contains('document')) {
      return Icons.description_outlined;
    }
    if (t.contains('wallet') || t.contains('payout') || t.contains('pay') || lowerTitle.contains('payout')) {
      return Icons.account_balance_wallet_outlined;
    }
    if (t.contains('alert') || lowerTitle.contains('warning') || lowerTitle.contains('urgent')) {
      return Icons.warning_amber_rounded;
    }
    return Icons.notifications_outlined;
  }

  @override
  Widget build(BuildContext context) {
    final isUnread = !notification.isRead;
    final cardBorderColor = isSelected
        ? AppColors.primary
        : isUnread
            ? AppColors.info.tintBorder
            : AppColors.border;

    final cardBgColor = isSelected
        ? AppColors.info.tint.withValues(alpha: 0.7)
        : isUnread
            ? AppColors.info.tint.withValues(alpha: 0.3)
            : AppColors.surface;

    final typeIcon = _getIconForType(notification.notificationType, notification.title);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.cardStandard),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: cardBgColor,
            borderRadius: BorderRadius.circular(AppRadius.cardStandard),
            border: Border.all(color: cardBorderColor, width: isSelected ? 1.5 : 1.0),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Checkbox in selection mode
              if (isSelectionMode)
                Padding(
                  padding: const EdgeInsets.only(right: AppSpacing.sm, top: 2),
                  child: SizedBox(
                    width: 22,
                    height: 22,
                    child: Checkbox(
                      value: isSelected,
                      onChanged: (_) => onToggleSelect(),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                      activeColor: AppColors.primary,
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                  ),
                ),

              // Icon with badge
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: isUnread ? AppColors.info.tint : AppColors.surfaceMuted,
                  borderRadius: BorderRadius.circular(AppRadius.button),
                  border: Border.all(
                    color: isUnread ? AppColors.info.tintBorder : AppColors.border,
                  ),
                ),
                child: Center(
                  child: Icon(
                    typeIcon,
                    size: 17,
                    color: isUnread ? AppColors.primary : AppColors.textSecondary,
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.md),

              // Notification Title, Message, Timestamp
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        if (isUnread) ...[
                          Container(
                            key: const Key('unread_indicator_dot'),
                            width: 6,
                            height: 6,
                            margin: const EdgeInsets.only(right: 6),
                            decoration: const BoxDecoration(
                              color: AppColors.primary,
                              shape: BoxShape.circle,
                            ),
                          ),
                        ],
                        Expanded(
                          child: Text(
                            notification.title,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: isUnread ? FontWeight.w800 : FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      notification.message,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 12,
                        color: isUnread ? AppColors.textPrimary : AppColors.textSecondary,
                        height: 1.35,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            _relativeTime(notification.createdAt),
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: isUnread ? FontWeight.w600 : FontWeight.w400,
                              color: isUnread ? AppColors.primary : AppColors.textMuted,
                            ),
                          ),
                        ),
                        if (!isSelectionMode)
                          InkWell(
                            key: Key('delete_single_notification_${notification.id}'),
                            onTap: onDelete,
                            borderRadius: BorderRadius.circular(4),
                            child: Padding(
                              padding: const EdgeInsets.all(2),
                              child: Icon(
                                Icons.delete_outline_rounded,
                                size: 16,
                                color: AppColors.textMuted,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _relativeTime(DateTime? dateTime) {
  if (dateTime == null) return '';
  final diff = DateTime.now().difference(dateTime);
  if (diff.inMinutes < 1) return 'Just now';
  if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
  if (diff.inHours < 24) return '${diff.inHours}h ago';
  if (diff.inDays < 7) return '${diff.inDays}d ago';
  return '${dateTime.day}/${dateTime.month}/${dateTime.year}';
}
