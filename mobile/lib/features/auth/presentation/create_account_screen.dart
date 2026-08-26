import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/api_error.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/app_typography.dart';
import '../../../routing/app_routes.dart';
import 'auth_controller.dart';

/// The native Flutter Create Account / Registration screen for Workforce technicians.
class CreateAccountScreen extends ConsumerStatefulWidget {
  const CreateAccountScreen({super.key});

  @override
  ConsumerState<CreateAccountScreen> createState() => _CreateAccountScreenState();
}

class _CreateAccountScreenState extends ConsumerState<CreateAccountScreen> {
  final _formKey = GlobalKey<FormState>();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _mobileController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _mobileController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _errorMessage = null);

    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    final firstName = _firstNameController.text.trim();
    final lastName = _lastNameController.text.trim();
    final mobileNumber = _mobileController.text.trim();
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    final confirmPassword = _confirmPasswordController.text;

    if (password != confirmPassword) {
      setState(() => _errorMessage = 'Passwords do not match.');
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      await ref.read(authControllerProvider.notifier).signup(
            firstName: firstName,
            lastName: lastName.isNotEmpty ? lastName : null,
            mobileNumber: mobileNumber,
            email: email,
            password: password,
          );
      // Upon successful signup, GoRouter redirect automatically checks
      // user.registrationStatus ('not_started') and routes to RegistrationIncompleteScreen.
    } on DioException catch (e) {
      debugPrint('[WORKFORCE SIGNUP ERROR] ${e.response?.statusCode}: ${e.response?.data}');
      if (mounted) {
        setState(
          () => _errorMessage = describeDioError(
            e,
            fallback: 'Unable to create workforce account. Please check details and retry.',
          ),
        );
      }
    } catch (e) {
      debugPrint('[WORKFORCE SIGNUP UNEXPECTED ERROR] $e');
      if (mounted) {
        setState(
          () => _errorMessage =
              'Unable to create workforce account. Please check details and retry.',
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  void _showInfoSheet(BuildContext context, String title, String content) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.sheet)),
      ),
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.55,
        minChildSize: 0.35,
        maxChildSize: 0.85,
        expand: false,
        builder: (ctx, scrollController) => Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.md,
            AppSpacing.lg,
            AppSpacing.xl,
          ),
          child: ListView(
            controller: scrollController,
            children: [
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
              Text(
                title,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              Divider(color: AppColors.border),
              const SizedBox(height: AppSpacing.sm),
              Text(
                content,
                style: TextStyle(
                  fontSize: 13,
                  height: 1.5,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  style: OutlinedButton.styleFrom(
                    side: BorderSide(color: AppColors.border),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.button),
                    ),
                  ),
                  child: const Text('Close'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final brandGreen = AppColors.success.base;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.xl,
              vertical: AppSpacing.lg,
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // ── Brand Header ─────────────────────────────────────────
                    Center(
                      child: Container(
                        width: 64,
                        height: 64,
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF004E89).withValues(alpha: 0.18),
                              blurRadius: 16,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Image.asset(
                          'assets/images/sevo_logo.png',
                          fit: BoxFit.contain,
                          errorBuilder: (context, error, stackTrace) => Container(
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                colors: [Color(0xFF004E89), Color(0xFF059669)],
                              ),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: const Icon(
                              Icons.handyman_rounded,
                              color: Colors.white,
                              size: 28,
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    const Text(
                      'SEVO VENDOR',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.5,
                        color: Color(0xFF0A2540),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Center(
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 2.5,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFF059669).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(AppRadius.chip),
                          border: Border.all(
                            color: const Color(0xFF059669).withValues(alpha: 0.3),
                          ),
                        ),
                        child: const Text(
                          'WORKFORCE',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.8,
                            color: Color(0xFF065F46),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.lg),

                    // ── Heading ──────────────────────────────────────────────
                    Text(
                      'Join the Workforce Platform',
                      textAlign: TextAlign.center,
                      style: AppTypography.displayTitle.copyWith(fontSize: 22),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Create your technician account to start onboarding',
                      textAlign: TextAlign.center,
                      style: AppTypography.supporting,
                    ),
                    const SizedBox(height: AppSpacing.lg),

                    // ── Error Banner ─────────────────────────────────────────
                    if (_errorMessage != null) ...[
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(AppSpacing.md),
                        decoration: BoxDecoration(
                          color: AppColors.error.tint,
                          border: Border.all(color: AppColors.error.tintBorder),
                          borderRadius: BorderRadius.circular(AppRadius.input),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              Icons.error_outline_rounded,
                              size: 18,
                              color: AppColors.error.base,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _errorMessage!,
                                style: TextStyle(
                                  color: AppColors.error.onTint,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                            GestureDetector(
                              onTap: () => setState(() => _errorMessage = null),
                              child: Icon(
                                Icons.close_rounded,
                                size: 16,
                                color: AppColors.error.base,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: AppSpacing.md),
                    ],

                    // ── Name Fields Row ──────────────────────────────────────
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _FieldLabel(label: 'First Name', isRequired: true),
                              const SizedBox(height: 6),
                              TextFormField(
                                controller: _firstNameController,
                                autocorrect: false,
                                enabled: !_isSubmitting,
                                textInputAction: TextInputAction.next,
                                validator: (value) {
                                  if (value == null || value.trim().isEmpty) {
                                    return 'First name required';
                                  }
                                  return null;
                                },
                                decoration: _inputDecoration(
                                  hintText: 'Ramesh',
                                  prefixIcon: Icons.person_outline,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: AppSpacing.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _FieldLabel(label: 'Last Name', isRequired: false),
                              const SizedBox(height: 6),
                              TextFormField(
                                controller: _lastNameController,
                                autocorrect: false,
                                enabled: !_isSubmitting,
                                textInputAction: TextInputAction.next,
                                decoration: _inputDecoration(
                                  hintText: 'Kumar',
                                  prefixIcon: Icons.person_outline,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),

                    // ── Mobile Number ────────────────────────────────────────
                    _FieldLabel(label: 'Mobile Number', isRequired: true),
                    const SizedBox(height: 6),
                    TextFormField(
                      controller: _mobileController,
                      keyboardType: TextInputType.phone,
                      autocorrect: false,
                      enabled: !_isSubmitting,
                      textInputAction: TextInputAction.next,
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Mobile number required';
                        }
                        final cleaned = value.replaceAll(RegExp(r'[\s-]'), '');
                        if (cleaned.length < 8) {
                          return 'Enter a valid mobile number';
                        }
                        return null;
                      },
                      decoration: _inputDecoration(
                        hintText: '9876543210',
                        prefixIcon: Icons.phone_android_outlined,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),

                    // ── Email Address ────────────────────────────────────────
                    _FieldLabel(label: 'Email Address', isRequired: true),
                    const SizedBox(height: 6),
                    TextFormField(
                      controller: _emailController,
                      keyboardType: TextInputType.emailAddress,
                      autocorrect: false,
                      enabled: !_isSubmitting,
                      textInputAction: TextInputAction.next,
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Email address required';
                        }
                        if (!value.contains('@') || !value.contains('.')) {
                          return 'Enter a valid email address';
                        }
                        return null;
                      },
                      decoration: _inputDecoration(
                        hintText: 'ramesh.tech@example.com',
                        prefixIcon: Icons.mail_outline,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),

                    // ── Password ─────────────────────────────────────────────
                    _FieldLabel(label: 'Password', isRequired: true),
                    const SizedBox(height: 6),
                    TextFormField(
                      controller: _passwordController,
                      obscureText: _obscurePassword,
                      enabled: !_isSubmitting,
                      textInputAction: TextInputAction.next,
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Password required';
                        }
                        if (value.length < 6) {
                          return 'Password must be at least 6 characters';
                        }
                        return null;
                      },
                      decoration: _inputDecoration(
                        hintText: 'Minimum 6 characters',
                        prefixIcon: Icons.lock_outline,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscurePassword
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                            color: AppColors.textMuted,
                          ),
                          onPressed: () => setState(
                            () => _obscurePassword = !_obscurePassword,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),

                    // ── Confirm Password ─────────────────────────────────────
                    _FieldLabel(label: 'Confirm Password', isRequired: true),
                    const SizedBox(height: 6),
                    TextFormField(
                      controller: _confirmPasswordController,
                      obscureText: _obscureConfirmPassword,
                      enabled: !_isSubmitting,
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _submit(),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Please confirm password';
                        }
                        if (value != _passwordController.text) {
                          return 'Passwords do not match';
                        }
                        return null;
                      },
                      decoration: _inputDecoration(
                        hintText: 'Re-enter your password',
                        prefixIcon: Icons.lock_outline,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscureConfirmPassword
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                            color: AppColors.textMuted,
                          ),
                          onPressed: () => setState(
                            () => _obscureConfirmPassword =
                                !_obscureConfirmPassword,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xl),

                    // ── Primary CTA Button ───────────────────────────────────
                    Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: _isSubmitting
                              ? [
                                  AppColors.primary.withValues(alpha: 0.6),
                                  brandGreen.withValues(alpha: 0.6),
                                ]
                              : [AppColors.primary, brandGreen],
                        ),
                        borderRadius: BorderRadius.circular(AppRadius.button),
                        boxShadow: _isSubmitting
                            ? const []
                            : [
                                BoxShadow(
                                  color: AppColors.primary.withValues(alpha: 0.25),
                                  blurRadius: 12,
                                  offset: const Offset(0, 4),
                                ),
                              ],
                      ),
                      child: ElevatedButton(
                        onPressed: _isSubmitting ? null : _submit,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.transparent,
                          disabledBackgroundColor: Colors.transparent,
                          foregroundColor: Colors.white,
                          disabledForegroundColor: Colors.white,
                          shadowColor: Colors.transparent,
                          elevation: 0,
                          minimumSize: const Size.fromHeight(52),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(AppRadius.button),
                          ),
                        ),
                        child: _isSubmitting
                            ? const SizedBox(
                                height: 18,
                                width: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Text(
                                'Create Account & Start Onboarding',
                                style: TextStyle(
                                  fontSize: 14.5,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.lg),

                    // ── Sign In Navigation Link ──────────────────────────────
                    Center(
                      child: Wrap(
                        alignment: WrapAlignment.center,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            'Already have an account? ',
                            style: TextStyle(
                              fontSize: 13,
                              color: AppColors.textSecondary,
                            ),
                          ),
                          GestureDetector(
                            onTap: () {
                              if (context.canPop()) {
                                context.pop();
                              } else {
                                context.go(AppRoutes.login);
                              }
                            },
                            child: Text(
                              'Sign In',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w800,
                                color: AppColors.primary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xl),

                    // ── Informational / Legal Links ──────────────────────────
                    Wrap(
                      alignment: WrapAlignment.center,
                      spacing: 8,
                      runSpacing: 4,
                      children: [
                        _LegalLink(
                          label: 'Privacy Policy',
                          onTap: () => _showInfoSheet(
                            context,
                            'Privacy Policy',
                            'SEVO Workforce respects technician privacy. Operational location telemetry, documents, and identity information are securely stored and utilized strictly for job assignment, verification, and dispatch compliance.',
                          ),
                        ),
                        const Text('•', style: TextStyle(color: Colors.grey, fontSize: 11)),
                        _LegalLink(
                          label: 'Terms of Service',
                          onTap: () => _showInfoSheet(
                            context,
                            'Terms of Service',
                            'Technicians operating on the SEVO platform agree to follow safety protocols, quality checklists, and vendor dispatch guidelines. All work is subject to customer verification and platform approval.',
                          ),
                        ),
                        const Text('•', style: TextStyle(color: Colors.grey, fontSize: 11)),
                        _LegalLink(
                          label: 'Support & Contact',
                          onTap: () => _showInfoSheet(
                            context,
                            'Support & Contact',
                            'For operational, payroll, or document verification assistance, contact SEVO Workforce Operations Desk via email at support@calservices.com.',
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Center(
                      child: Text(
                        '© 2026 CALDIM ENGINEERING PRIVATE LIMITED. All rights reserved.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 10.5,
                          color: AppColors.textMuted,
                          height: 1.3,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  InputDecoration _inputDecoration({
    required String hintText,
    required IconData prefixIcon,
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      prefixIcon: Icon(prefixIcon, color: AppColors.textMuted, size: 18),
      suffixIcon: suffixIcon,
      hintText: hintText,
      hintStyle: TextStyle(color: AppColors.textMuted.withValues(alpha: 0.7), fontSize: 13),
      filled: true,
      fillColor: AppColors.surface,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: 14,
        vertical: 14,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.input),
        borderSide: BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.input),
        borderSide: BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.input),
        borderSide: BorderSide(color: AppColors.primary, width: 1.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.input),
        borderSide: BorderSide(color: AppColors.error.base),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.input),
        borderSide: BorderSide(color: AppColors.error.base, width: 1.5),
      ),
    );
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel({required this.label, required this.isRequired});

  final String label;
  final bool isRequired;

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(
        text: label,
        style: TextStyle(
          fontSize: 12.5,
          fontWeight: FontWeight.w700,
          color: AppColors.textPrimary,
        ),
        children: [
          if (isRequired)
            const TextSpan(
              text: ' *',
              style: TextStyle(
                color: Color(0xFFE11D48),
                fontWeight: FontWeight.w700,
              ),
            ),
        ],
      ),
    );
  }
}

class _LegalLink extends StatelessWidget {
  const _LegalLink({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: AppColors.textSecondary,
          decoration: TextDecoration.underline,
        ),
      ),
    );
  }
}
