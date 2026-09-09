import 'package:flutter/material.dart';

import '../../../../../core/theme/app_theme.dart';
import '../../domain/platform_worker.dart';

/// Card widget displaying a single technician with live classification, skills, contact and tie actions.
class WorkerCard extends StatelessWidget {
  const WorkerCard({
    super.key,
    required this.worker,
    required this.onManageTie,
  });

  final PlatformWorker worker;
  final VoidCallback onManageTie;

  @override
  Widget build(BuildContext context) {
    final isTied = worker.isTied;
    final initial =
        worker.name.isNotEmpty ? worker.name[0].toUpperCase() : 'T';

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(
          color: isTied ? const Color(0xFFD1FAE5) : const Color(0xFFE2E8F0),
        ),
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
          // ── Top Header Row ──────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Avatar with online status indicator
                Stack(
                  children: [
                    CircleAvatar(
                      radius: 20,
                      backgroundColor: isTied
                          ? const Color(0xFFECFDF5)
                          : const Color(0xFFEFF6FF),
                      child: Text(
                        initial,
                        style: TextStyle(
                          color: isTied
                              ? const Color(0xFF065F46)
                              : const Color(0xFF1E40AF),
                          fontWeight: FontWeight.w800,
                          fontSize: 15,
                        ),
                      ),
                    ),
                    Positioned(
                      bottom: 0,
                      right: 0,
                      child: Container(
                        width: 10,
                        height: 10,
                        decoration: BoxDecoration(
                          color: worker.isOnline
                              ? const Color(0xFF10B981)
                              : const Color(0xFF94A3B8),
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 1.5),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 10),
                // Worker Name and ID
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        worker.name,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF0F172A),
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Row(
                        children: [
                          Text(
                            worker.employeeId.isNotEmpty
                                ? worker.employeeId
                                : '#${worker.id}',
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF64748B),
                              fontFamily: 'monospace',
                            ),
                          ),
                          if (worker.city.isNotEmpty) ...[
                            const SizedBox(width: 6),
                            const Text(
                              '•',
                              style: TextStyle(
                                fontSize: 10,
                                color: Color(0xFFCBD5E1),
                              ),
                            ),
                            const SizedBox(width: 6),
                            Flexible(
                              child: Text(
                                worker.city,
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: Color(0xFF64748B),
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 6),
                // Classification Pill Badge (SOLO vs TIED)
                _ClassificationBadge(isTied: isTied),
              ],
            ),
          ),

          // ── Tied Vendor Banner (if tied) ─────────────────────────────────
          if (isTied && worker.tiedVendor != null)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm + 2,
                vertical: 6,
              ),
              decoration: BoxDecoration(
                color: const Color(0xFFF0FDF4),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFFA7F3D0)),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.business_rounded,
                    size: 14,
                    color: Color(0xFF059669),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'Tied to:',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF065F46),
                    ),
                  ),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      worker.tiedVendor!.companyName,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF064E3B),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),

          // ── Trade Skills & Service Capabilities ──────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.md,
              AppSpacing.xs + 2,
              AppSpacing.md,
              AppSpacing.xs,
            ),
            child: Wrap(
              spacing: 4,
              runSpacing: 4,
              children: [
                if (worker.skills.isNotEmpty)
                  ...worker.skills.take(3).map(
                        (skill) => Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF1F5F9),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            skill,
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF475569),
                            ),
                          ),
                        ),
                      ),
                if (worker.skills.length > 3)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE2E8F0),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '+${worker.skills.length - 3} more',
                      style: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF64748B),
                      ),
                    ),
                  ),
                if (worker.skills.isEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF8FAFC),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: const Text(
                      'General Technician',
                      style: TextStyle(
                        fontSize: 10,
                        fontStyle: FontStyle.italic,
                        color: Color(0xFF94A3B8),
                      ),
                    ),
                  ),
              ],
            ),
          ),

          // ── Contact & Details Row ────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (worker.phone.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.phone_outlined,
                          size: 13,
                          color: Color(0xFF94A3B8),
                        ),
                        const SizedBox(width: 5),
                        Text(
                          worker.phone,
                          style: const TextStyle(
                            fontSize: 11,
                            color: Color(0xFF475569),
                          ),
                        ),
                      ],
                    ),
                  ),
                if (worker.email.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.mail_outline_rounded,
                          size: 13,
                          color: Color(0xFF94A3B8),
                        ),
                        const SizedBox(width: 5),
                        Expanded(
                          child: Text(
                            worker.email,
                            style: const TextStyle(
                              fontSize: 11,
                              color: Color(0xFF475569),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),

          const SizedBox(height: AppSpacing.sm),
          const Divider(height: 1, color: Color(0xFFF1F5F9)),

          // ── Bottom Actions Bar ───────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.xs + 2,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Status Indicator
                Flexible(
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: worker.registrationStatus.toLowerCase() == 'approved'
                              ? const Color(0xFF10B981)
                              : const Color(0xFFF59E0B),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 5),
                      Flexible(
                        child: Text(
                          worker.registrationStatus.toUpperCase(),
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            color: worker.registrationStatus.toLowerCase() == 'approved'
                                ? const Color(0xFF047857)
                                : const Color(0xFFB45309),
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                // Tie / Reassign Action Button
                InkWell(
                  onTap: onManageTie,
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: isTied
                          ? const Color(0xFFFFFBEB)
                          : const Color(0xFFEEF2FF),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: isTied
                            ? const Color(0xFFFDE68A)
                            : const Color(0xFFC7D2FE),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          isTied
                              ? Icons.sync_rounded
                              : Icons.link_rounded,
                          size: 12,
                          color: isTied
                              ? const Color(0xFFB45309)
                              : const Color(0xFF4338CA),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          isTied ? 'Reassign / Untie' : 'Tie to Vendor',
                          style: TextStyle(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w800,
                            color: isTied
                                ? const Color(0xFF92400E)
                                : const Color(0xFF3730A3),
                          ),
                        ),
                      ],
                    ),
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

class _ClassificationBadge extends StatelessWidget {
  const _ClassificationBadge({required this.isTied});

  final bool isTied;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: isTied ? const Color(0xFFECFDF5) : const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isTied ? const Color(0xFFA7F3D0) : const Color(0xFFBFDBFE),
          width: 0.8,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isTied ? Icons.business_rounded : Icons.person_rounded,
            size: 11,
            color: isTied ? const Color(0xFF059669) : const Color(0xFF2563EB),
          ),
          const SizedBox(width: 3.5),
          Text(
            isTied ? 'TIED' : 'SOLO',
            style: TextStyle(
              fontSize: 9.5,
              fontWeight: FontWeight.w900,
              color: isTied ? const Color(0xFF065F46) : const Color(0xFF1E40AF),
              letterSpacing: 0.4,
            ),
          ),
        ],
      ),
    );
  }
}
