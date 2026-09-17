import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/app_card.dart';
import '../../../../shared/widgets/empty_state.dart';
import '../../../../shared/widgets/workforce_app_bar.dart';
import '../../data/admin_dashboard_api.dart';
import '../../domain/admin_social_security_registration.dart';
import '../widgets/admin_drawer.dart';
import 'admin_social_security_providers.dart';

/// Super Admin / SEVO Platform Social Security Compliance Screen.
///
/// Tracks 90+ days worked aggregator eligibility under the Code on Social Security, 2020
/// and records manual submissions to the Shram Suvidha portal.
class AdminSocialSecurityScreen extends ConsumerStatefulWidget {
  const AdminSocialSecurityScreen({super.key});

  @override
  ConsumerState<AdminSocialSecurityScreen> createState() =>
      _AdminSocialSecurityScreenState();
}

class _AdminSocialSecurityScreenState
    extends ConsumerState<AdminSocialSecurityScreen> {
  static const _statusFilters = [
    {'id': '', 'label': 'All statuses'},
    {'id': 'NOT_YET_ELIGIBLE', 'label': 'Not Yet Eligible'},
    {'id': 'ELIGIBLE_PENDING', 'label': 'Eligible — Pending'},
    {'id': 'REGISTERED', 'label': 'Registered'},
  ];

  Future<void> _refresh() async {
    ref.invalidate(adminSocialSecurityListProvider);
  }

  Future<void> _recordSubmission(AdminSocialSecurityRegistration reg) async {
    final refController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.card),
        ),
        title: Text(
          'Record Portal Submission for ${reg.employeeName}',
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Enter the Shram Suvidha / e-Shram portal reference or acknowledgment number:',
              style: TextStyle(fontSize: 12.5, color: Color(0xFF475569)),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: refController,
              decoration: const InputDecoration(
                labelText: 'Portal Reference ID',
                hintText: 'e.g. SS-2026-004921',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF0F172A),
            ),
            child: const Text('Record Submission'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final api = ref.read(adminDashboardApiProvider);
      await api.markSocialSecurityRegistered(
        registrationId: reg.registrationId,
        portalReferenceId: refController.text.trim(),
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                'Registration recorded for ${reg.employeeName}.'),
            backgroundColor: const Color(0xFF059669),
          ),
        );
        await _refresh();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to record registration: $e'),
            backgroundColor: const Color(0xFFDC2626),
          ),
        );
      }
    }
  }

  Color _getStatusBg(String status) {
    switch (status) {
      case 'REGISTERED':
        return const Color(0xFFECFDF5);
      case 'ELIGIBLE_PENDING':
        return const Color(0xFFFEF3C7);
      case 'NOT_YET_ELIGIBLE':
      default:
        return const Color(0xFFF1F5F9);
    }
  }

  Color _getStatusTextColor(String status) {
    switch (status) {
      case 'REGISTERED':
        return const Color(0xFF047857);
      case 'ELIGIBLE_PENDING':
        return const Color(0xFF92400E);
      case 'NOT_YET_ELIGIBLE':
      default:
        return const Color(0xFF475569);
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusFilter = ref.watch(adminSocialSecurityStatusFilterProvider);
    final registrationsAsync = ref.watch(adminSocialSecurityListProvider);
    final totalCount = registrationsAsync.valueOrNull?.length ?? 0;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: const WorkforceAppBar(
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _refresh,
          color: const Color(0xFF0F172A),
          child: ListView(
            padding: const EdgeInsets.all(AppSpacing.md),
            children: [
              // ── Screen Header ──────────────────────────────────────────────
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x040F172A),
                      blurRadius: 8,
                      offset: Offset(0, 2),
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
                          width: 42,
                          height: 42,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [Color(0xFF059669), Color(0xFF047857)],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(
                            Icons.health_and_safety_rounded,
                            color: Colors.white,
                            size: 22,
                          ),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Social Security',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF0F172A),
                                  letterSpacing: -0.2,
                                ),
                              ),
                              SizedBox(height: 3),
                              Text(
                                'Compliance tracking under the Code on Social Security, 2020.',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF64748B),
                                  height: 1.35,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    const Divider(height: 1, color: Color(0xFFF1F5F9)),
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        OutlinedButton.icon(
                          onPressed: _refresh,
                          icon: const Icon(Icons.refresh_rounded, size: 15),
                          label: const Text('Refresh'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF475569),
                            side: const BorderSide(color: Color(0xFFCBD5E1)),
                            visualDensity: VisualDensity.compact,
                            textStyle: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // ── Important Information Banner ───────────────────────────────
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFEFF6FF),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFBFDBFE)),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.info_outline_rounded,
                            size: 17, color: Color(0xFF1D4ED8)),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Individual workers only -- SEVO is the "aggregator" under the Code on Social Security, 2020 for this channel and must register eligible workers on the Shram Suvidha portal itself.',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF1E40AF),
                              height: 1.35,
                            ),
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 8),
                    Text(
                      'This page tracks eligibility (90+ days worked this financial year) and records that the manual portal submission actually happened; it does not submit anything automatically.',
                      style: TextStyle(
                        fontSize: 11.5,
                        color: Color(0xFF1E3A8A),
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // ── Main Section Heading: Registrations Count ──────────────────
              Text(
                'Social Security Code Registrations ($totalCount)',
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF0F172A),
                ),
              ),
              const SizedBox(height: AppSpacing.sm),

              // ── Status Filters Carousel ────────────────────────────────────
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: _statusFilters.map((st) {
                    final isSelected = statusFilter == st['id'];
                    return Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        label: Text(
                          st['label']!,
                          style: TextStyle(
                            fontSize: 11.5,
                            fontWeight: isSelected
                                ? FontWeight.w800
                                : FontWeight.w600,
                          ),
                        ),
                        selected: isSelected,
                        onSelected: (val) {
                          if (val) {
                            ref
                                .read(adminSocialSecurityStatusFilterProvider
                                    .notifier)
                                .state = st['id']!;
                          }
                        },
                        selectedColor: const Color(0xFF0F172A),
                        labelStyle: TextStyle(
                          color: isSelected
                              ? Colors.white
                              : const Color(0xFF334155),
                        ),
                        backgroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                          side: BorderSide(
                            color: isSelected
                                ? const Color(0xFF0F172A)
                                : const Color(0xFFE2E8F0),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // ── Registrations List ─────────────────────────────────────────
              registrationsAsync.when(
                loading: () => const Center(
                  child: Padding(
                    padding: EdgeInsets.all(AppSpacing.xxl),
                    child: CircularProgressIndicator(color: Color(0xFF0F172A)),
                  ),
                ),
                error: (err, _) => AppCard(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: Column(
                    children: [
                      const Icon(
                        Icons.error_outline_rounded,
                        color: Color(0xFFDC2626),
                        size: 36,
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'Unable to load registrations',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        err.toString(),
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFF64748B),
                        ),
                      ),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: _refresh,
                        icon: const Icon(Icons.refresh_rounded, size: 16),
                        label: const Text('Try again'),
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFF0F172A),
                        ),
                      ),
                    ],
                  ),
                ),
                data: (registrations) {
                  if (registrations.isEmpty) {
                    return AppCard(
                      padding: const EdgeInsets.symmetric(
                          vertical: 40, horizontal: 16),
                      child: const EmptyState(
                        icon: Icons.assignment_outlined,
                        title: 'No individual worker registrations to show.',
                        message: 'No worker records match the selected compliance criteria.',
                      ),
                    );
                  }

                  return Column(
                    children: registrations.map((reg) {
                      return _RegistrationCard(
                        registration: reg,
                        statusBg: _getStatusBg(reg.status),
                        statusTextColor: _getStatusTextColor(reg.status),
                        onRecordSubmission: () => _recordSubmission(reg),
                      );
                    }).toList(),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RegistrationCard extends StatelessWidget {
  const _RegistrationCard({
    required this.registration,
    required this.statusBg,
    required this.statusTextColor,
    required this.onRecordSubmission,
  });

  final AdminSocialSecurityRegistration registration;
  final Color statusBg;
  final Color statusTextColor;
  final VoidCallback onRecordSubmission;

  @override
  Widget build(BuildContext context) {
    final days = registration.daysWorkedCurrentFy;
    final progress = registration.progressToThreshold;

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x040F172A),
            blurRadius: 4,
            offset: Offset(0, 1),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: Worker Name + Status Badge
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      registration.employeeName,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Worker ID: #${registration.employeeId} · Reg #${registration.registrationId}',
                      style: const TextStyle(
                        fontSize: 11.5,
                        color: Color(0xFF64748B),
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 2.5),
                decoration: BoxDecoration(
                  color: statusBg,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  registration.statusDisplay,
                  style: TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w800,
                    color: statusTextColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(height: 1, color: Color(0xFFF1F5F9)),
          const SizedBox(height: 10),

          // Days Worked Progress
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Expanded(
                child: Text(
                  'FY Days Worked (90d statutory threshold)',
                  style: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF475569),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '$days / 90 days',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  color: days >= 90
                      ? const Color(0xFF059669)
                      : const Color(0xFF0F172A),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 6,
              backgroundColor: const Color(0xFFE2E8F0),
              color: days >= 90
                  ? const Color(0xFF059669)
                  : const Color(0xFF3B82F6),
            ),
          ),
          const SizedBox(height: 10),

          // Registration Metadata if available
          if (registration.isRegistered) ...[
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFF1F5F9)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (registration.portalReferenceId.isNotEmpty)
                    Text(
                      'Portal Reference: ${registration.portalReferenceId}',
                      style: const TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF0F172A),
                        fontFamily: 'monospace',
                      ),
                    ),
                  if (registration.registeredAt != null)
                    Text(
                      'Registered on ${registration.registeredAt!.day.toString().padLeft(2, '0')}/${registration.registeredAt!.month.toString().padLeft(2, '0')}/${registration.registeredAt!.year}${registration.registeredBy.isNotEmpty ? ' by ${registration.registeredBy}' : ''}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: Color(0xFF64748B),
                      ),
                    ),
                ],
              ),
            ),
          ] else if (registration.isEligiblePending) ...[
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: onRecordSubmission,
                icon: const Icon(Icons.edit_note_rounded, size: 16),
                label: const Text('Mark as Registered'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF0F172A),
                  side: const BorderSide(color: Color(0xFFCBD5E1)),
                  padding: const EdgeInsets.symmetric(vertical: 9),
                  textStyle: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
