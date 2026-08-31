import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_error.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/loading_button.dart';
import '../../data/finance_repository.dart';
import '../finance_providers.dart';

/// Modal bottom sheet for adding a new bank payout account.
///
/// Security: Account number is write-only transmitted over TLS to backend;
/// never stored locally or printed in logs.
class AddBankAccountSheet extends ConsumerStatefulWidget {
  const AddBankAccountSheet({super.key});

  static Future<bool?> show(BuildContext context) {
    return showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => const AddBankAccountSheet(),
    );
  }

  @override
  ConsumerState<AddBankAccountSheet> createState() => _AddBankAccountSheetState();
}

class _AddBankAccountSheetState extends ConsumerState<AddBankAccountSheet> {
  final _formKey = GlobalKey<FormState>();

  late final TextEditingController _holderNameController;
  late final TextEditingController _bankNameController;
  late final TextEditingController _accountNumberController;
  late final TextEditingController _ifscController;

  String _accountType = 'SAVINGS';
  bool _obscureAccountNumber = true;
  bool _isSubmitting = false;
  String? _serverError;

  @override
  void initState() {
    super.initState();
    _holderNameController = TextEditingController();
    _bankNameController = TextEditingController();
    _accountNumberController = TextEditingController();
    _ifscController = TextEditingController();
  }

  @override
  void dispose() {
    _holderNameController.dispose();
    _bankNameController.dispose();
    _accountNumberController.dispose();
    _ifscController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_isSubmitting) return;
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isSubmitting = true;
      _serverError = null;
    });

    try {
      await ref.read(financeRepositoryProvider).addPayoutAccount(
        accountHolderName: _holderNameController.text.trim(),
        bankName: _bankNameController.text.trim(),
        accountNumber: _accountNumberController.text.trim(),
        ifscCode: _ifscController.text.trim().toUpperCase(),
        accountType: _accountType,
        isPrimary: true,
      );

      ref.invalidate(payoutAccountsProvider);
      ref.invalidate(withdrawalEligibilityProvider);

      if (mounted) {
        Navigator.of(context).pop(true);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Bank account added successfully.'),
            backgroundColor: Color(0xFF059669),
          ),
        );
      }
    } on DioException catch (e) {
      if (mounted) {
        setState(() {
          _serverError = describeDioError(e, fallback: 'Failed to add bank account.');
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _serverError = e.toString();
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(AppRadius.sheet)),
      ),
      padding: EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.md,
        AppSpacing.lg,
        MediaQuery.of(context).viewInsets.bottom + AppSpacing.xl,
      ),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Handle bar
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: AppSpacing.md),
                  decoration: BoxDecoration(
                    color: AppColors.border,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // Title Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF004E89).withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(
                          Icons.add_card_rounded,
                          size: 20,
                          color: Color(0xFF004E89),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      Text(
                        'Link Bank Account',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 20),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),

              // Security notice
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: const Color(0xFFEFF6FF),
                  borderRadius: BorderRadius.circular(AppRadius.card),
                  border: Border.all(color: const Color(0xFFBFDBFE)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.lock_outline_rounded, size: 18, color: Color(0xFF1D4ED8)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Your banking details are encrypted. Only the masked last 4 digits will ever be displayed.',
                        style: TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                          color: const Color(0xFF1E40AF),
                          height: 1.35,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              if (_serverError != null) ...[
                Container(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  margin: const EdgeInsets.only(bottom: AppSpacing.md),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF1F2),
                    borderRadius: BorderRadius.circular(AppRadius.chip),
                    border: Border.all(color: const Color(0xFFFECDD3)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.error_outline_rounded, size: 18, color: Color(0xFFE11D48)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _serverError!,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF9F1239),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              // 1. Account Holder Name
              Text(
                'Account Holder Name *',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 4),
              TextFormField(
                controller: _holderNameController,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(
                  hintText: 'e.g. Ramesh Kumar',
                ),
                validator: (val) {
                  if (val == null || val.trim().isEmpty) {
                    return 'Account holder name is required.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.md),

              // 2. Bank Name
              Text(
                'Bank Name',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 4),
              TextFormField(
                controller: _bankNameController,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(
                  hintText: 'e.g. State Bank of India, HDFC Bank',
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // 3. Account Number
              Text(
                'Account Number *',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 4),
              TextFormField(
                controller: _accountNumberController,
                keyboardType: TextInputType.number,
                obscureText: _obscureAccountNumber,
                style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700),
                decoration: InputDecoration(
                  hintText: 'Enter full account number',
                  suffixIcon: IconButton(
                    icon: Icon(
                      _obscureAccountNumber
                          ? Icons.visibility_outlined
                          : Icons.visibility_off_outlined,
                      size: 20,
                    ),
                    onPressed: () =>
                        setState(() => _obscureAccountNumber = !_obscureAccountNumber),
                  ),
                ),
                validator: (val) {
                  if (val == null || val.trim().isEmpty) {
                    return 'Account number is required.';
                  }
                  if (val.trim().length < 4) {
                    return 'Account number must be at least 4 digits.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 4),
              Text(
                'Securely masked; only last 4 digits are retained for display.',
                style: TextStyle(
                  fontSize: 11,
                  color: AppColors.textMuted,
                  height: 1.3,
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // 4. IFSC Code
              Text(
                'IFSC Code',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 4),
              TextFormField(
                controller: _ifscController,
                textCapitalization: TextCapitalization.characters,
                style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700),
                decoration: const InputDecoration(
                  hintText: 'e.g. SBIN0001234',
                ),
                validator: (val) {
                  if (val != null && val.trim().isNotEmpty) {
                    final clean = val.trim().toUpperCase();
                    if (clean.length != 11) {
                      return 'IFSC code must be exactly 11 characters.';
                    }
                  }
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.md),

              // 5. Account Type Selector
              Text(
                'Account Type',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 6),
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(
                    value: 'SAVINGS',
                    label: Text('Savings'),
                    icon: Icon(Icons.savings_outlined, size: 16),
                  ),
                  ButtonSegment(
                    value: 'CURRENT',
                    label: Text('Current'),
                    icon: Icon(Icons.business_outlined, size: 16),
                  ),
                ],
                selected: {_accountType},
                onSelectionChanged: (set) {
                  setState(() => _accountType = set.first);
                },
              ),
              const SizedBox(height: AppSpacing.lg),

              // Action buttons
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _isSubmitting ? null : () => Navigator.of(context).pop(),
                      child: const Text('Cancel'),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    flex: 2,
                    child: LoadingButton(
                      label: 'SAVE ACCOUNT',
                      icon: Icons.check_circle_outline_rounded,
                      isLoading: _isSubmitting,
                      onPressed: _submit,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF004E89),
                        foregroundColor: Colors.white,
                        minimumSize: const Size.fromHeight(48),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
