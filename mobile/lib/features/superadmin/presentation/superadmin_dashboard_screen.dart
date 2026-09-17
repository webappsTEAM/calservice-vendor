import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/async_value_view.dart';
import '../../../shared/widgets/workforce_app_bar.dart';
import '../../admin/presentation/widgets/admin_drawer.dart';
import '../domain/superadmin_dashboard.dart';
import 'superadmin_dashboard_providers.dart';
import 'widgets/action_center_card.dart';
import 'widgets/recent_operation_card.dart';
import 'widgets/superadmin_dashboard_header.dart';
import 'widgets/workforce_metric_card.dart';

/// The official Super Admin Platform Dashboard (Workforce Operations Center).
///
/// Provides live monitoring, dossier verification, and dynamic dispatch overview
/// natively adapted for mobile screens with zero mock data.
class SuperAdminDashboardScreen extends ConsumerWidget {
  const SuperAdminDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardAsync = ref.watch(superAdminDashboardDataProvider);

    return Scaffold(
      appBar: const WorkforceAppBar(
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(superAdminDashboardDataProvider);
          await ref.read(superAdminDashboardDataProvider.future);
        },
        child: AsyncValueView<SuperAdminDashboardData>(
          value: dashboardAsync,
          errorMessage: 'Unable to load platform dashboard',
          onRetry: () => ref.invalidate(superAdminDashboardDataProvider),
          builder: (context, data) {
            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.md,
                AppSpacing.md,
                AppSpacing.md,
                AppSpacing.xxl,
              ),
              children: [
                // 1. Executive Page Header & Direct Actions
                SuperAdminDashboardHeader(
                  onRefresh: () => ref.invalidate(superAdminDashboardDataProvider),
                  isRefreshing: dashboardAsync.isLoading,
                ),
                const SizedBox(height: 20),

                // 2. Action Center (4 Operational Queues)
                SuperAdminActionCenterSection(data: data),
                const SizedBox(height: 20),

                // 3. Workforce Overview (5 Key Metric Cards)
                SuperAdminWorkforceOverviewSection(data: data),
                const SizedBox(height: 20),

                // 4. Recent Operations & Service Bookings Feed
                SuperAdminRecentOperationsSection(data: data),
              ],
            );
          },
        ),
      ),
    );
  }
}
