import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/async_value_view.dart';
import '../../profile/domain/employee_profile.dart';
import '../../profile/presentation/profile_providers.dart';
import 'documents_providers.dart';

/// Specification for a standard platform compliance document requirement.
class DocumentRequirementSpec {
  const DocumentRequirementSpec({
    required this.categoryKeys,
    required this.defaultCategory,
    required this.title,
    required this.description,
    required this.isMandatory,
    required this.icon,
  });

  final List<String> categoryKeys;
  final String defaultCategory;
  final String title;
  final String description;
  final bool isMandatory;
  final IconData icon;
}

const _standardRequirementSpecs = [
  DocumentRequirementSpec(
    categoryKeys: ['identity_proof', 'government_id', 'aadhaar', 'gov_id', 'id_proof'],
    defaultCategory: 'identity_proof',
    title: 'Government Identity Proof (Aadhaar / ID)',
    description: 'Government issued photo identity with full name and date of birth.',
    isMandatory: true,
    icon: Icons.badge_outlined,
  ),
  DocumentRequirementSpec(
    categoryKeys: ['driving_license', 'driver_license', 'driving_licence', 'license', 'vehicle_rc'],
    defaultCategory: 'driving_license',
    title: 'Driving License / Vehicle RC',
    description: 'Valid motor vehicle license for field transit and customer dispatch.',
    isMandatory: true,
    icon: Icons.directions_car_outlined,
  ),
  DocumentRequirementSpec(
    categoryKeys: [
      'trade_qualification',
      'technical_qualification',
      'qualification',
      'trade_certification',
      'certification',
      'vocational'
    ],
    defaultCategory: 'technical_qualification',
    title: 'Trade & Technical Qualification',
    description: 'ITI, Diploma, or verified vocational trade certification in your service category.',
    isMandatory: true,
    icon: Icons.workspace_premium_outlined,
  ),
  DocumentRequirementSpec(
    categoryKeys: ['police_verification', 'background_check', 'pcc', 'police_clearance'],
    defaultCategory: 'police_verification',
    title: 'Police Verification / Background Check',
    description: 'Criminal background clearance report or local police verification certificate.',
    isMandatory: false,
    icon: Icons.verified_user_outlined,
  ),
  DocumentRequirementSpec(
    categoryKeys: ['bank_passbook', 'bank_proof', 'cancelled_cheque', 'bank_statement', 'passbook'],
    defaultCategory: 'bank_passbook',
    title: 'Bank Passbook / Cancelled Cheque',
    description: 'Official document clearly showing your name, account number, and IFSC code.',
    isMandatory: true,
    icon: Icons.account_balance_outlined,
  ),
];

