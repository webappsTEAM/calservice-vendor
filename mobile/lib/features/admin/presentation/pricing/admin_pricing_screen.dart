import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/app_card.dart';
import '../../../../shared/widgets/empty_state.dart';
import '../../../../shared/widgets/workforce_app_bar.dart';
import '../../data/admin_dashboard_api.dart';
import '../../domain/admin_pricing_policy.dart';
import '../widgets/admin_drawer.dart';
import 'admin_pricing_providers.dart';

/// Super Admin / SEVO Platform Pricing & Approval Rules Screen.
///
/// Sets what a consultation visit costs, when a quote needs review before
/// the customer sees it, advance payment requirements, and structural clearance rules.
class AdminPricingApprovalsScreen extends ConsumerStatefulWidget {
  const AdminPricingApprovalsScreen({super.key});

  @override
  ConsumerState<AdminPricingApprovalsScreen> createState() =>
      _AdminPricingApprovalsScreenState();
}

class _AdminPricingApprovalsScreenState
    extends ConsumerState<AdminPricingApprovalsScreen> {
  Future<void> _refresh() async {
    ref.invalidate(adminPricingPoliciesProvider);
  }

  @override
  Widget build(BuildContext context) {
    final policiesAsync = ref.watch(adminPricingPoliciesProvider);

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
                              colors: [Color(0xFF7C3AED), Color(0xFF6D28D9)],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(
                            Icons.price_change_rounded,
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
                                'Pricing & Approval Rules',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF0F172A),
                                  letterSpacing: -0.2,
                                ),
                              ),
                              SizedBox(height: 3),
                              Text(
                                'Applies to new quotations and bookings. Invoices already issued keep the figures they were issued with.',
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

              // ── Async Policies List ────────────────────────────────────────
              policiesAsync.when(
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
                        'Unable to load pricing policies',
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
                data: (policies) {
                  if (policies.isEmpty) {
                    return AppCard(
                      padding: const EdgeInsets.symmetric(
                          vertical: 40, horizontal: 16),
                      child: const EmptyState(
                        icon: Icons.price_change_outlined,
                        title: 'No pricing policies found.',
                        message: 'No service category pricing policies configured.',
                      ),
                    );
                  }

                  return Column(
                    children: policies.map((policy) {
                      return _CategoryPricingPolicyCard(
                        key: ValueKey(policy.id),
                        policy: policy,
                        onSaved: (msg) {
                          _refresh();
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(msg),
                              backgroundColor: const Color(0xFF059669),
                            ),
                          );
                        },
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

/// Reusable Pricing Policy Card for any service category (AC, Masonry, Painting, etc.)
class _CategoryPricingPolicyCard extends ConsumerStatefulWidget {
  const _CategoryPricingPolicyCard({
    super.key,
    required this.policy,
    required this.onSaved,
  });

  final AdminPricingPolicy policy;
  final void Function(String message) onSaved;

  @override
  ConsumerState<_CategoryPricingPolicyCard> createState() =>
      _CategoryPricingPolicyCardState();
}

class _CategoryPricingPolicyCardState
    extends ConsumerState<_CategoryPricingPolicyCard> {
  late String _feeMode;
  late TextEditingController _feeAmountController;
  late TextEditingController _freeRadiusController;
  late TextEditingController _beyondRadiusController;
  late TextEditingController _thresholdController;
  late TextEditingController _advancePercentController;
  late bool _requiresApproval;
  late bool _allowCustomerMaterials;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _feeMode = widget.policy.consultationFeeMode;
    _feeAmountController = TextEditingController(
      text: widget.policy.consultationFeeAmount > 0
          ? widget.policy.consultationFeeAmount.toStringAsFixed(0)
          : '0',
    );
    _freeRadiusController = TextEditingController(
      text: widget.policy.freeRadiusKm > 0
          ? widget.policy.freeRadiusKm.toStringAsFixed(0)
          : '15',
    );
    _beyondRadiusController = TextEditingController(
      text: widget.policy.beyondRadiusAmount > 0
          ? widget.policy.beyondRadiusAmount.toStringAsFixed(0)
          : '300',
    );
    _thresholdController = TextEditingController(
      text: widget.policy.highValueReviewThreshold != null
          ? widget.policy.highValueReviewThreshold!.toStringAsFixed(0)
          : '',
    );
    _advancePercentController = TextEditingController(
      text: widget.policy.advancePercent.toStringAsFixed(0),
    );
    _requiresApproval = widget.policy.requiresAdminApproval;
    _allowCustomerMaterials = widget.policy.allowCustomerSuppliedMaterials;
  }

  @override
  void dispose() {
    _feeAmountController.dispose();
    _freeRadiusController.dispose();
    _beyondRadiusController.dispose();
    _thresholdController.dispose();
    _advancePercentController.dispose();
    super.dispose();
  }

  Future<void> _saveChanges() async {
    final advance = double.tryParse(_advancePercentController.text.trim()) ?? 100.0;
    if (advance < 0 || advance > 100) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Advance percentage must be between 0 and 100.'),
          backgroundColor: Color(0xFFDC2626),
        ),
      );
      return;
    }

    setState(() => _isSaving = true);
    try {
      final thresholdText = _thresholdController.text.trim();
      final double? thresholdVal =
          thresholdText.isEmpty ? null : double.tryParse(thresholdText);

      final payload = <String, dynamic>{
        'consultation_fee_mode': _feeMode,
        'consultation_fee_amount':
            double.tryParse(_feeAmountController.text.trim()) ?? 0.0,
        'free_radius_km':
            double.tryParse(_freeRadiusController.text.trim()) ?? 15.0,
        'beyond_radius_amount':
            double.tryParse(_beyondRadiusController.text.trim()) ?? 300.0,
        'high_value_review_threshold': thresholdVal,
        'advance_percent': advance,
        'requires_admin_approval': _requiresApproval,
        'allow_customer_supplied_materials': _allowCustomerMaterials,
      };

      final api = ref.read(adminDashboardApiProvider);
      await api.updatePricingPolicy(widget.policy.id, payload);

      if (mounted) {
        widget.onSaved('${widget.policy.effectiveTitle} policy updated successfully.');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save policy: $e'),
            backgroundColor: const Color(0xFFDC2626),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x040F172A),
            blurRadius: 6,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Category Header ───────────────────────────────────────────────
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.policy.effectiveTitle,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Category: ${widget.policy.serviceCategory}',
                      style: const TextStyle(
                        fontSize: 11.5,
                        color: Color(0xFF64748B),
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ),
              if (widget.policy.isActive)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0xFFECFDF5),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0xFFA7F3D0)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.check_circle_rounded,
                          size: 12, color: Color(0xFF059669)),
                      SizedBox(width: 4),
                      Text(
                        'Policy active',
                        style: TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF065F46),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 14),
          const Divider(height: 1, color: Color(0xFFF1F5F9)),
          const SizedBox(height: 12),

          // ── Consultation Fee Mode ─────────────────────────────────────────
          const Text(
            'Consultation Fee',
            style: TextStyle(
              fontSize: 12.5,
              fontWeight: FontWeight.w800,
              color: Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 6),
          DropdownButtonFormField<String>(
            initialValue: _feeMode,
            isExpanded: true,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              contentPadding:
                  EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            ),
            items: const [
              DropdownMenuItem(
                value: 'FREE',
                child: Text('Always free', style: TextStyle(fontSize: 13)),
              ),
              DropdownMenuItem(
                value: 'FLAT',
                child: Text('Flat fee', style: TextStyle(fontSize: 13)),
              ),
              DropdownMenuItem(
                value: 'DISTANCE_BAND',
                child: Text('Free within radius, fee beyond',
                    style: TextStyle(fontSize: 13)),
              ),
            ],
            onChanged: (val) {
              if (val != null) setState(() => _feeMode = val);
            },
          ),
          const SizedBox(height: 10),

          // Conditional fields based on fee mode
          if (_feeMode == 'FLAT') ...[
            TextField(
              controller: _feeAmountController,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Fee amount (₹)',
                border: OutlineInputBorder(),
                prefixText: '₹ ',
              ),
            ),
            const SizedBox(height: 12),
          ] else if (_feeMode == 'DISTANCE_BAND') ...[
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _freeRadiusController,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'Free within (km)',
                      border: OutlineInputBorder(),
                      suffixText: 'km',
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _beyondRadiusController,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'Fee beyond that (₹)',
                      border: OutlineInputBorder(),
                      prefixText: '₹ ',
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
          ],

          // ── Quote Review Threshold ────────────────────────────────────────
          TextField(
            controller: _thresholdController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
              labelText: 'Review quotes above (₹)',
              border: OutlineInputBorder(),
              prefixText: '₹ ',
              helperText: 'Blank means no pre-send review for this category.',
            ),
          ),
          const SizedBox(height: 12),

          // ── Advance Payment ───────────────────────────────────────────────
          TextField(
            controller: _advancePercentController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
              labelText: 'Advance payable (%)',
              border: OutlineInputBorder(),
              suffixText: '%',
              helperText: '100 bills the whole invoice up front.',
            ),
          ),
          const SizedBox(height: 12),

          // ── Approval Policy Toggle ────────────────────────────────────────
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Expanded(
                child: Text(
                  'SEVO approves accepted quotes before work is scheduled',
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF1E293B),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Switch.adaptive(
                value: _requiresApproval,
                activeTrackColor: const Color(0xFF7C3AED),
                onChanged: (val) => setState(() => _requiresApproval = val),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Divider(height: 1, color: Color(0xFFF1F5F9)),
          const SizedBox(height: 6),

          // ── Customer-Supplied Materials Toggle ────────────────────────────
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Allow customer-supplied materials',
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF1E293B),
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Off by default — customer-supplied material voids the workmanship warranty.',
                      style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Switch.adaptive(
                value: _allowCustomerMaterials,
                activeTrackColor: const Color(0xFF7C3AED),
                onChanged: (val) => setState(() => _allowCustomerMaterials = val),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // ── Save Action ───────────────────────────────────────────────────
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _isSaving ? null : _saveChanges,
              icon: _isSaving
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.save_rounded, size: 15),
              label: Text(_isSaving ? 'Saving...' : 'Save'),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF0F172A),
                padding: const EdgeInsets.symmetric(vertical: 11),
                textStyle: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
