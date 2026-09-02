import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/notifications/data/notifications_repository.dart';
import 'package:mobile/features/notifications/domain/app_notification.dart';
import 'package:mobile/features/notifications/presentation/notifications_providers.dart';
import 'package:mobile/features/notifications/presentation/notifications_screen.dart';

class FakeNotificationsRepository implements NotificationsRepository {
  FakeNotificationsRepository({List<AppNotification>? initialItems})
      : items = List<AppNotification>.from(initialItems ?? []);

  List<AppNotification> items;

  @override
  Future<NotificationsResult> fetchNotifications() async {
    final unread = items.where((n) => !n.isRead).length;
    return NotificationsResult(unreadCount: unread, items: List.from(items));
  }

  @override
  Future<void> markAsRead(int id) async {
    items = [
      for (final n in items)
        if (n.id == id) n.copyWith(isRead: true) else n,
    ];
  }

  @override
  Future<void> markAllAsRead() async {
    items = [for (final n in items) n.copyWith(isRead: true)];
  }

  @override
  Future<void> clearNotification(int id) async {
    items.removeWhere((n) => n.id == id);
  }

  @override
  Future<void> clearSelected(List<int> ids) async {
    final set = ids.toSet();
    items.removeWhere((n) => set.contains(n.id));
  }

  @override
  Future<void> clearAll() async {
    items.clear();
  }
}