/// Classic Documents & Identity screen for Workforce mobile app.
///
/// Features:
/// 1. Classic App Bar with Peacock gradient, title "Documents & Identity", back navigation, and refresh action.
/// 2. Subtitle: "Manage your identity credentials, trade certifications, and compliance verification files"
/// 3. Credential Status Card with audit explanation and dynamic Account Status badge.
/// 4. 5 Standard Document Cards (Identity, License, Qualification, Police Verification, Bank Proof) with:
///    - Mandatory / Optional badge
///    - Approved / Pending / Missing / Rejected status styling
///    - Upload File / View Uploaded Document / Replace Document actions
/// 5. Image picker & document upload integration via DocumentsApi.
/// 6. In-app document preview dialog & browser launcher.
/// 7. Responsive layout supporting 320px-412px widths with zero RenderFlex overflow.
class DocumentsScreen extends ConsumerWidget {
  const DocumentsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(employeeProfileProvider);
    final actionState = ref.watch(documentsControllerProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.peacockNavy,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: false,
        leading: Navigator.of(context).canPop()
            ? IconButton(
                icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
                tooltip: 'Back',
                onPressed: () => Navigator.of(context).pop(),
              )
            : null,
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: AppColors.peacockGradient,
          ),
        ),
        title: const Text(
          'Documents & Identity',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w800,
            color: Colors.white,
            letterSpacing: 0.2,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 22),
            tooltip: 'Refresh Documents',
            onPressed: () => ref.invalidate(employeeProfileProvider),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(employeeProfileProvider.future),
        child: AsyncValueView<EmployeeProfile>(
          value: profileAsync,
          onRetry: () => ref.invalidate(employeeProfileProvider),
          builder: (context, profile) {
            final docsList = profile.documents;

            // Match documents to standard specs
            final matchedDocs = <DocumentRequirementSpec, EmployeeDocument?>{};
            final claimedDocIndices = <int>{};

            for (final spec in _standardRequirementSpecs) {
              EmployeeDocument? matched;
              for (int i = 0; i < docsList.length; i++) {
                if (claimedDocIndices.contains(i)) continue;
                final doc = docsList[i];
                final cat = doc.category.toLowerCase();
                final title = doc.title.toLowerCase();

                final matchesCat = spec.categoryKeys.any((k) => cat.contains(k) || k.contains(cat));
                final matchesTitle = spec.categoryKeys.any((k) => title.contains(k.replaceAll('_', ' ')));

                if (matchesCat || matchesTitle) {
                  matched = doc;
                  claimedDocIndices.add(i);
                  break;
                }
              }
              matchedDocs[spec] = matched;
            }

            // Unclaimed additional documents
            final extraDocs = <EmployeeDocument>[];
            for (int i = 0; i < docsList.length; i++) {
              if (!claimedDocIndices.contains(i)) {
                extraDocs.add(docsList[i]);
              }
            }

            // Calculate account compliance status
            final regStatus = profile.registrationStatus.toLowerCase();
            final String accountStatusDisplay;
            final Color accountStatusColor;

            if (regStatus == 'approved' || regStatus == 'verified' || regStatus == 'active') {
              accountStatusDisplay = 'Approved';
              accountStatusColor = const Color(0xFF059669); // Emerald Green
            } else if (regStatus == 'rejected') {
              accountStatusDisplay = 'Rejected';
              accountStatusColor = const Color(0xFFE11D48); // Red
            } else if (regStatus == 'under_review') {
              accountStatusDisplay = 'Under Review';
              accountStatusColor = const Color(0xFFD97706); // Amber
            } else if (regStatus == 'submitted' || regStatus == 'pending') {
              accountStatusDisplay = 'Pending Review';
              accountStatusColor = const Color(0xFFD97706); // Amber
            } else {
              accountStatusDisplay = 'Pending';
              accountStatusColor = const Color(0xFFD97706);
            }

            return ListView(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.lg,
                AppSpacing.sm,
                AppSpacing.lg,
                AppSpacing.xxl,
              ),
              children: [
                // ── Subtitle Context ─────────────────────────────────────────
                Text(
                  'Manage your identity credentials, trade certifications, and compliance verification files',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.textMuted,
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: AppSpacing.md),

                // ── Credential Status Card ───────────────────────────────────
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(AppRadius.card),
                    border: Border.all(
                      color: const Color(0xFF004E89).withValues(alpha: 0.2),
                    ),
                    boxShadow: AppElevation.subtle,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
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
                              Icons.shield_outlined,
                              size: 18,
                              color: Color(0xFF004E89),
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          const Expanded(
                            child: Text(
                              'Credential Status',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF0F172A),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: accountStatusColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(999),
                          border: Border.all(
                            color: accountStatusColor.withValues(alpha: 0.35),
                            width: 0.8,
                          ),
                        ),
                        child: Text(
                          accountStatusColor == const Color(0xFF059669)
                              ? '🟢 Account Status: $accountStatusDisplay'
                              : 'Account Status: $accountStatusDisplay',
                          style: TextStyle(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w800,
                            color: accountStatusColor,
                          ),
                        ),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Text(
                        'All documents are securely archived and audited against platform compliance requirements.',
                        style: TextStyle(
                          fontSize: 11.5,
                          color: AppColors.textSecondary,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.md),

                // ── Document Requirement Cards ───────────────────────────────
                for (final spec in _standardRequirementSpecs) ...[
                  _StandardDocumentCard(
                    spec: spec,
                    document: matchedDocs[spec],
                    isUploading: actionState.isLoading,
                    onUpload: () => _handleDocUpload(
                      context,
                      ref,
                      category: matchedDocs[spec]?.category ?? spec.defaultCategory,
                      title: spec.title,
                      documentNumber: matchedDocs[spec]?.documentNumber,
                    ),
                    onPreview: () {
                      if (matchedDocs[spec]?.hasFile == true) {
                        _handleDocPreview(context, matchedDocs[spec]!);
                      }
                    },
                  ),
                  const SizedBox(height: AppSpacing.sm),
                ],

                // ── Additional Custom Documents on file ──────────────────────
                if (extraDocs.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    'ADDITIONAL COMPLIANCE FILES',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.5,
                      color: AppColors.textMuted,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  for (final doc in extraDocs) ...[
                    _CustomDocumentCard(
                      document: doc,
                      isUploading: actionState.isLoading,
                      onUpload: () => _handleDocUpload(
                        context,
                        ref,
                        category: doc.category,
                        title: doc.title,
                        documentNumber: doc.documentNumber,
                      ),
                      onPreview: () {
                        if (doc.hasFile) {
                          _handleDocPreview(context, doc);
                        }
                      },
                    ),
                    const SizedBox(height: AppSpacing.sm),
                  ],
                ],
              ],
            );
          },
        ),
      ),
    );
  }

  Future<void> _handleDocUpload(
    BuildContext context,
    WidgetRef ref, {
    required String category,
    required String title,
    String? documentNumber,
  }) async {
    final picker = ImagePicker();
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
      ),
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: AppSpacing.sm),
            Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.border,
                borderRadius: BorderRadius.circular(999),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined, color: Color(0xFF004E89)),
              title: Text(
                'Take Photo of $title',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
              ),
              onTap: () => Navigator.of(ctx).pop(ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined, color: Color(0xFF004E89)),
              title: const Text(
                'Choose from Gallery',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
              ),
              onTap: () => Navigator.of(ctx).pop(ImageSource.gallery),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
        ),
      ),
    );

    if (source == null) return;

    final image = await picker.pickImage(source: source, imageQuality: 85, maxWidth: 1600);
    if (image == null) return;

    final success = await ref.read(documentsControllerProvider.notifier).uploadDocument(
          category: category,
          filePath: image.path,
          title: title,
          documentNumber: documentNumber,
        );

    if (!context.mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$title uploaded successfully.'),
          backgroundColor: const Color(0xFF059669),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to upload $title.'),
          backgroundColor: const Color(0xFFDC2626),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  void _handleDocPreview(BuildContext context, EmployeeDocument doc) {
    if (!doc.hasFile) return;

    final url = doc.fileUrl!;
    final isImage = url.toLowerCase().contains(RegExp(r'\.(jpeg|jpg|png|gif|webp)')) ||
        url.startsWith('data:image');

    if (isImage) {
      showDialog(
        context: context,
        builder: (ctx) => Dialog(
          clipBehavior: Clip.antiAlias,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.card),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AppBar(
                backgroundColor: AppColors.peacockNavy,
                foregroundColor: Colors.white,
                title: Text(
                  doc.title,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
                ),
                automaticallyImplyLeading: false,
                actions: [
                  IconButton(
                    icon: const Icon(Icons.close_rounded, color: Colors.white),
                    onPressed: () => Navigator.of(ctx).pop(),
                  ),
                ],
              ),
              InteractiveViewer(
                child: Image.network(
                  url,
                  fit: BoxFit.contain,
                  loadingBuilder: (context, child, progress) {
                    if (progress == null) return child;
                    return const SizedBox(
                      height: 250,
                      child: Center(
                        child: CircularProgressIndicator(color: Color(0xFF004E89)),
                      ),
                    );
                  },
                  errorBuilder: (context, error, stack) => const SizedBox(
                    height: 200,
                    child: Center(child: Text('Failed to load image preview')),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton.icon(
                      onPressed: () => launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication),
                      icon: const Icon(Icons.open_in_browser_rounded, size: 16),
                      label: const Text('Open External'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    } else {
      launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    }
  }
}

// ── Standard Document Requirement Card ────────────────────────────────────────

class _StandardDocumentCard extends StatelessWidget {
  const _StandardDocumentCard({
    required this.spec,
    required this.document,
    required this.isUploading,
    required this.onUpload,
    required this.onPreview,
  });

  final DocumentRequirementSpec spec;
  final EmployeeDocument? document;
  final bool isUploading;
  final VoidCallback onUpload;
  final VoidCallback onPreview;

  @override
  Widget build(BuildContext context) {
    final doc = document;
    final isUploaded = doc != null && (doc.hasFile || doc.isApproved || doc.isPending);

    // Resolve status
    final String statusText;
    final Color statusColor;

    if (doc == null || (!doc.hasFile && doc.status.toLowerCase() == 'missing')) {
      statusText = 'Missing';
      statusColor = const Color(0xFF64748B); // Slate
    } else if (doc.isApproved) {
      statusText = 'Approved';
      statusColor = const Color(0xFF059669); // Emerald Green
    } else if (doc.isRejected) {
      statusText = 'Rejected';
      statusColor = const Color(0xFFDC2626); // Red
    } else if (doc.isPending) {
      statusText = 'Pending';
      statusColor = const Color(0xFFD97706); // Amber
    } else {
      statusText = doc.status.toUpperCase();
      statusColor = const Color(0xFF004E89);
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(
          color: isUploaded ? AppColors.border : const Color(0xFFD97706).withValues(alpha: 0.3),
          width: 1.0,
        ),
        boxShadow: AppElevation.subtle,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Row: Icon + Title + Badges
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: isUploaded
                      ? const Color(0xFF004E89).withValues(alpha: 0.1)
                      : const Color(0xFFFFFBEB),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(
                  spec.icon,
                  size: 20,
                  color: isUploaded ? const Color(0xFF004E89) : const Color(0xFFD97706),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      spec.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Wrap(
                      spacing: 6,
                      runSpacing: 4,
                      children: [
                        // Mandatory / Optional badge
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: spec.isMandatory
                                ? const Color(0xFFEFF6FF)
                                : const Color(0xFFF1F5F9),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                              color: spec.isMandatory
                                  ? const Color(0xFFBFDBFE)
                                  : const Color(0xFFCBD5E1),
                              width: 0.6,
                            ),
                          ),
                          child: Text(
                            spec.isMandatory ? 'Mandatory' : 'Optional',
                            style: TextStyle(
                              fontSize: 9.5,
                              fontWeight: FontWeight.w800,
                              color: spec.isMandatory
                                  ? const Color(0xFF1D4ED8)
                                  : const Color(0xFF475569),
                            ),
                          ),
                        ),
                        // Status badge
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: statusColor.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                              color: statusColor.withValues(alpha: 0.35),
                              width: 0.6,
                            ),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (statusText == 'Approved')
                                const Text('🟢 ', style: TextStyle(fontSize: 7.5)),
                              Text(
                                statusText,
                                style: TextStyle(
                                  fontSize: 9.5,
                                  fontWeight: FontWeight.w800,
                                  color: statusColor,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),

          // Description
          Text(
            spec.description,
            style: TextStyle(
              fontSize: 11.5,
              color: AppColors.textSecondary,
              height: 1.35,
            ),
          ),

          // Document Number / Metadata if uploaded
          if (doc != null && doc.documentNumber?.isNotEmpty == true) ...[
            const SizedBox(height: 6),
            Text(
              'Doc #: ${doc.documentNumber}',
              style: TextStyle(
                fontSize: 11,
                fontFamily: 'monospace',
                fontWeight: FontWeight.bold,
                color: AppColors.textMuted,
              ),
            ),
          ],

          // Rejection Reason Alert if rejected
          if (doc != null && doc.isRejected && doc.rejectionReason?.isNotEmpty == true) ...[
            const SizedBox(height: AppSpacing.sm),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.sm),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF1F2),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFFFECDD3), width: 0.8),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.error_outline_rounded, size: 14, color: Color(0xFFDC2626)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Rejection Reason: ${doc.rejectionReason}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: Color(0xFF9F1239),
                        height: 1.3,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: AppSpacing.sm),

          // Action Buttons
          if (isUploaded) ...[
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                if (doc.hasFile)
                  OutlinedButton.icon(
                    onPressed: onPreview,
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      side: BorderSide(color: AppColors.border),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                    icon: const Icon(Icons.visibility_outlined, size: 15, color: Color(0xFF004E89)),
                    label: const Text(
                      'View Uploaded Document',
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF004E89),
                      ),
                    ),
                  ),
                FilledButton.icon(
                  onPressed: isUploading ? null : onUpload,
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF004E89),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  icon: isUploading
                      ? const SizedBox(
                          width: 12,
                          height: 12,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.file_upload_outlined, size: 15, color: Colors.white),
                  label: const Text(
                    'Replace Document',
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ] else ...[
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: isUploading ? null : onUpload,
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF004E89),
                  padding: const EdgeInsets.symmetric(vertical: 9),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
                icon: isUploading
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.upload_file_outlined, size: 16, color: Colors.white),
                label: const Text(
                  'Upload File',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ── Custom Additional Document Card ───────────────────────────────────────────

class _CustomDocumentCard extends StatelessWidget {
  const _CustomDocumentCard({
    required this.document,
    required this.isUploading,
    required this.onUpload,
    required this.onPreview,
  });

  final EmployeeDocument document;
  final bool isUploading;
  final VoidCallback onUpload;
  final VoidCallback onPreview;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: AppColors.border),
        boxShadow: AppElevation.subtle,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF004E89).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.description_outlined, size: 20, color: Color(0xFF004E89)),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  document.title,
                  style: TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: 8,
            children: [
              if (document.hasFile)
                OutlinedButton.icon(
                  onPressed: onPreview,
                  icon: const Icon(Icons.visibility_outlined, size: 14),
                  label: const Text('View Uploaded Document', style: TextStyle(fontSize: 11.5)),
                ),
              FilledButton.icon(
                onPressed: isUploading ? null : onUpload,
                style: FilledButton.styleFrom(backgroundColor: const Color(0xFF004E89)),
                icon: const Icon(Icons.file_upload_outlined, size: 14),
                label: const Text('Replace Document', style: TextStyle(fontSize: 11.5)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
