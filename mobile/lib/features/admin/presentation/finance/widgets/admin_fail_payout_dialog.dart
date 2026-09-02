import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/data/admin_finance_repository.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';

/// Modal dialog for administrator to mark a withdrawal as failed with reason.
class AdminFailPayoutDialog extends ConsumerStatefulWidget {
  const AdminFailPayoutDialog({
    super.key,
    required this.withdrawal,
  });

  final AdminWithdrawal withdrawal;

  static Future<bool?> show(BuildContext context, AdminWithdrawal withdrawal) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AdminFailPayoutDialog(withdrawal: withdrawal),
    );
  }

  @override
  ConsumerState<AdminFailPayoutDialog> createState() => _AdminFailPayoutDialogState();
}

class _AdminFailPayoutDialogState extends ConsumerState<AdminFailPayoutDialog> {
  final _formKey = GlobalKey<FormState>();
  final _reasonController = TextEditingController();
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      await ref.read(adminFinanceRepositoryProvider).failWithdrawal(
            withdrawalId: widget.withdrawal.id,
            failureReason: _reasonController.text.trim(),
          );
      ref.invalidate(adminWithdrawalsProvider);
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
            'Mark Payout as Failed',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Color(0xFFDC2626)),
          ),
          const SizedBox(height: 2),
          Text(
            'Request #${widget.withdrawal.id} • ₹${widget.withdrawal.amount.toStringAsFixed(2)}',
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

              // Reversal Notice
              Container(
                padding: const EdgeInsets.all(AppSpacing.sm),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFFBEB),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFFDE68A)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.info_outline_rounded, size: 16, color: Color(0xFFD97706)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Marking this withdrawal as failed will automatically reverse ₹${widget.withdrawal.amount.toStringAsFixed(2)} back into the technician\'s available wallet balance.',
                        style: const TextStyle(fontSize: 11.5, color: Color(0xFF92400E)),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // Failure Reason Input
              const Text(
                'Failure Reason *',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              TextFormField(
                controller: _reasonController,
                maxLines: 3,
                decoration: const InputDecoration(
                  hintText: 'e.g. Invalid bank account / IFSC, bank transfer rejected...',
                ),
                validator: (val) {
                  if (val == null || val.trim().length < 5) {
                    return 'Please enter a detailed failure reason (at least 5 chars).';
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
        FilledButton.icon(
          onPressed: _isSubmitting ? null : _submit,
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xFFDC2626),
          ),
          icon: _isSubmitting
              ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
              : const Icon(Icons.close_rounded, size: 16),
          label: const Text('Mark Failed & Reverse'),
        ),
      ],
    );
  }
}
