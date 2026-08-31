import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/data/admin_finance_repository.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';

/// Modal bottom sheet for an administrator to add a bank payout account.
///
/// Security: The full account number is write-only over TLS.
/// Only the masked last 4 digits are ever stored, returned, or displayed.
class AdminAddBankAccountSheet extends ConsumerStatefulWidget {
  const AdminAddBankAccountSheet({super.key});

  static Future<bool?> show(BuildContext context) {
    return showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => const AdminAddBankAccountSheet(),
    );
  }

  @override
  ConsumerState<AdminAddBankAccountSheet> createState() => _AdminAddBankAccountSheetState();
}

class _AdminAddBankAccountSheetState extends ConsumerState<AdminAddBankAccountSheet> {
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
      await ref.read(adminFinanceRepositoryProvider).addPayoutAccount(
            accountHolderName: _holderNameController.text.trim(),
            bankName: _bankNameController.text.trim().isNotEmpty
                ? _bankNameController.text.trim()
                : 'Direct Bank Transfer',
            accountNumber: _accountNumberController.text.trim(),
            ifscCode: _ifscController.text.trim().toUpperCase(),
            accountType: _accountType,
            isPrimary: true,
          );

      ref.invalidate(adminBankAccountsProvider);

      if (mounted) {
        Navigator.of(context).pop(true);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Bank account added successfully.'),
            backgroundColor: Color(0xFF059669),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _serverError = e.toString().replaceAll('Exception:', '').trim();
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(AppRadius.sheet)),
      ),
      padding: EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.md,
        AppSpacing.lg,
        bottomInset + AppSpacing.xl,
      ),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // ── Handle Bar ─────────────────────────────────────────
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

                // ── Title Row with Bank Icon ───────────────────────────
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(7),
                          decoration: BoxDecoration(
                            color: const Color(0xFF004E89).withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Icon(
                            Icons.account_balance_rounded,
                            size: 20,
                            color: Color(0xFF004E89),
                          ),
                        ),
                        const SizedBox(width: AppSpacing.sm),
                        Text(
                          'Add Bank Account',
                          style: TextStyle(
                            fontSize: 16.5,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary,
                          ),
                        ),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 20),
                      onPressed: () => Navigator.of(context).pop(),
                      visualDensity: VisualDensity.compact,
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),

                // ── Subtle Security Card ───────────────────────────────
                Container(
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEFF6FF),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFBFDBFE)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.shield_outlined, size: 16, color: Color(0xFF1D4ED8)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text(
                              'Security',
                              style: TextStyle(
                                fontSize: 11.5,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF1E3A8A),
                              ),
                            ),
                            SizedBox(height: 1),
                            Text(
                              'Only the last 4 digits of your account number are stored. The full number is never retained.',
                              style: TextStyle(
                                fontSize: 11,
                                color: Color(0xFF1E40AF),
                                height: 1.3,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.md),

                // Error Banner
                if (_serverError != null) ...[
                  Container(
                    padding: const EdgeInsets.all(AppSpacing.sm),
                    margin: const EdgeInsets.only(bottom: AppSpacing.md),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFF1F2),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFFFECDD3)),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.error_outline_rounded, size: 16, color: Color(0xFFE11D48)),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            _serverError!,
                            style: const TextStyle(fontSize: 12, color: Color(0xFF9F1239)),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                // ── Field 1: Account Holder Name * ─────────────────────
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
                    hintText: 'Enter account holder name',
                  ),
                  validator: (val) {
                    if (val == null || val.trim().isEmpty) {
                      return 'Account holder name is required.';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: AppSpacing.md),

                // ── Field 2: Bank Name ─────────────────────────────────
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
                    hintText: 'Enter bank name',
                  ),
                ),
                const SizedBox(height: AppSpacing.md),

                // ── Field 3: Account Number * (Write-only) ─────────────
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
                    hintText: 'Enter account number',
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
                const SizedBox(height: AppSpacing.md),

                // ── Field 4: IFSC Code ─────────────────────────────────
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
                    hintText: 'Enter IFSC code',
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

                // ── Field 5: Account Type Selector ─────────────────────
                Text(
                  'Account Type',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Expanded(
                      child: ChoiceChip(
                        label: const Center(child: Text('Savings')),
                        selected: _accountType == 'SAVINGS',
                        selectedColor: const Color(0xFF004E89),
                        labelStyle: TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w800,
                          color: _accountType == 'SAVINGS' ? Colors.white : const Color(0xFF475569),
                        ),
                        onSelected: (selected) {
                          if (selected) setState(() => _accountType = 'SAVINGS');
                        },
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: ChoiceChip(
                        label: const Center(child: Text('Current')),
                        selected: _accountType == 'CURRENT',
                        selectedColor: const Color(0xFF004E89),
                        labelStyle: TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w800,
                          color: _accountType == 'CURRENT' ? Colors.white : const Color(0xFF475569),
                        ),
                        onSelected: (selected) {
                          if (selected) setState(() => _accountType = 'CURRENT');
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.lg),

                // ── Bottom Actions: [ Cancel ] [ Add Account ] ─────────
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _isSubmitting ? null : () => Navigator.of(context).pop(),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          minimumSize: const Size(0, 44),
                        ),
                        child: const Text('Cancel', style: TextStyle(fontWeight: FontWeight.w700)),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.md),
                    Expanded(
                      flex: 2,
                      child: FilledButton.icon(
                        onPressed: _isSubmitting ? null : _submit,
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFF004E89), // Peacock Blue branding
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          minimumSize: const Size(0, 44),
                        ),
                        icon: _isSubmitting
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.add_rounded, size: 18),
                        label: const Text(
                          'Add Account',
                          style: TextStyle(fontWeight: FontWeight.w800),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
