import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/api_error.dart';
import '../../../core/theme/app_theme.dart';
import '../../../routing/app_routes.dart';
import 'auth_controller.dart';

/// The native Flutter Create Account / Registration screen for Workforce technicians.
///
/// Features:
/// - Clean, modern, executive Sevo-inspired aesthetic
/// - Subtle light ambient gradient canvas with soft decorative accents
/// - Compact top branding section with SEVO VENDOR logo and WORKFORCE badge
/// - Clean elevated surface card with modern rounded corners, soft shadow, and border
/// - Clear section organization (PERSONAL DETAILS, CONTACT DETAILS, SECURITY CREDENTIALS)
/// - Polished form fields with responsive keyboard handling and zero RenderFlex overflow
/// - 100% preservation of all existing controllers, validation, and submission logic
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
    return Scaffold(
      backgroundColor: const Color(0xFF062B4F), // Deep Peacock Navy baseline
      body: Stack(
        children: [
          // ── 1. Rich Peacock-Inspired Gradient Canvas ───────────────────────
          // Top: Deep royal / peacock navy
          // Middle: Rich blue transitioning into vibrant peacock teal
          // Lower: Subtle emerald green grounding accents
          Positioned.fill(
            child: Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Color(0xFF062B4F), // Deep Peacock Navy
                    Color(0xFF004E89), // Deep Peacock Blue
                    Color(0xFF005B96), // Royal Peacock Blue
                    Color(0xFF007A99), // Ocean Teal-Blue
                    Color(0xFF008C95), // Peacock Teal
                    Color(0xFF065F46), // Deep Emerald Accent
                    Color(0xFF0B9F6E), // Emerald Green Base
                  ],
                  stops: [0.0, 0.16, 0.32, 0.52, 0.70, 0.88, 1.0],
                ),
              ),
            ),
          ),

          // ── 2. Subtle Decorative Ambient Depth Orbs (High-End & Non-Intrusive)
          // Top-right soft teal radial glow
          Positioned(
            top: -50,
            right: -30,
            child: Container(
              width: 250,
              height: 250,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    const Color(0xFF008C95).withValues(alpha: 0.22),
                    const Color(0xFF008C95).withValues(alpha: 0.0),
                  ],
                ),
              ),
            ),
          ),
          // Mid-left soft emerald radial glow
          Positioned(
            top: 260,
            left: -60,
            child: Container(
              width: 260,
              height: 260,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    const Color(0xFF0B9F6E).withValues(alpha: 0.18),
                    const Color(0xFF0B9F6E).withValues(alpha: 0.0),
                  ],
                ),
              ),
            ),
          ),
          // Bottom-right royal blue radial glow
          Positioned(
            bottom: -40,
            right: -40,
            child: Container(
              width: 240,
              height: 240,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    const Color(0xFF0A66C2).withValues(alpha: 0.20),
                    const Color(0xFF0A66C2).withValues(alpha: 0.0),
                  ],
                ),
              ),
            ),
          ),

          // Subtle elegant low-opacity curved accent shape behind form
          Positioned(
            top: 100,
            left: -30,
            child: Transform.rotate(
              angle: -0.3,
              child: Container(
                width: 180,
                height: 38,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(999),
                  gradient: LinearGradient(
                    colors: [
                      const Color(0xFF008C95).withValues(alpha: 0.12),
                      const Color(0xFF0B9F6E).withValues(alpha: 0.0),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // ── 4. Main Scrollable Content Area ───────────────────────────────
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                padding: const EdgeInsets.symmetric(
                  horizontal: 18,
                  vertical: 16,
                ),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 460),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // ── Top Branding & Header Area (Sitting on Peacock BG)
                        Center(
                          child: Container(
                            width: 64,
                            height: 64,
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(18),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.25),
                                  blurRadius: 18,
                                  offset: const Offset(0, 6),
                                ),
                                BoxShadow(
                                  color: const Color(0xFF0B9F6E).withValues(alpha: 0.30),
                                  blurRadius: 12,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Image.asset(
                              'assets/images/sevo_logo.png',
                              fit: BoxFit.contain,
                              errorBuilder: (context, error, stackTrace) => Container(
                                decoration: BoxDecoration(
                                  gradient: const LinearGradient(
                                    colors: [Color(0xFF005B96), Color(0xFF0B9F6E)],
                                  ),
                                  borderRadius: BorderRadius.circular(12),
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
                        const SizedBox(height: 12),
                        const Text(
                          'SEVO VENDOR',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 1.8,
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 5),
                        Center(
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 3,
                            ),
                            decoration: BoxDecoration(
                              color: const Color(0xFF0B9F6E).withValues(alpha: 0.25),
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(
                                color: const Color(0xFF34D399).withValues(alpha: 0.55),
                                width: 1,
                              ),
                            ),
                            child: const Text(
                              'WORKFORCE',
                              style: TextStyle(
                                fontSize: 10.5,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 1.2,
                                color: Color(0xFF6EE7B7),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 14),

                        // ── Page Title & Context (Crisp High-Contrast White) ─
                        const Text(
                          'Create Technician',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 23,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.4,
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Create your account and start your workforce journey.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w400,
                            color: Colors.white.withValues(alpha: 0.88),
                          ),
                        ),
                        const SizedBox(height: 20),

                        // ── Error Banner ─────────────────────────────────────
                        if (_errorMessage != null) ...[
                          Container(
                            width: double.infinity,
                            margin: const EdgeInsets.only(bottom: 16),
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFFF1F2),
                              border: Border.all(color: const Color(0xFFFECDD3)),
                              borderRadius: BorderRadius.circular(12),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.1),
                                  blurRadius: 10,
                                  offset: const Offset(0, 4),
                                ),
                              ],
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(
                                  Icons.error_outline_rounded,
                                  size: 18,
                                  color: Color(0xFFE11D48),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    _errorMessage!,
                                    style: const TextStyle(
                                      color: Color(0xFF9F1239),
                                      fontSize: 13,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ),
                                GestureDetector(
                                  onTap: () => setState(() => _errorMessage = null),
                                  child: const Icon(
                                    Icons.close_rounded,
                                    size: 16,
                                    color: Color(0xFFE11D48),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],

                        // ── 5. Premium Floating Elevated Form Card ───────────
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 20,
                            vertical: 22,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(22),
                            border: Border.all(
                              color: const Color(0xFFE2E8F0),
                              width: 1,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.18),
                                blurRadius: 32,
                                offset: const Offset(0, 12),
                              ),
                              BoxShadow(
                                color: const Color(0xFF005B96).withValues(alpha: 0.12),
                                blurRadius: 14,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              // ── Section 1: Personal Details ────────────────
                              _buildSectionHeader(
                                icon: Icons.badge_outlined,
                                label: 'PERSONAL DETAILS',
                                color: const Color(0xFF005B96),
                                bgColor: const Color(0xFFEFF6FF),
                              ),
                              const SizedBox(height: 12),

                              // Name Fields Row
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const _FieldLabel(label: 'First Name', isRequired: true),
                                        const SizedBox(height: 6),
                                        TextFormField(
                                          controller: _firstNameController,
                                          autocorrect: false,
                                          enabled: !_isSubmitting,
                                          textInputAction: TextInputAction.next,
                                          style: const TextStyle(
                                            fontSize: 14,
                                            fontWeight: FontWeight.w500,
                                            color: Color(0xFF0F172A),
                                          ),
                                          validator: (value) {
                                            if (value == null || value.trim().isEmpty) {
                                              return 'First name required';
                                            }
                                            return null;
                                          },
                                          decoration: _inputDecoration(
                                            hintText: 'Ramesh',
                                            prefixIcon: Icons.person_outline_rounded,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const _FieldLabel(label: 'Last Name', isRequired: false),
                                        const SizedBox(height: 6),
                                        TextFormField(
                                          controller: _lastNameController,
                                          autocorrect: false,
                                          enabled: !_isSubmitting,
                                          textInputAction: TextInputAction.next,
                                          style: const TextStyle(
                                            fontSize: 14,
                                            fontWeight: FontWeight.w500,
                                            color: Color(0xFF0F172A),
                                          ),
                                          decoration: _inputDecoration(
                                            hintText: 'Kumar',
                                            prefixIcon: Icons.person_outline_rounded,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),

                              const Padding(
                                padding: EdgeInsets.symmetric(vertical: 18),
                                child: Divider(color: Color(0xFFF1F5F9), thickness: 1),
                              ),

                              // ── Section 2: Contact Details ─────────────────
                              _buildSectionHeader(
                                icon: Icons.contact_phone_outlined,
                                label: 'CONTACT DETAILS',
                                color: const Color(0xFF008C95),
                                bgColor: const Color(0xFFECFEFF),
                              ),
                              const SizedBox(height: 12),

                              // Mobile Number
                              const _FieldLabel(label: 'Mobile Number', isRequired: true),
                              const SizedBox(height: 6),
                              TextFormField(
                                controller: _mobileController,
                                keyboardType: TextInputType.phone,
                                autocorrect: false,
                                enabled: !_isSubmitting,
                                textInputAction: TextInputAction.next,
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w500,
                                  color: Color(0xFF0F172A),
                                ),
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
                                  prefixIcon: Icons.phone_android_rounded,
                                ),
                              ),
                              const SizedBox(height: 14),

                              // Email Address
                              const _FieldLabel(label: 'Email Address', isRequired: true),
                              const SizedBox(height: 6),
                              TextFormField(
                                controller: _emailController,
                                keyboardType: TextInputType.emailAddress,
                                autocorrect: false,
                                enabled: !_isSubmitting,
                                textInputAction: TextInputAction.next,
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w500,
                                  color: Color(0xFF0F172A),
                                ),
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
                                  prefixIcon: Icons.mail_outline_rounded,
                                ),
                              ),

                              const Padding(
                                padding: EdgeInsets.symmetric(vertical: 18),
                                child: Divider(color: Color(0xFFF1F5F9), thickness: 1),
                              ),

                              // ── Section 3: Security & Credentials ──────────
                              _buildSectionHeader(
                                icon: Icons.shield_outlined,
                                label: 'SECURITY CREDENTIALS',
                                color: const Color(0xFF0B9F6E),
                                bgColor: const Color(0xFFECFDF5),
                              ),
                              const SizedBox(height: 12),

                              // Password
                              const _FieldLabel(label: 'Password', isRequired: true),
                              const SizedBox(height: 6),
                              TextFormField(
                                controller: _passwordController,
                                obscureText: _obscurePassword,
                                enabled: !_isSubmitting,
                                textInputAction: TextInputAction.next,
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w500,
                                  color: Color(0xFF0F172A),
                                ),
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
                                  prefixIcon: Icons.lock_outline_rounded,
                                  suffixIcon: IconButton(
                                    icon: Icon(
                                      _obscurePassword
                                          ? Icons.visibility_outlined
                                          : Icons.visibility_off_outlined,
                                      color: const Color(0xFF94A3B8),
                                      size: 20,
                                    ),
                                    onPressed: () => setState(
                                      () => _obscurePassword = !_obscurePassword,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 14),

                              // Confirm Password
                              const _FieldLabel(label: 'Confirm Password', isRequired: true),
                              const SizedBox(height: 6),
                              TextFormField(
                                controller: _confirmPasswordController,
                                obscureText: _obscureConfirmPassword,
                                enabled: !_isSubmitting,
                                textInputAction: TextInputAction.done,
                                onFieldSubmitted: (_) => _submit(),
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w500,
                                  color: Color(0xFF0F172A),
                                ),
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
                                  prefixIcon: Icons.lock_outline_rounded,
                                  suffixIcon: IconButton(
                                    icon: Icon(
                                      _obscureConfirmPassword
                                          ? Icons.visibility_outlined
                                          : Icons.visibility_off_outlined,
                                      color: const Color(0xFF94A3B8),
                                      size: 20,
                                    ),
                                    onPressed: () => setState(
                                      () => _obscureConfirmPassword =
                                          !_obscureConfirmPassword,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 22),

                              // ── Primary Create Technician CTA Button ───────
                              // Peacock Blue -> Teal -> Emerald Green Gradient
                              Container(
                                height: 50,
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    colors: _isSubmitting
                                        ? [
                                            const Color(0xFF005B96).withValues(alpha: 0.6),
                                            const Color(0xFF008C95).withValues(alpha: 0.6),
                                            const Color(0xFF0B9F6E).withValues(alpha: 0.6),
                                          ]
                                        : const [
                                            Color(0xFF005B96), // Peacock Blue
                                            Color(0xFF008C95), // Teal Accent
                                            Color(0xFF0B9F6E), // Emerald Green
                                          ],
                                  ),
                                  borderRadius: BorderRadius.circular(14),
                                  boxShadow: _isSubmitting
                                      ? const []
                                      : [
                                          BoxShadow(
                                            color: const Color(0xFF0B9F6E).withValues(alpha: 0.35),
                                            blurRadius: 14,
                                            offset: const Offset(0, 4),
                                          ),
                                          BoxShadow(
                                            color: const Color(0xFF005B96).withValues(alpha: 0.25),
                                            blurRadius: 10,
                                            offset: const Offset(0, 2),
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
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(14),
                                    ),
                                  ),
                                  child: _isSubmitting
                                      ? const SizedBox(
                                          height: 20,
                                          width: 20,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2.2,
                                            color: Colors.white,
                                          ),
                                        )
                                      : const Text(
                                          'Create Account & Continue',
                                          style: TextStyle(
                                            fontSize: 15,
                                            fontWeight: FontWeight.w700,
                                            letterSpacing: 0.3,
                                          ),
                                        ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 20),

                        // ── 6. Sign In Navigation Link (Sitting on Peacock BG)
                        Center(
                          child: Wrap(
                            alignment: WrapAlignment.center,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              Text(
                                'Already have an account? ',
                                style: TextStyle(
                                  fontSize: 13.5,
                                  color: Colors.white.withValues(alpha: 0.85),
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
                                child: const Padding(
                                  padding: EdgeInsets.symmetric(
                                    horizontal: 4,
                                    vertical: 4,
                                  ),
                                  child: Text(
                                    'Sign In',
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w800,
                                      color: Color(0xFF6EE7B7), // Mint/Emerald glow
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 20),

                        // ── 7. Informational & Legal Links ───────────────────
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
                              color: Colors.white.withValues(alpha: 0.75),
                            ),
                            Text('•', style: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 11)),
                            _LegalLink(
                              label: 'Terms of Service',
                              onTap: () => _showInfoSheet(
                                context,
                                'Terms of Service',
                                'Technicians operating on the SEVO platform agree to follow safety protocols, quality checklists, and vendor dispatch guidelines. All work is subject to customer verification and platform approval.',
                              ),
                              color: Colors.white.withValues(alpha: 0.75),
                            ),
                            Text('•', style: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 11)),
                            _LegalLink(
                              label: 'Support & Contact',
                              onTap: () => _showInfoSheet(
                                context,
                                'Support & Contact',
                                'For operational, payroll, or document verification assistance, contact SEVO Workforce Operations Desk via email at support@calservices.com.',
                              ),
                              color: Colors.white.withValues(alpha: 0.75),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Center(
                          child: Text(
                            '© 2026 CALDIM ENGINEERING PRIVATE LIMITED. All rights reserved.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 10.5,
                              color: Colors.white.withValues(alpha: 0.55),
                              height: 1.3,
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader({
    required IconData icon,
    required String label,
    required Color color,
    required Color bgColor,
  }) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.8,
                  color: color,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  InputDecoration _inputDecoration({
    required String hintText,
    required IconData prefixIcon,
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      prefixIcon: Icon(prefixIcon, color: const Color(0xFF64748B), size: 19),
      suffixIcon: suffixIcon,
      hintText: hintText,
      hintStyle: const TextStyle(
        color: Color(0xFF94A3B8),
        fontSize: 13.5,
        fontWeight: FontWeight.w400,
      ),
      errorStyle: const TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w500,
        color: Color(0xFFE11D48),
      ),
      errorMaxLines: 2,
      filled: true,
      fillColor: const Color(0xFFF8FAFC),
      contentPadding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 14,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFF004E89), width: 1.8),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFE11D48), width: 1.2),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFE11D48), width: 1.8),
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
        style: const TextStyle(
          fontSize: 12.5,
          fontWeight: FontWeight.w700,
          color: Color(0xFF0F172A),
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
  const _LegalLink({
    required this.label,
    required this.onTap,
    this.color,
  });

  final String label;
  final VoidCallback onTap;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final effectiveColor = color ?? const Color(0xFF64748B);
    return GestureDetector(
      onTap: onTap,
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: effectiveColor,
          decoration: TextDecoration.underline,
          decorationColor: effectiveColor.withValues(alpha: 0.5),
        ),
      ),
    );
  }
}


