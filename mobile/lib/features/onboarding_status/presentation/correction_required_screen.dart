import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/theme/app_typography.dart';
import '../../../routing/app_routes.dart';
import '../../../shared/widgets/workforce_app_bar.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../documents/presentation/documents_providers.dart';
import '../../onboarding_wizard/presentation/onboarding_wizard_providers.dart';
import '../../profile/domain/employee_profile.dart';
import '../../profile/presentation/profile_providers.dart';

class CorrectionRequiredScreen extends ConsumerStatefulWidget {
  const CorrectionRequiredScreen({super.key});

  @override
  ConsumerState<CorrectionRequiredScreen> createState() =>
      _CorrectionRequiredScreenState();
}

class _CorrectionRequiredScreenState
    extends ConsumerState<CorrectionRequiredScreen> {
  bool _isSubmitting = false;
  String? _errorMessage;
  String? _successMessage;

  Future<void> _handleDocumentReplace(String category, String title) async {
    final picker = ImagePicker();
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      shape: RoundedRectangleBorder(
        borderRadius:
            BorderRadius.vertical(top: Radius.circular(AppRadius.sheet)),
      ),
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: AppSpacing.sm),
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: Text('Take Photo of $title'),
              onTap: () => Navigator.of(context).pop(ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Choose from Gallery'),
              onTap: () => Navigator.of(context).pop(ImageSource.gallery),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
        ),
      ),
    );
    if (source == null) return;

    final image = await picker.pickImage(
      source: source,
      imageQuality: 85,
      maxWidth: 1600,
    );
    if (image == null) return;

    setState(() {
      _errorMessage = null;
      _successMessage = null;
    });

    final success = await ref
        .read(documentsControllerProvider.notifier)
        .uploadDocument(category: category, filePath: image.path, title: title);

    if (!mounted) return;
    if (success) {
      ref.invalidate(employeeProfileProvider);
      setState(() => _successMessage = 'Replacement for $title uploaded!');
    } else {
      setState(() => _errorMessage = 'Failed to upload document replacement.');
    }
  }

  Future<void> _resubmit() async {
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    final ok =
        await ref.read(onboardingWizardControllerProvider.notifier).submit();

    if (!mounted) return;
    setState(() => _isSubmitting = false);
    if (!ok) {
      setState(() => _errorMessage =
          'Resubmission failed. Please verify documents and retry.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(employeeProfileProvider);
    final profile = profileAsync.valueOrNull;
    final notes = profile?.onboardingData.correctionNotes?.isNotEmpty == true
        ? profile!.onboardingData.correctionNotes!
        : 'Please update the highlighted documents/details below.';
    final docs = profile?.documents ?? <EmployeeDocument>[];

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: const WorkforceAppBar(
        titleText: 'SEVO',
        showBrand: true,
        showSearch: false,
        showNotifications: false,
        showAvatar: false,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: AppSpacing.lg,
          ),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Container(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius:
                          BorderRadius.circular(AppRadius.cardStandard),
                      border: Border.all(color: AppColors.border),
                      boxShadow: AppElevation.subtle,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // ── Header Row ───────────────────────────────────
                        Row(
                          children: [
                            Container(
                              width: 44,
                              height: 44,
                              decoration: BoxDecoration(
                                color: AppColors.warning.tint,
                                border: Border.all(
                                    color: AppColors.warning.tintBorder),
                                borderRadius:
                                    BorderRadius.circular(AppRadius.button),
                              ),
                              child: Icon(
                                Icons.edit_note_rounded,
                                size: 24,
                                color: AppColors.warning.base,
                              ),
                            ),
                            const SizedBox(width: AppSpacing.md),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 2,
                                    ),
                                    decoration: BoxDecoration(
                                      color: AppColors.warning.tint,
                                      borderRadius:
                                          BorderRadius.circular(AppRadius.chip),
                                      border: Border.all(
                                          color: AppColors.warning.tintBorder),
                                    ),
                                    child: Text(
                                      'ACTION REQUIRED',
                                      style: TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w800,
                                        letterSpacing: 0.6,
                                        color: AppColors.warning.onTint,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    'Corrections Needed',
                                    style: AppTypography.pageTitle,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.md),

                        // ── Admin Notes Box ──────────────────────────────
                        Container(
                          padding: const EdgeInsets.all(AppSpacing.md),
                          decoration: BoxDecoration(
                            color: AppColors.warning.tint,
                            border:
                                Border.all(color: AppColors.warning.tintBorder),
                            borderRadius:
                                BorderRadius.circular(AppRadius.input),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'ADMIN REVIEW NOTES:',
                                style: TextStyle(
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 0.6,
                                  color: AppColors.warning.onTint,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '"$notes"',
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textPrimary,
                                  height: 1.4,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),

                        if (_errorMessage != null) ...[
                          Container(
                            padding: const EdgeInsets.all(AppSpacing.sm),
                            decoration: BoxDecoration(
                              color: AppColors.error.tint,
                              border:
                                  Border.all(color: AppColors.error.tintBorder),
                              borderRadius:
                                  BorderRadius.circular(AppRadius.input),
                            ),
                            child: Text(
                              _errorMessage!,
                              style: TextStyle(
                                color: AppColors.error.onTint,
                                fontSize: 12,
                              ),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                        ],

                        if (_successMessage != null) ...[
                          Container(
                            padding: const EdgeInsets.all(AppSpacing.sm),
                            decoration: BoxDecoration(
                              color: AppColors.success.tint,
                              border: Border.all(
                                  color: AppColors.success.tintBorder),
                              borderRadius:
                                  BorderRadius.circular(AppRadius.input),
                            ),
                            child: Text(
                              _successMessage!,
                              style: TextStyle(
                                color: AppColors.success.onTint,
                                fontSize: 12,
                              ),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                        ],

                        // ── Documents to Review ──────────────────────────
                        Text(
                          'DOCUMENTS TO REVIEW',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.6,
                            color: AppColors.textMuted,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.sm),

                        if (docs.isEmpty)
                          Container(
                            padding: const EdgeInsets.all(AppSpacing.md),
                            decoration: BoxDecoration(
                              color: AppColors.background,
                              borderRadius:
                                  BorderRadius.circular(AppRadius.input),
                              border: Border.all(color: AppColors.border),
                            ),
                            child: const Text(
                              'Please use the Registration Wizard below to review all form details and files.',
                              style: TextStyle(fontSize: 12),
                            ),
                          )
                        else
                          ...docs.map((doc) {
                            final isRejected = doc.isRejected;
                            return Container(
                              margin:
                                  const EdgeInsets.only(bottom: AppSpacing.sm),
                              padding: const EdgeInsets.all(AppSpacing.md),
                              decoration: BoxDecoration(
                                color: isRejected
                                    ? AppColors.error.tint
                                    : AppColors.background,
                                border: Border.all(
                                  color: isRejected
                                      ? AppColors.error.tintBorder
                                      : AppColors.border,
                                ),
                                borderRadius:
                                    BorderRadius.circular(AppRadius.input),
                              ),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.center,
                                children: [
                                  Icon(
                                    isRejected
                                        ? Icons.error_outline_rounded
                                        : Icons.file_present_outlined,
                                    color: isRejected
                                        ? AppColors.error.base
                                        : AppColors.textMuted,
                                    size: 20,
                                  ),
                                  const SizedBox(width: AppSpacing.sm),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          doc.title,
                                          style: const TextStyle(
                                            fontSize: 13,
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                        if (doc.rejectionReason != null &&
                                            doc.rejectionReason!.isNotEmpty)
                                          Text(
                                            'Flag: ${doc.rejectionReason}',
                                            style: TextStyle(
                                              fontSize: 11.5,
                                              fontWeight: FontWeight.w600,
                                              color: AppColors.error.base,
                                            ),
                                          ),
                                      ],
                                    ),
                                  ),
                                  OutlinedButton.icon(
                                    onPressed: () => _handleDocumentReplace(
                                      doc.category,
                                      doc.title,
                                    ),
                                    icon: const Icon(Icons.upload_file_rounded,
                                        size: 15),
                                    label: const Text('Replace',
                                        style: TextStyle(fontSize: 12)),
                                  ),
                                ],
                              ),
                            );
                          }),

                        const SizedBox(height: AppSpacing.lg),

                        // ── Navigation Buttons ───────────────────────────
                        ElevatedButton.icon(
                          onPressed: () =>
                              context.push(AppRoutes.onboardingWizard),
                          icon: const Icon(Icons.tune_rounded, size: 18),
                          label: const Text('Open Registration Wizard'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            foregroundColor: Colors.white,
                            minimumSize: const Size.fromHeight(46),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        OutlinedButton.icon(
                          onPressed: _isSubmitting ? null : _resubmit,
                          icon: _isSubmitting
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child:
                                      CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.send_rounded, size: 18),
                          label: Text(_isSubmitting
                              ? 'Resubmitting...'
                              : 'Resubmit Application'),
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size.fromHeight(46),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        TextButton(
                          onPressed: () => ref
                              .read(authControllerProvider.notifier)
                              .logout(),
                          child: const Text('Log Out'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
