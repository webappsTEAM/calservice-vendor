import 'package:flutter/material.dart';

import '../../../../../core/theme/app_theme.dart';
import '../superadmin_vendor_providers.dart';

/// Overview summary metrics cards and primary platform action for the Vendor Directory.
class VendorDirectoryMetricsCards extends StatelessWidget {
  const VendorDirectoryMetricsCards({
    super.key,
    required this.metrics,
    required this.onManageWorkforce,
  });

  final VendorDirectoryMetrics metrics;
  final VoidCallback onManageWorkforce;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Top Action: Manage All Workforce (Solo & Tied)
        Material(
          color: const Color(0xFF004E89), // Peacock Blue
          borderRadius: BorderRadius.circular(AppRadius.card),
          elevation: 1,
          shadowColor: const Color(0xFF004E89).withValues(alpha: 0.3),
          child: InkWell(
            onTap: onManageWorkforce,
            borderRadius: BorderRadius.circular(AppRadius.card),
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.md,
                vertical: 12,
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(7),
                    decoration: const BoxDecoration(
                      color: Colors.white24,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.groups_rounded,
                      color: Colors.white,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Manage All Workforce (Solo & Tied)',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 13.5,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.2,
                          ),
                        ),
                        SizedBox(height: 1),
                        Text(
                          'Platform-wide technician directory & assignment',
                          style: TextStyle(
                            color: Color(0xFFBAE6FD),
                            fontSize: 11,
                            fontWeight: FontWeight.w400,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Icon(
                    Icons.arrow_forward_ios_rounded,
                    color: Colors.white70,
                    size: 14,
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Metrics Grid (Responsive Layout)
        LayoutBuilder(
          builder: (context, constraints) {
            final isNarrow = constraints.maxWidth < 360;

            final registeredCard = _MetricTile(
              label: 'REGISTERED VENDORS',
              value: '${metrics.registeredVendors}',
              icon: Icons.business_rounded,
              valueColor: const Color(0xFF0F172A),
              accentColor: const Color(0xFF2563EB),
            );

            final tiedCard = _MetricTile(
              label: 'TOTAL TIED WORKFORCE',
              value: '${metrics.totalTiedWorkforce}',
              icon: Icons.link_rounded,
              valueColor: const Color(0xFF059669),
              accentColor: const Color(0xFF059669),
            );

            if (isNarrow) {
              return Column(
                children: [
                  registeredCard,
                  const SizedBox(height: 8),
                  tiedCard,
                ],
              );
            }

            return Row(
              children: [
                Expanded(child: registeredCard),
                const SizedBox(width: 8),
                Expanded(child: tiedCard),
              ],
            );
          },
        ),
        const SizedBox(height: 8),

        // Platform Operations Banner
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Row(
            children: [
              Icon(
                Icons.shield_rounded,
                size: 18,
                color: Color(0xFF004E89),
              ),
              SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'PLATFORM OPERATIONS',
                      style: TextStyle(
                        fontSize: 9.5,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF64748B),
                        letterSpacing: 0.5,
                      ),
                    ),
                    SizedBox(height: 1),
                    Text(
                      'Multi-Tenant Architecture Active',
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF004E89),
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: const BoxDecoration(
                  color: Color(0xFFDCFCE7),
                  borderRadius: BorderRadius.all(Radius.circular(4)),
                ),
                child: const Text(
                  'LIVE',
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w900,
                    color: Color(0xFF15803D),
                    letterSpacing: 0.4,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.label,
    required this.value,
    required this.icon,
    required this.valueColor,
    required this.accentColor,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color valueColor;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x05000000),
            blurRadius: 3,
            offset: Offset(0, 1),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(
                  label,
                  style: const TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF64748B),
                    letterSpacing: 0.5,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Icon(icon, size: 16, color: accentColor),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w900,
              color: valueColor,
              letterSpacing: -0.5,
            ),
          ),
        ],
      ),
    );
  }
}
