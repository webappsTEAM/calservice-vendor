import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/admin_monitoring.dart';

/// Network Guardrails & Traffic Optimizations section.
class NetworkGuardrailsSection extends StatelessWidget {
  const NetworkGuardrailsSection({
    super.key,
    required this.data,
  });

  final AdminMonitoringData data;

  @override
  Widget build(BuildContext context) {
    final optimizations = data.apiTrafficOptimizations;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ── Section Title & Subtitle ─────────────────────────────────────
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Network Guardrails & Optimizations',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w900,
                      color: Color(0xFF0A2540),
                      letterSpacing: -0.3,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'What was fixed?',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textMuted,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFF004E89).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: const Color(0xFF004E89).withValues(alpha: 0.25)),
              ),
              child: const Text(
                'Code-Derived',
                style: TextStyle(
                  fontSize: 9.5,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF004E89),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),

        // ── Guardrail Cards ─────────────────────────────────────────────
        ...optimizations.map((opt) => _GuardrailCard(optimization: opt)),
      ],
    );
  }
}

class _GuardrailCard extends StatefulWidget {
  const _GuardrailCard({required this.optimization});

  final TrafficOptimization optimization;

  @override
  State<_GuardrailCard> createState() => _GuardrailCardState();
}

class _GuardrailCardState extends State<_GuardrailCard> {
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    final opt = widget.optimization;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x040A2540),
            blurRadius: 3,
            offset: Offset(0, 1),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () => setState(() => _isExpanded = !_isExpanded),
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top Row: Title + Status
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: const Color(0xFFECFDF5),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Icon(
                        Icons.verified_outlined,
                        size: 16,
                        color: Color(0xFF059669),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            opt.title,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF0A2540),
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            opt.endpoint,
                            style: const TextStyle(
                              fontSize: 10.5,
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF004E89),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFFECFDF5),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: const Color(0xFFA7F3D0)),
                      ),
                      child: Text(
                        opt.status,
                        style: const TextStyle(
                          fontSize: 9.5,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF059669),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),

                // Explanation
                Text(
                  opt.simpleExplanation,
                  style: TextStyle(
                    fontSize: 11.5,
                    color: AppColors.textSecondary,
                    height: 1.35,
                  ),
                ),

                // Expanded Technical Details
                if (_isExpanded) ...[
                  const SizedBox(height: 8),
                  const Divider(height: 1, color: Color(0xFFE2E8F0)),
                  const SizedBox(height: 8),
                  if (opt.mechanism != null && opt.mechanism!.isNotEmpty) ...[
                    _buildDetailRow('Mechanism', opt.mechanism!),
                    const SizedBox(height: 4),
                  ],
                  if (opt.serializer != null && opt.serializer!.isNotEmpty) ...[
                    _buildDetailRow('Serializer', opt.serializer!),
                    const SizedBox(height: 4),
                  ],
                  if (opt.payloadReduction.isNotEmpty) ...[
                    _buildDetailRow('Payload Effect', opt.payloadReduction),
                    const SizedBox(height: 4),
                  ],
                  _buildDetailRow('Measurement Type', opt.measurementType),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '$label: ',
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w700,
            color: Color(0xFF64748B),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(
              fontSize: 11,
              fontFamily: 'monospace',
              fontWeight: FontWeight.w600,
              color: Color(0xFF1E293B),
            ),
          ),
        ),
      ],
    );
  }
}
