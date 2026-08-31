import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/data/admin_finance_repository.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';

/// Modal dialog for an administrator to post a manual credit or debit adjustment.
class AdminAdjustmentDialog extends ConsumerStatefulWidget {
  const AdminAdjustmentDialog({
    super.key,
    required this.wallet,
  });

  final AdminWallet wallet;

  static Future<bool?> show(BuildContext context, AdminWallet wallet) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AdminAdjustmentDialog(wallet: wallet),
    );
  }

  @override
  ConsumerState<AdminAdjustmentDialog> createState() => _AdminAdjustmentDialogState();
}

class _AdminAdjustmentDialogState extends ConsumerState<AdminAdjustmentDialog> {
  final _formKey = GlobalKey<FormState>();
  String _direction = 'CREDIT';
  final _amountController = TextEditingController();
  final _reasonController = TextEditingController();
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _amountController.dispose();
    _reasonController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final amount = double.tryParse(_amountController.text.trim());
    if (amount == null || amount <= 0) {
      setState(() => _errorMessage = 'Please enter a valid positive amount.');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      await ref.read(adminFinanceRepositoryProvider).postAdjustment(
            employeeId: widget.wallet.employeeId,
            direction: _direction,
            amount: amount,
            reason: _reasonController.text.trim(),
          );
      ref.invalidate(adminWalletsProvider);
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
          _errorMessage = e.toString().replaceAll('Exception:', '').trim();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Manual Balance Adjustment',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 2),
          Text(
            '${widget.wallet.employeeName} (EMP-${widget.wallet.employeeId})',
            style: TextStyle(fontSize: 12, color: AppColors.textMuted),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (_errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF1F2),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFFFECDD3)),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: const TextStyle(fontSize: 12, color: Color(0xFFE11D48)),
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
              ],

              // Current Balance Info
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.surfaceMuted,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Current Available:', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                    Text(
                      '₹${widget.wallet.availableBalance.toStringAsFixed(2)}',
                      style: const TextStyle(
                        fontSize: 13,
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // Direction Selector (CREDIT vs DEBIT)
              const Text(
                'Adjustment Type *',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  Expanded(
                    child: ChoiceChip(
                      label: const Center(child: Text('CREDIT (+)')),
                      selected: _direction == 'CREDIT',
                      selectedColor: const Color(0xFFDCFCE7),
                      labelStyle: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        color: _direction == 'CREDIT' ? const Color(0xFF15803D) : const Color(0xFF64748B),
                      ),
                      onSelected: (selected) {
                        if (selected) setState(() => _direction = 'CREDIT');
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: ChoiceChip(
                      label: const Center(child: Text('DEBIT (-)')),
                      selected: _direction == 'DEBIT',
                      selectedColor: const Color(0xFFFEE2E2),
                      labelStyle: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        color: _direction == 'DEBIT' ? const Color(0xFFB91C1C) : const Color(0xFF64748B),
                      ),
                      onSelected: (selected) {
                        if (selected) setState(() => _direction = 'DEBIT');
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),

              // Amount Input
              const Text(
                'Adjustment Amount (₹) *',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              TextFormField(
                controller: _amountController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  hintText: '0.00',
                  prefixText: '₹ ',
                ),
                validator: (val) {
                  if (val == null || val.trim().isEmpty) return 'Amount is required.';
                  final parsed = double.tryParse(val.trim());
                  if (parsed == null || parsed <= 0) return 'Enter a positive amount.';
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.md),

              // Audit Reason Input
              const Text(
                'Audit Reason *',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              TextFormField(
                controller: _reasonController,
                maxLines: 2,
                decoration: const InputDecoration(
                  hintText: 'Reason for balance adjustment (e.g. bonus, correction)...',
                ),
                validator: (val) {
                  if (val == null || val.trim().length < 3) {
                    return 'Reason must be at least 3 characters.';
                  }
                  return null;
                },
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isSubmitting ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _isSubmitting ? null : _submit,
          style: FilledButton.styleFrom(
            backgroundColor: _direction == 'CREDIT' ? const Color(0xFF059669) : const Color(0xFFDC2626),
          ),
          child: _isSubmitting
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
              : Text('Post $_direction'),
        ),
      ],
    );
  }
}
