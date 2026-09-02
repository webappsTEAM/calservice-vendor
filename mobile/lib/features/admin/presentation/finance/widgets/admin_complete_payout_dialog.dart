import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/data/admin_finance_repository.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';

/// Modal dialog for administrator to complete a payout with bank UTR number.
class AdminCompletePayoutDialog extends ConsumerStatefulWidget {
  const AdminCompletePayoutDialog({
    super.key,
    required this.withdrawal,
  });

  final AdminWithdrawal withdrawal;

  static Future<bool?> show(BuildContext context, AdminWithdrawal withdrawal) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AdminCompletePayoutDialog(withdrawal: withdrawal),
    );
  }

  @override
  ConsumerState<AdminCompletePayoutDialog> createState() => _AdminCompletePayoutDialogState();
}

class _AdminCompletePayoutDialogState extends ConsumerState<AdminCompletePayoutDialog> {
  final _formKey = GlobalKey<FormState>();
  final _utrController = TextEditingController();
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _utrController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      await ref.read(adminFinanceRepositoryProvider).completeWithdrawal(
            withdrawalId: widget.withdrawal.id,
            bankTransactionId: _utrController.text.trim(),
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
            'Complete Payout Transfer',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 2),
          Text(
            'Payout Request #${widget.withdrawal.id} • ₹${widget.withdrawal.amount.toStringAsFixed(2)}',
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

              // Bank Details Card
              Container(
                padding: const EdgeInsets.all(AppSpacing.sm),
                decoration: BoxDecoration(
                  color: const Color(0xFFEFF6FF),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFDBEAFE)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.account_balance_rounded, size: 16, color: Color(0xFF1D4ED8)),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            widget.withdrawal.payoutAccountDisplay?.bankName ?? 'Direct Bank Transfer',
                            style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: Color(0xFF1E3A8A)),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Account: ${widget.withdrawal.payoutAccountDisplay?.maskedAccountDisplay ?? "••••"}  •  Payee: ${widget.withdrawal.payoutAccountDisplay?.accountHolderName ?? widget.withdrawal.employeeName}',
                      style: const TextStyle(fontSize: 11, color: Color(0xFF3B82F6)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // UTR / Transaction Reference Input
              const Text(
                'Bank Reference / UTR Number *',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              TextFormField(
                controller: _utrController,
                textCapitalization: TextCapitalization.characters,
                decoration: const InputDecoration(
                  hintText: 'e.g. UTR20260826001234',
                  prefixIcon: Icon(Icons.receipt_rounded, size: 18),
                ),
                validator: (val) {
                  if (val == null || val.trim().length < 4) {
                    return 'Please enter a valid bank UTR / reference ID.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                'This UTR number will be visible to the technician as proof of disbursement.',
                style: TextStyle(fontSize: 10.5, color: AppColors.textMuted),
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
            backgroundColor: const Color(0xFF059669),
          ),
          icon: _isSubmitting
              ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
              : const Icon(Icons.check_circle_rounded, size: 16),
          label: const Text('Mark Completed'),
        ),
      ],
    );
  }
}
