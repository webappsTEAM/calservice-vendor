import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../routing/app_routes.dart';
import '../../../../shared/widgets/status_chip.dart';
import '../../../../shared/widgets/workforce_app_bar.dart';
import '../admin_dashboard_providers.dart';
import '../widgets/admin_drawer.dart';

/// Admin Company Profile Screen.
/// Displays organization legal details, primary administrator, verification status, and business entities.
class AdminProviderProfileScreen extends ConsumerWidget {
  const AdminProviderProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(adminProviderProfileProvider);

    return Scaffold(
      appBar: const WorkforceAppBar(
        titleText: 'Company Profile',
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(adminProviderProfileProvider);
          await ref.read(adminProviderProfileProvider.future);
        },
        child: profileAsync.when(
          loading: () => const Center(
            child: Padding(
              padding: EdgeInsets.all(AppSpacing.xl),
              child: CircularProgressIndicator(),
            ),
          ),
          error: (err, _) => Center(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.error_outline_rounded, color: Color(0xFFDC2626), size: 40),
                  const SizedBox(height: 12),
                  Text('Failed to load company profile: $err', textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () => ref.invalidate(adminProviderProfileProvider),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          ),
          data: (profile) {
            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(AppSpacing.md),
              children: [
                // ── Hero Organization Card ─────────────────────────────────
                Container(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(AppRadius.card),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x040A2540),
                        blurRadius: 4,
                        offset: Offset(0, 1.5),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 52,
                            height: 52,
                            decoration: BoxDecoration(
                              color: const Color(0xFF004E89),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: const Center(
                              child: Icon(
                                Icons.apartment_rounded,
                                color: Colors.white,
                                size: 28,
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        profile.companyName,
                                        style: const TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.w900,
                                          color: Color(0xFF0F172A),
                                        ),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    StatusChip(
                                      status: profile.isActive ? 'active' : 'inactive',
                                    ),
                                    const SizedBox(width: 6),
                                    if (profile.isVerified)
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFECFDF5),
                                          borderRadius: BorderRadius.circular(4),
                                          border: Border.all(color: const Color(0xFFA7F3D0)),
                                        ),
                                        child: const Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(Icons.verified_rounded, size: 12, color: Color(0xFF059669)),
                                            SizedBox(width: 3),
                                            Text(
                                              'VERIFIED',
                                              style: TextStyle(
                                                fontSize: 9.5,
                                                fontWeight: FontWeight.w800,
                                                color: Color(0xFF059669),
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Divider(height: 1, color: Color(0xFFF1F5F9)),
                      const SizedBox(height: 12),

                      // Metric Strip
                      Row(
                        children: [
                          Expanded(
                            child: _buildMetricTile(
                              label: 'Tied Technicians',
                              value: '${profile.tiedTechniciansCount}',
                              icon: Icons.groups_rounded,
                              color: const Color(0xFF004E89),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: _buildMetricTile(
                              label: 'Entity Code',
                              value: profile.companyCode ?? '#${profile.id}',
                              icon: Icons.badge_outlined,
                              color: const Color(0xFF7C3AED),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.md),

                // ── Business Information ───────────────────────────────────
                _buildInfoSection(
                  title: 'Business Information',
                  icon: Icons.business_center_outlined,
                  children: [
                    _buildInfoRow('Legal Company Name', profile.companyName),
                    if (profile.registrationNumber != null)
                      _buildInfoRow('Registration / Tax No', profile.registrationNumber!),
                    if (profile.email != null)
                      _buildInfoRow('Contact Email', profile.email!),
                    if (profile.phone != null)
                      _buildInfoRow('Contact Phone', profile.phone!),
                    _buildInfoRow('Headquarters Address', profile.fullAddress),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),

                // ── Primary Administrator ──────────────────────────────────
                if (profile.primaryAdmin != null) ...[
                  _buildInfoSection(
                    title: 'Primary Administrator',
                    icon: Icons.admin_panel_settings_outlined,
                    children: [
                      _buildInfoRow(
                        'Admin Name',
                        '${profile.primaryAdmin!['first_name'] ?? ''} ${profile.primaryAdmin!['last_name'] ?? ''}'.trim().isEmpty
                            ? (profile.primaryAdmin!['username'] ?? 'Primary Admin').toString()
                            : '${profile.primaryAdmin!['first_name'] ?? ''} ${profile.primaryAdmin!['last_name'] ?? ''}'.trim(),
                      ),
                      if (profile.primaryAdmin!['email'] != null)
                        _buildInfoRow('Admin Email', profile.primaryAdmin!['email'].toString()),
                      if (profile.primaryAdmin!['username'] != null)
                        _buildInfoRow('Username', profile.primaryAdmin!['username'].toString()),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                ],

                // ── Quick Operations Links ─────────────────────────────────
                Container(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(AppRadius.card),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Quick Operations',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 10),
                      _buildNavRow(
                        icon: Icons.people_alt_rounded,
                        title: 'Tied Technicians Roster',
                        onTap: () => context.push(AppRoutes.adminTiedTechnicians),
                      ),
                      const Divider(height: 1, color: Color(0xFFF1F5F9)),
                      _buildNavRow(
                        icon: Icons.send_rounded,
                        title: 'Dispatch Radar Console',
                        onTap: () => context.push(AppRoutes.adminDispatch),
                      ),
                      const Divider(height: 1, color: Color(0xFFF1F5F9)),
                      _buildNavRow(
                        icon: Icons.account_balance_wallet_rounded,
                        title: 'Company Wallet & Ledger',
                        onTap: () => context.push(AppRoutes.adminFinanceWallets),
                      ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildMetricTile({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.15)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                    color: color,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF64748B),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoSection({
    required String title,
    required IconData icon,
    required List<Widget> children,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: const Color(0xFF004E89)),
              const SizedBox(width: 6),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF0F172A),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          const Divider(height: 1, color: Color(0xFFF1F5F9)),
          const SizedBox(height: 8),
          ...children,
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: Color(0xFF64748B),
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: Color(0xFF0F172A),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNavRow({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          children: [
            Icon(icon, size: 18, color: const Color(0xFF004E89)),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF334155),
                ),
              ),
            ),
            const Icon(Icons.chevron_right_rounded, size: 18, color: Color(0xFF94A3B8)),
          ],
        ),
      ),
    );
  }
}
