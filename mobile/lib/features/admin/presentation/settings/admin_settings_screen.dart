import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/workforce_app_bar.dart';
import '../widgets/admin_drawer.dart';

/// Admin System Settings Screen.
/// Accessible from the bottom of the Admin Navigation Drawer.
class AdminSettingsScreen extends StatelessWidget {
  const AdminSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const WorkforceAppBar(
        titleText: 'System Settings',
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.md),
        children: [
          // Header Card
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
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(5),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: const Text(
                    'GOVERNANCE & CONFIGURATION',
                    style: TextStyle(
                      fontSize: 9.5,
                      fontWeight: FontWeight.w900,
                      color: Color(0xFF64748B),
                      letterSpacing: 0.6,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'System Settings',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                    color: Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 2),
                const Text(
                  'Manage administrative account security, preferences, notifications and privacy',
                  style: TextStyle(
                    fontSize: 12,
                    color: Color(0xFF64748B),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),

          _AdminSettingsMenuCard(
            icon: Icons.lock_outline_rounded,
            iconColor: const Color(0xFF2563EB),
            title: 'Account & Security',
            subtitle: 'Password, authentication, sessions & administrative access',
            onTap: () => context.push('/more/settings/security'),
          ),
          const SizedBox(height: AppSpacing.sm),
          _AdminSettingsMenuCard(
            icon: Icons.palette_outlined,
            iconColor: const Color(0xFF7C3AED),
            title: 'Appearance & UI',
            subtitle: 'Theme modes, contrast, text scaling & accessibility',
            onTap: () => context.push('/more/settings/appearance'),
          ),
          const SizedBox(height: AppSpacing.sm),
          _AdminSettingsMenuCard(
            icon: Icons.notifications_outlined,
            iconColor: const Color(0xFFD97706),
            title: 'Notifications & Alerts',
            subtitle: 'Dispatch alarms, dossier alerts & operational subscriptions',
            onTap: () => context.push('/more/settings/notifications'),
          ),
          const SizedBox(height: AppSpacing.sm),
          _AdminSettingsMenuCard(
            icon: Icons.shield_outlined,
            iconColor: const Color(0xFF059669),
            title: 'Privacy & Data Governance',
            subtitle: 'Data egress policies, audit exports & organization compliance',
            onTap: () => context.push('/more/settings/privacy'),
          ),
          const SizedBox(height: AppSpacing.lg),

          // Build & Environment Info
          Center(
            child: Column(
              children: [
                Text(
                  'SEVO Workforce Operations Platform v2.4.0',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textMuted,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Enterprise Mobile Operations Center • Multi-Tenant Compliant',
                  style: TextStyle(
                    fontSize: 10,
                    color: AppColors.textMuted.withValues(alpha: 0.8),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AdminSettingsMenuCard extends StatelessWidget {
  const _AdminSettingsMenuCard({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadius.card),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Row(
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: iconColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, size: 22, color: iconColor),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          fontSize: 13.5,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        subtitle,
                        style: const TextStyle(
                          fontSize: 11.5,
                          color: Color(0xFF64748B),
                        ),
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right_rounded, color: Color(0xFF94A3B8)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