void main() {
  group('NotificationsScreen Enhanced UI/UX Tests', () {
    final sampleNotifications = [
      AppNotification(
        id: 101,
        title: 'New Job Assigned',
        message: 'Job #SR-8801 has been assigned to you in Indiranagar.',
        notificationType: 'job_assigned',
        relatedObjectId: 8801,
        isRead: false,
        createdAt: DateTime.now().subtract(const Duration(minutes: 5)),
      ),
      AppNotification(
        id: 102,
        title: 'Schedule Updated',
        message: 'Your shift schedule for tomorrow has been updated.',
        notificationType: 'schedule_update',
        relatedObjectId: null,
        isRead: false,
        createdAt: DateTime.now().subtract(const Duration(hours: 2)),
      ),
      AppNotification(
        id: 103,
        title: 'Document Approved',
        message: 'Your Electrical License document was approved by Admin.',
        notificationType: 'document_approval',
        relatedObjectId: null,
        isRead: true,
        createdAt: DateTime.now().subtract(const Duration(days: 1)),
      ),
    ];

    Widget createTestWidget({
      required FakeNotificationsRepository repo,
      Widget? extraHeader,
    }) {
      return ProviderScope(
        overrides: [
          notificationsRepositoryProvider.overrideWithValue(repo),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                ?extraHeader,
                const Expanded(child: NotificationsScreen()),
              ],
            ),
          ),
        ),
      );
    }

    // 1. Notification count displays correctly
    testWidgets('1. Notification count displays correctly', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      expect(find.text('Notifications'), findsWidgets);
      expect(find.text('3 notifications'), findsOneWidget);
      expect(find.text('New Job Assigned'), findsOneWidget);
      expect(find.text('Schedule Updated'), findsOneWidget);
      expect(find.text('Document Approved'), findsOneWidget);
    });

    // 2. Select mode can be activated
    testWidgets('2. Select mode can be activated', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      final selectButton = find.byKey(const Key('select_mode_button'));
      expect(selectButton, findsOneWidget);

      await tester.tap(selectButton);
      await tester.pumpAndSettle();

      expect(find.text('Select Notifications'), findsOneWidget);
      expect(find.text('0 of 3 selected'), findsOneWidget);
      expect(find.text('Select All'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.byType(Checkbox), findsNWidgets(3));
    });

    // 3. Individual notifications can be selected
    testWidgets('3. Individual notifications can be selected', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('select_mode_button')));
      await tester.pumpAndSettle();

      // Tap on the first notification card to select it
      await tester.tap(find.text('New Job Assigned'));
      await tester.pumpAndSettle();

      expect(find.text('1 of 3 selected'), findsOneWidget);
      expect(find.text('1 selected'), findsOneWidget);
      expect(find.text('Delete Selected (1)'), findsOneWidget);
    });

    // 4. Multiple notifications can be selected (including Select All)
    testWidgets('4. Multiple notifications can be selected and Select All works', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('select_mode_button')));
      await tester.pumpAndSettle();

      // Tap Select All
      await tester.tap(find.byKey(const Key('toggle_select_all_button')));
      await tester.pumpAndSettle();

      expect(find.text('3 of 3 selected'), findsOneWidget);
      expect(find.text('3 selected'), findsOneWidget);
      expect(find.text('Deselect All'), findsOneWidget);
      expect(find.text('Delete Selected (3)'), findsOneWidget);
    });

    // 5. Cancel exits selection mode and clears selection
    testWidgets('5. Cancel exits selection mode and clears selection', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('select_mode_button')));
      await tester.pumpAndSettle();

      await tester.tap(find.text('New Job Assigned'));
      await tester.pumpAndSettle();
      expect(find.text('1 of 3 selected'), findsOneWidget);

      // Tap Cancel
      await tester.tap(find.byKey(const Key('cancel_selection_button')));
      await tester.pumpAndSettle();

      expect(find.text('Notifications'), findsWidgets);
      expect(find.text('3 notifications'), findsOneWidget);
      expect(find.byType(Checkbox), findsNothing);
      expect(find.byKey(const Key('select_mode_button')), findsOneWidget);
    });

    // 6. Delete Selected removes only selected notifications
    testWidgets('6. Delete Selected removes only selected notifications', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('select_mode_button')));
      await tester.pumpAndSettle();

      // Select item 101 and item 103
      await tester.tap(find.text('New Job Assigned'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Document Approved'));
      await tester.pumpAndSettle();

      expect(find.text('Delete Selected (2)'), findsOneWidget);

      // Tap Delete Selected
      await tester.tap(find.byKey(const Key('delete_selected_button')));
      await tester.pumpAndSettle();

      expect(find.text('1 notification'), findsOneWidget);
      expect(find.text('Schedule Updated'), findsOneWidget);
      expect(find.text('New Job Assigned'), findsNothing);
      expect(find.text('Document Approved'), findsNothing);
      expect(find.text('Deleted 2 notifications'), findsOneWidget);
    });

    // 7. Individual notification delete works
    testWidgets('7. Individual notification delete works', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      expect(find.text('3 notifications'), findsOneWidget);

      // Tap individual delete on notification 102
      final deleteBtn = find.byKey(const Key('delete_single_notification_102'));
      expect(deleteBtn, findsOneWidget);
      await tester.tap(deleteBtn);
      await tester.pumpAndSettle();

      expect(find.text('2 notifications'), findsOneWidget);
      expect(find.text('Schedule Updated'), findsNothing);
      expect(find.text('New Job Assigned'), findsOneWidget);
      expect(find.text('Document Approved'), findsOneWidget);
      expect(find.text('Notification removed'), findsOneWidget);
    });

    // 8. Mark All as Read works
    testWidgets('8. Mark All as Read works and removes unread indicators', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      // 2 unread indicators should exist initially
      expect(find.byKey(const Key('unread_indicator_dot')), findsNWidgets(2));

      // Open header menu
      await tester.tap(find.byKey(const Key('notification_header_menu')));
      await tester.pumpAndSettle();

      // Tap Mark All as Read
      await tester.tap(find.byKey(const Key('mark_all_read_menu_item')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('unread_indicator_dot')), findsNothing);
      expect(find.text('All notifications marked as read'), findsOneWidget);
    });

    // 9. Clear All requires confirmation dialog
    testWidgets('9. Clear All requires confirmation dialog', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      // Open header menu
      await tester.tap(find.byKey(const Key('notification_header_menu')));
      await tester.pumpAndSettle();

      // Tap Clear All
      await tester.tap(find.byKey(const Key('clear_all_menu_item')));
      await tester.pumpAndSettle();

      expect(find.text('Clear All Notifications?'), findsOneWidget);
      expect(find.text('Are you sure you want to clear all notifications?'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Clear All'), findsOneWidget);

      // Dismiss dialog via Cancel
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      // Items should still exist
      expect(find.text('3 notifications'), findsOneWidget);
    });

    // 10. Clear All removes all notifications after confirmation
    testWidgets('10. Clear All removes all notifications on confirmation', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('notification_header_menu')));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('clear_all_menu_item')));
      await tester.pumpAndSettle();

      // Tap the Clear All action in dialog
      final clearAllDialogBtn = find.widgetWithText(FilledButton, 'Clear All');
      await tester.tap(clearAllDialogBtn);
      await tester.pumpAndSettle();

      expect(find.text('0 notifications'), findsOneWidget);
      expect(find.text('No notifications'), findsOneWidget);
      expect(find.text("You're all caught up."), findsOneWidget);
      expect(find.text('All notifications cleared'), findsOneWidget);
    });

    // 11. Notification count updates after deletion
    testWidgets('11. Notification count updates dynamically after deletion', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      expect(find.text('3 notifications'), findsOneWidget);

      await tester.tap(find.byKey(const Key('delete_single_notification_101')));
      await tester.pumpAndSettle();
      expect(find.text('2 notifications'), findsOneWidget);

      await tester.tap(find.byKey(const Key('delete_single_notification_102')));
      await tester.pumpAndSettle();
      expect(find.text('1 notification'), findsOneWidget);

      await tester.tap(find.byKey(const Key('delete_single_notification_103')));
      await tester.pumpAndSettle();
      expect(find.text('0 notifications'), findsOneWidget);
    });

    // 12. Header notification badge updates after deletion and mark as read
    testWidgets('12. Header notification badge synchronizes on delete and mark read', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);

      final badgeHeader = Consumer(
        builder: (context, ref, _) {
          final unread = ref.watch(unreadNotificationsCountProvider);
          return Text('Badge Count: $unread');
        },
      );

      await tester.pumpWidget(createTestWidget(repo: repo, extraHeader: badgeHeader));
      await tester.pumpAndSettle();

      // Initially 2 unread
      expect(find.text('Badge Count: 2'), findsOneWidget);

      // Tapping unread notification 101 marks it read
      await tester.tap(find.text('New Job Assigned'));
      await tester.pumpAndSettle();

      // Badge count decrements to 1
      expect(find.text('Badge Count: 1'), findsOneWidget);

      // Delete unread notification 102
      await tester.tap(find.byKey(const Key('delete_single_notification_102')));
      await tester.pumpAndSettle();

      // Badge count decrements to 0
      expect(find.text('Badge Count: 0'), findsOneWidget);
    });

    // 13. Unread/read visual state updates correctly
    testWidgets('13. Unread/read visual state updates correctly on tap', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('unread_indicator_dot')), findsNWidgets(2));

      // Tap on unread notification
      await tester.tap(find.text('New Job Assigned'));
      await tester.pumpAndSettle();

      // Now only 1 unread indicator dot remains
      expect(find.byKey(const Key('unread_indicator_dot')), findsOneWidget);
    });

    // 14. Empty state displays when there are no notifications
    testWidgets('14. Empty state displays properly when there are no notifications', (WidgetTester tester) async {
      final repo = FakeNotificationsRepository(initialItems: const []);
      await tester.pumpWidget(createTestWidget(repo: repo));
      await tester.pumpAndSettle();

      expect(find.text('0 notifications'), findsOneWidget);
      expect(find.text('No notifications'), findsOneWidget);
      expect(find.text("You're all caught up."), findsOneWidget);
      expect(find.byKey(const Key('select_mode_button')), findsNothing);
      expect(find.byKey(const Key('notification_header_menu')), findsNothing);
    });

    // 15. Multi-screen responsiveness without overflow
    group('15. Multi-Screen Responsiveness (320px, 360px, 390px, 412px, 480px)', () {
      final screenSizes = <String, Size>{
        'Small Phone (320px)': const Size(320, 640),
        'Standard Phone (360px)': const Size(360, 780),
        'Medium Phone (390px)': const Size(390, 844),
        'Large Phone (412px)': const Size(412, 915),
        'Wide Phone (480px)': const Size(480, 800),
      };

      for (final entry in screenSizes.entries) {
        testWidgets('NotificationsScreen adapts without overflow on ${entry.key}', (WidgetTester tester) async {
          tester.view.physicalSize = entry.value;
          tester.view.devicePixelRatio = 1.0;
          addTearDown(() => tester.view.resetPhysicalSize());

          final repo = FakeNotificationsRepository(initialItems: sampleNotifications);
          await tester.pumpWidget(createTestWidget(repo: repo));
          await tester.pumpAndSettle();

          expect(tester.takeException(), isNull);
          expect(find.text('3 notifications'), findsOneWidget);

          // Activate selection mode on this screen size
          await tester.tap(find.byKey(const Key('select_mode_button')));
          await tester.pumpAndSettle();

          expect(tester.takeException(), isNull);
          expect(find.text('Select Notifications'), findsOneWidget);

          // Select an item
          await tester.tap(find.text('New Job Assigned'));
          await tester.pumpAndSettle();

          expect(tester.takeException(), isNull);
          expect(find.text('1 of 3 selected'), findsOneWidget);
          expect(find.byKey(const Key('delete_selected_button')), findsOneWidget);
        });
      }
    });
  });
}
