import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/admin_application.dart';
import 'package:mobile/features/superadmin/applications/data/superadmin_applications_repository.dart';
import 'package:mobile/shared/widgets/workforce_avatar.dart';
import 'package:url_launcher/url_launcher.dart';

import 'application_status_badge.dart';

/// Detailed dossier bottom sheet for inspecting an applicant's submitted credentials,
/// trade services, uploaded compliance documents, and executing individual & bulk review actions.
class ApplicationDetailSheet extends ConsumerStatefulWidget {
  const ApplicationDetailSheet({
    super.key,
    required this.application,
    required this.onApprove,
    required this.onReject,
    required this.onRequestCorrection,
    this.onOpenFullDossier,
    this.onDossierUpdated,
  });

  final AdminApplication application;
  final VoidCallback onApprove;
  final VoidCallback onReject;
  final VoidCallback onRequestCorrection;
  final VoidCallback? onOpenFullDossier;
  final VoidCallback? onDossierUpdated;

  @override
  ConsumerState<ApplicationDetailSheet> createState() =>
      _ApplicationDetailSheetState();
}

class _ApplicationDetailSheetState extends ConsumerState<ApplicationDetailSheet> {
  late AdminApplication _application;
  final Set<int> _processingServiceIds = {};
  final Set<String> _processingDocCategories = {};
  bool _isBulkProcessing = false;

  @override
  void initState() {
    super.initState();
    _application = widget.application;
  }

  void _showFeedback(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(
              isError ? Icons.error_outline_rounded : Icons.check_circle_outline_rounded,
              color: Colors.white,
              size: 20,
            ),
            const SizedBox(width: 10),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: isError ? const Color(0xFFDC2626) : const Color(0xFF059669),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 4),
      ),
    );
  }

  String _extractErrorMessage(dynamic error, String fallback) {
    if (error is DioException && error.response?.data is Map) {
      final data = error.response!.data as Map;
      if (data['error'] != null) return data['error'].toString();
      if (data['message'] != null) return data['message'].toString();
      if (data['detail'] != null) return data['detail'].toString();
    }
    return error?.toString() ?? fallback;
  }

  Future<void> _refreshDossier() async {
    try {
      final freshApp = await ref
          .read(superAdminApplicationsRepositoryProvider)
          .fetchApplicationDetail(_application.id);
      if (mounted) {
        setState(() {
          _application = freshApp;
        });
      }
      widget.onDossierUpdated?.call();
    } catch (_) {
      // Keep existing application if fetch fails
    }
  }

  Future<void> _viewDocument(String? urlString) async {
    if (urlString == null || urlString.isEmpty) {
      _showFeedback('Document file URL is not available.', isError: true);
      return;
    }
    try {
      final uri = Uri.parse(urlString);
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched && mounted) {
        _showFeedback('Could not open document URL: $urlString', isError: true);
      }
    } catch (e) {
      if (mounted) {
        _showFeedback('Failed to open document: $e', isError: true);
      }
    }
  }

  // ── Service Decisions ───────────────────────────────────────────────────────

  Future<void> _handleDecideService(AdminServiceItem svc, String action) async {
    String reason = '';
    if (action == 'reject') {
      final reasonCtrl = TextEditingController();
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text('Reject Service "${svc.name}"'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Please specify a reason for rejecting this service authorization:'),
              const SizedBox(height: 10),
              TextField(
                controller: reasonCtrl,
                decoration: const InputDecoration(
                  hintText: 'e.g. Does not meet minimum certification criteria...',
                  border: OutlineInputBorder(),
                ),
                maxLines: 2,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFFDC2626)),
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Reject Service'),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
      reason = reasonCtrl.text.trim();
      if (reason.isEmpty) {
        _showFeedback('A rejection reason is required to reject a service.', isError: true);
        return;
      }
    }

    setState(() => _processingServiceIds.add(svc.id));
    try {
      final res = await ref
          .read(superAdminApplicationsRepositoryProvider)
          .decideService(
            employeeId: _application.id,
            serviceId: svc.id,
            action: action,
            reason: reason,
          );
      final msg = res['message'] ??
          (action == 'approve'
              ? 'Service "${svc.name}" approved.'
              : 'Service "${svc.name}" rejected.');
      _showFeedback(msg);
      await _refreshDossier();
    } catch (e) {
      _showFeedback(_extractErrorMessage(e, 'Failed to update service authorization.'), isError: true);
    } finally {
      if (mounted) {
        setState(() => _processingServiceIds.remove(svc.id));
      }
    }
  }

  Future<void> _handleBulkDecideServices(String action) async {
    setState(() => _isBulkProcessing = true);
    try {
      final res = await ref
          .read(superAdminApplicationsRepositoryProvider)
          .bulkDecideServices(
            applicationId: _application.id,
            serviceIds: const [],
            action: action,
            allPending: true,
          );
      final count = res['updated_count'] ?? 0;
      _showFeedback(res['message'] ?? 'Successfully ${action}d $count service(s).');
      await _refreshDossier();
    } catch (e) {
      _showFeedback(_extractErrorMessage(e, 'Failed to bulk-decide services.'), isError: true);
    } finally {
      if (mounted) {
        setState(() => _isBulkProcessing = false);
      }
    }
  }

  // ── Document Decisions ─────────────────────────────────────────────────────

  Future<void> _handleVerifyDocument(AdminDocumentItem doc, String action) async {
    String reason = '';
    if (action == 'reject') {
      final reasonCtrl = TextEditingController();
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text('Reject Document "${doc.title}"'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Specify reason for rejecting this document:'),
              const SizedBox(height: 10),
              TextField(
                controller: reasonCtrl,
                decoration: const InputDecoration(
                  hintText: 'e.g. Blurry photo or unreadable document number...',
                  border: OutlineInputBorder(),
                ),
                maxLines: 2,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFFDC2626)),
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Reject Document'),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
      reason = reasonCtrl.text.trim();
      if (reason.isEmpty) {
        _showFeedback('A rejection reason is required to reject a document.', isError: true);
        return;
      }
    }

    setState(() => _processingDocCategories.add(doc.category));
    try {
      final res = await ref
          .read(superAdminApplicationsRepositoryProvider)
          .verifyDocument(
            applicationId: _application.id,
            docCategory: doc.category,
            action: action,
            reason: reason,
          );
      final msg = res['message'] ??
          (action == 'approve'
              ? 'Document "${doc.title}" approved.'
              : 'Document "${doc.title}" rejected.');
      _showFeedback(msg);
      await _refreshDossier();
    } catch (e) {
      _showFeedback(_extractErrorMessage(e, 'Failed to verify document.'), isError: true);
    } finally {
      if (mounted) {
        setState(() => _processingDocCategories.remove(doc.category));
      }
    }
  }

  Future<void> _handleBulkVerifyDocuments(String action) async {
    setState(() => _isBulkProcessing = true);
    try {
      final res = await ref
          .read(superAdminApplicationsRepositoryProvider)
          .bulkVerifyDocuments(
            applicationId: _application.id,
            categories: const [],
            action: action,
            allPending: true,
          );
      final count = res['updated_count'] ?? 0;
      _showFeedback(res['message'] ?? 'Successfully ${action}d $count document(s).');
      await _refreshDossier();
    } catch (e) {
      _showFeedback(_extractErrorMessage(e, 'Failed to bulk-verify documents.'), isError: true);
    } finally {
      if (mounted) {
        setState(() => _isBulkProcessing = false);
      }
    }
  }

  // ── Quick Approve All Prerequisites ───────────────────────────────────────

  Future<void> _handleQuickApproveAllPrerequisites() async {
    setState(() => _isBulkProcessing = true);
    try {
      if (_application.pendingDocumentsCount > 0) {
        await ref
            .read(superAdminApplicationsRepositoryProvider)
            .bulkVerifyDocuments(
              applicationId: _application.id,
              categories: const [],
              action: 'approve',
              allPending: true,
            );
      }
      if (_application.pendingServicesCount > 0) {
        await ref
            .read(superAdminApplicationsRepositoryProvider)
            .bulkDecideServices(
              applicationId: _application.id,
              serviceIds: const [],
              action: 'approve',
              allPending: true,
            );
      }
      _showFeedback('All prerequisite documents and services approved!');
      await _refreshDossier();
    } catch (e) {
      _showFeedback(_extractErrorMessage(e, 'Failed to approve prerequisites.'), isError: true);
    } finally {
      if (mounted) {
        setState(() => _isBulkProcessing = false);
      }
    }
  }

  void _onFinalApprovePressed() {
    final hasDocsApproved = _application.uploadedDocumentsCount == 0 ||
        (_application.pendingDocumentsCount == 0 && _application.rejectedDocumentsCount == 0);
    final hasServiceApproved = _application.approvedServicesCount > 0;

    if (!hasDocsApproved || !hasServiceApproved) {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: Color(0xFFD97706), size: 22),
              SizedBox(width: 8),
              Flexible(child: Text('Prerequisites Required')),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Before approving the technician for platform onboarding, the following requirements must be satisfied:',
                style: TextStyle(fontSize: 13, color: Color(0xFF334155)),
              ),
              const SizedBox(height: 12),
              _buildPrerequisiteItem(
                title: 'All Uploaded Documents Approved',
                isSatisfied: hasDocsApproved,
                detail: hasDocsApproved
                    ? '${_application.verifiedDocumentsCount}/${_application.uploadedDocumentsCount} Approved'
                    : '${_application.pendingDocumentsCount} Document(s) Pending Review',
              ),
              const SizedBox(height: 8),
              _buildPrerequisiteItem(
                title: 'At least 1 Service Approved',
                isSatisfied: hasServiceApproved,
                detail: hasServiceApproved
                    ? '${_application.approvedServicesCount} Service(s) Approved'
                    : 'No approved services yet',
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton.icon(
              icon: const Icon(Icons.bolt_rounded, size: 16),
              label: const Text('Approve Prerequisites First'),
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFF004E89)),
              onPressed: () {
                Navigator.of(ctx).pop();
                _handleQuickApproveAllPrerequisites();
              },
            ),
          ],
        ),
      );
      return;
    }

    widget.onApprove();
  }

  @override
  Widget build(BuildContext context) {
    final isDecided = _application.isApproved || _application.isRejected;
    final hasApprovedService = _application.approvedServicesCount > 0;
    final hasAllDocsApproved = _application.uploadedDocumentsCount == 0 ||
        (_application.pendingDocumentsCount == 0 && _application.rejectedDocumentsCount == 0);
    final isReadyForApproval = hasApprovedService && hasAllDocsApproved;

    return DraggableScrollableSheet(
      initialChildSize: 0.88,
      minChildSize: 0.45,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
          ),
          child: Column(
            children: [
              Center(
                child: Container(
                  margin: const EdgeInsets.symmetric(vertical: 8),
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: const Color(0xFFCBD5E1),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.fromLTRB(AppSpacing.md, 0, AppSpacing.md, AppSpacing.sm),
                decoration: const BoxDecoration(
                  border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    WorkforceAvatar(
                      imageUrl: _application.avatar,
                      name: _application.name,
                      initial: _application.initial,
                      radius: 22,
                      fontSize: 16,
                      backgroundColor: const Color(0xFF004E89).withValues(alpha: 0.1),
                      foregroundColor: const Color(0xFF004E89),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Flexible(
                                child: Text(
                                  _application.name ?? 'Technician #${_application.id}',
                                  style: const TextStyle(
                                    fontSize: 15,
                                    fontWeight: FontWeight.w800,
                                    color: Color(0xFF0F172A),
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              const SizedBox(width: 8),
                              ApplicationStatusBadge(
                                status: _application.registrationStatus,
                                dense: true,
                              ),
                            ],
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'ID: ${_application.employeeId ?? 'APP-#${_application.id}'}${_application.companyName != null ? ' • ${_application.companyName}' : ''}',
                            style: const TextStyle(
                              fontSize: 11,
                              color: Color(0xFF64748B),
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.w600,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                    if (widget.onOpenFullDossier != null) ...[
                      IconButton(
                        icon: const Icon(Icons.open_in_new_rounded, size: 18),
                        color: const Color(0xFF004E89),
                        tooltip: 'Open Full 7-Tab Dossier',
                        onPressed: widget.onOpenFullDossier,
                      ),
                    ],
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 20),
                      color: const Color(0xFF64748B),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.all(AppSpacing.md),
                  children: [
                    if (!isDecided) ...[
                      _buildPrerequisitesCard(
                        hasApprovedService: hasApprovedService,
                        hasAllDocsApproved: hasAllDocsApproved,
                        isReady: isReadyForApproval,
                      ),
                      const SizedBox(height: AppSpacing.md),
                    ],
                    _SectionBox(
                      title: 'PERSONAL INFORMATION',
                      icon: Icons.person_outline_rounded,
                      iconColor: const Color(0xFF2563EB),
                      children: [
                        _dataRow('Full Name', _application.name ?? '—'),
                        _dataRow('Mobile Number', _application.phone ?? '—', isMono: true),
                        _dataRow('Email Address', _application.email ?? '—'),
                        _dataRow('Date of Birth', _application.dob),
                        _dataRow('Gender', _application.gender),
                        _dataRow('Emergency Contact', _application.emergencyName),
                        _dataRow('Emergency Phone', _application.emergencyPhone, isMono: true),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _SectionBox(
                      title: 'ADDRESS & SERVICE TERRITORY',
                      icon: Icons.map_outlined,
                      iconColor: const Color(0xFF059669),
                      children: [
                        _dataRow('Street Address', _application.streetAddress),
                        _dataRow('City', _application.city),
                        _dataRow('State', _application.state),
                        _dataRow('Pincode', _application.pincode, isMono: true),
                        _dataRow('Service Radius', _application.serviceRadius, isBold: true, highlightColor: const Color(0xFF2563EB)),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _SectionBox(
                      title: 'PROFESSIONAL INFORMATION',
                      icon: Icons.military_tech_outlined,
                      iconColor: const Color(0xFF7C3AED),
                      children: [
                        _dataRow('Experience', _application.experienceYears, isBold: true),
                        _dataRow('Vehicle Transport', _application.vehicleType.toUpperCase()),
                        _dataRow('Driver License', _application.licenseNumber, isMono: true),
                        if (_application.skills.isNotEmpty) ...[
                          const SizedBox(height: 6),
                          const Text(
                            'Specialized Trade Skills:',
                            style: TextStyle(fontSize: 11, color: Color(0xFF64748B), fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 4),
                          Wrap(
                            spacing: 4,
                            runSpacing: 4,
                            children: _application.skills.entries.map((e) {
                              return Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFF1F5F9),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  '${e.key}: ${e.value}',
                                  style: const TextStyle(fontSize: 10.5, color: Color(0xFF334155), fontWeight: FontWeight.w700),
                                ),
                              );
                            }).toList(),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _SectionBox(
                      title: 'REQUESTED SERVICES (${_application.allRequestedServices.length})',
                      icon: Icons.handyman_outlined,
                      iconColor: const Color(0xFFD97706),
                      trailing: (!isDecided && _application.pendingServicesCount > 0)
                          ? InkWell(
                              onTap: _isBulkProcessing ? null : () => _handleBulkDecideServices('approve'),
                              borderRadius: BorderRadius.circular(4),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFECFDF5),
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(color: const Color(0xFFA7F3D0)),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.done_all_rounded, size: 13, color: Color(0xFF059669)),
                                    const SizedBox(width: 4),
                                    Text(
                                      _isBulkProcessing ? 'Approving...' : 'Approve All (${_application.pendingServicesCount})',
                                      style: const TextStyle(
                                        fontSize: 10.5,
                                        fontWeight: FontWeight.w700,
                                        color: Color(0xFF059669),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            )
                          : null,
                      children: [
                        if (_application.allRequestedServices.isEmpty)
                          const Text(
                            'No services requested in this application.',
                            style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                          )
                        else
                          ..._application.allRequestedServices.map((svc) {
                            final isProcessing = _processingServiceIds.contains(svc.id);
                            return Container(
                              margin: const EdgeInsets.only(bottom: 8),
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: svc.isApproved
                                    ? const Color(0xFFF0FDF4)
                                    : svc.isRejected
                                        ? const Color(0xFFFEF2F2)
                                        : const Color(0xFFF8FAFC),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: svc.isApproved
                                      ? const Color(0xFFBBF7D0)
                                      : svc.isRejected
                                          ? const Color(0xFFFECDD3)
                                          : const Color(0xFFE2E8F0),
                                ),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              svc.name,
                                              style: const TextStyle(
                                                fontSize: 13,
                                                fontWeight: FontWeight.w700,
                                                color: Color(0xFF0F172A),
                                              ),
                                            ),
                                            if (svc.category != null)
                                              Text(
                                                svc.category!,
                                                style: const TextStyle(
                                                  fontSize: 10.5,
                                                  color: Color(0xFF64748B),
                                                ),
                                              ),
                                          ],
                                        ),
                                      ),
                                      ApplicationStatusBadge(status: svc.status, dense: true),
                                    ],
                                  ),
                                  if (svc.rejectionReason != null && svc.rejectionReason!.isNotEmpty) ...[
                                    const SizedBox(height: 4),
                                    Text(
                                      'Reason: ${svc.rejectionReason}',
                                      style: const TextStyle(fontSize: 10.5, color: Color(0xFFDC2626)),
                                    ),
                                  ],
                                  if (!isDecided && svc.isPending) ...[
                                    const SizedBox(height: 6),
                                    const Divider(height: 1),
                                    const SizedBox(height: 6),
                                    Align(
                                      alignment: Alignment.centerRight,
                                      child: Wrap(
                                        alignment: WrapAlignment.end,
                                        spacing: 6,
                                        runSpacing: 4,
                                        children: [
                                          if (isProcessing)
                                            const SizedBox(
                                              width: 16,
                                              height: 16,
                                              child: CircularProgressIndicator(strokeWidth: 2),
                                            )
                                          else ...[
                                            OutlinedButton.icon(
                                              onPressed: () => _handleDecideService(svc, 'reject'),
                                              icon: const Icon(Icons.close_rounded, size: 14),
                                              label: const Text('Reject Svc'),
                                              style: OutlinedButton.styleFrom(
                                                foregroundColor: const Color(0xFFDC2626),
                                                side: const BorderSide(color: Color(0xFFFECDD3)),
                                                backgroundColor: const Color(0xFFFEF2F2),
                                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                                minimumSize: Size.zero,
                                                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                                textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                                              ),
                                            ),
                                            FilledButton.icon(
                                              onPressed: () => _handleDecideService(svc, 'approve'),
                                              icon: const Icon(Icons.check_rounded, size: 14),
                                              label: const Text('Approve Service'),
                                              style: FilledButton.styleFrom(
                                                backgroundColor: const Color(0xFF059669),
                                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                                minimumSize: Size.zero,
                                                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                                textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800),
                                              ),
                                            ),
                                          ],
                                        ],
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            );
                          }),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _SectionBox(
                      title: 'SUBMITTED DOCUMENTS (${_application.documentsList.length})',
                      icon: Icons.shield_outlined,
                      iconColor: const Color(0xFF0284C7),
                      trailing: (!isDecided && _application.pendingDocumentsCount > 0)
                          ? InkWell(
                              onTap: _isBulkProcessing ? null : () => _handleBulkVerifyDocuments('approve'),
                              borderRadius: BorderRadius.circular(4),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFECFDF5),
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(color: const Color(0xFFA7F3D0)),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.done_all_rounded, size: 13, color: Color(0xFF059669)),
                                    const SizedBox(width: 4),
                                    Text(
                                      _isBulkProcessing ? 'Verifying...' : 'Verify All (${_application.pendingDocumentsCount})',
                                      style: const TextStyle(
                                        fontSize: 10.5,
                                        fontWeight: FontWeight.w700,
                                        color: Color(0xFF059669),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            )
                          : null,
                      children: [
                        if (_application.documentsList.isEmpty)
                          const Text(
                            'No verification documents uploaded.',
                            style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                          )
                        else
                          ..._application.documentsList.map((doc) {
                            final isProcessing = _processingDocCategories.contains(doc.category);
                            return Container(
                              margin: const EdgeInsets.only(bottom: 8),
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: doc.isApproved
                                    ? const Color(0xFFF0FDF4)
                                    : doc.isRejected
                                        ? const Color(0xFFFEF2F2)
                                        : const Color(0xFFF8FAFC),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: doc.isApproved
                                      ? const Color(0xFFBBF7D0)
                                      : doc.isRejected
                                          ? const Color(0xFFFECDD3)
                                          : const Color(0xFFE2E8F0),
                                ),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      const Icon(Icons.description_outlined, size: 18, color: Color(0xFF2563EB)),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              doc.title,
                                              style: const TextStyle(
                                                fontSize: 12.5,
                                                fontWeight: FontWeight.w700,
                                                color: Color(0xFF0F172A),
                                              ),
                                            ),
                                            if (doc.documentNumber != null && doc.documentNumber!.isNotEmpty)
                                              Text(
                                                'No: ${doc.documentNumber}',
                                                style: const TextStyle(
                                                  fontSize: 10.5,
                                                  color: Color(0xFF64748B),
                                                  fontFamily: 'monospace',
                                                ),
                                              ),
                                          ],
                                        ),
                                      ),
                                      ApplicationStatusBadge(status: doc.status, dense: true),
                                    ],
                                  ),
                                  if (doc.rejectionReason != null && doc.rejectionReason!.isNotEmpty) ...[
                                    const SizedBox(height: 4),
                                    Text(
                                      'Reason: ${doc.rejectionReason}',
                                      style: const TextStyle(fontSize: 10.5, color: Color(0xFFDC2626)),
                                    ),
                                  ],
                                  const SizedBox(height: 6),
                                  const Divider(height: 1),
                                  const SizedBox(height: 6),
                                  Wrap(
                                    alignment: WrapAlignment.spaceBetween,
                                    crossAxisAlignment: WrapCrossAlignment.center,
                                    spacing: 6,
                                    runSpacing: 4,
                                    children: [
                                      if (doc.fileUrl != null && doc.fileUrl!.isNotEmpty)
                                        InkWell(
                                          onTap: () => _viewDocument(doc.fileUrl),
                                          borderRadius: BorderRadius.circular(4),
                                          child: Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3.5),
                                            decoration: BoxDecoration(
                                              color: const Color(0xFFEFF6FF),
                                              borderRadius: BorderRadius.circular(4),
                                              border: Border.all(color: const Color(0xFFBFDBFE)),
                                            ),
                                            child: const Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                Text(
                                                  'View File',
                                                  style: TextStyle(
                                                    fontSize: 11,
                                                    fontWeight: FontWeight.w700,
                                                    color: Color(0xFF1D4ED8),
                                                  ),
                                                ),
                                                SizedBox(width: 3),
                                                Icon(Icons.open_in_new_rounded, size: 12, color: Color(0xFF1D4ED8)),
                                              ],
                                            ),
                                          ),
                                        )
                                      else
                                        const SizedBox.shrink(),
                                      if (!isDecided && doc.isPending) ...[
                                        if (isProcessing)
                                          const SizedBox(
                                            width: 16,
                                            height: 16,
                                            child: CircularProgressIndicator(strokeWidth: 2),
                                          )
                                        else
                                          Wrap(
                                            spacing: 6,
                                            runSpacing: 4,
                                            children: [
                                              OutlinedButton.icon(
                                                onPressed: () => _handleVerifyDocument(doc, 'reject'),
                                                icon: const Icon(Icons.close_rounded, size: 13),
                                                label: const Text('Reject Doc'),
                                                style: OutlinedButton.styleFrom(
                                                  foregroundColor: const Color(0xFFDC2626),
                                                  side: const BorderSide(color: Color(0xFFFECDD3)),
                                                  backgroundColor: const Color(0xFFFEF2F2),
                                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                                  minimumSize: Size.zero,
                                                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                                  textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                                                ),
                                              ),
                                              FilledButton.icon(
                                                onPressed: () => _handleVerifyDocument(doc, 'approve'),
                                                icon: const Icon(Icons.check_rounded, size: 13),
                                                label: const Text('Approve Doc'),
                                                style: FilledButton.styleFrom(
                                                  backgroundColor: const Color(0xFF059669),
                                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                                  minimumSize: Size.zero,
                                                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                                  textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800),
                                                ),
                                              ),
                                            ],
                                          ),
                                      ],
                                    ],
                                  ),
                                ],
                              ),
                            );
                          }),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    if (_application.correctionNotes.isNotEmpty || _application.rejectionNotes.isNotEmpty)
                      _SectionBox(
                        title: 'AUDIT NOTES & DECISION LOG',
                        icon: Icons.history_edu_rounded,
                        iconColor: const Color(0xFFDC2626),
                        children: [
                          if (_application.correctionNotes.isNotEmpty) ...[
                            const Text(
                              'Correction Instructions Sent:',
                              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF9A3412)),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              _application.correctionNotes,
                              style: const TextStyle(fontSize: 11.5, color: Color(0xFF334155)),
                            ),
                            const SizedBox(height: 8),
                          ],
                          if (_application.rejectionNotes.isNotEmpty) ...[
                            const Text(
                              'Rejection Reason:',
                              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF991B1B)),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              _application.rejectionNotes,
                              style: const TextStyle(fontSize: 11.5, color: Color(0xFF334155)),
                            ),
                          ],
                        ],
                      ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  border: Border(top: BorderSide(color: Color(0xFFE2E8F0))),
                ),
                child: SafeArea(
                  top: false,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (!isDecided) ...[
                        LayoutBuilder(
                          builder: (context, constraints) {
                            if (constraints.maxWidth < 360) {
                              return Column(
                                mainAxisSize: MainAxisSize.min,
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  FilledButton.icon(
                                    onPressed: _onFinalApprovePressed,
                                    icon: const Icon(Icons.check_circle_outline_rounded, size: 16),
                                    label: const Text('Approve Application'),
                                    style: FilledButton.styleFrom(
                                      backgroundColor: isReadyForApproval
                                          ? const Color(0xFF059669)
                                          : const Color(0xFF004E89),
                                      padding: const EdgeInsets.symmetric(vertical: 10),
                                      textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800),
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Row(
                                    children: [
                                      Expanded(
                                        child: OutlinedButton.icon(
                                          onPressed: widget.onRequestCorrection,
                                          icon: const Icon(Icons.edit_note_rounded, size: 16),
                                          label: const Text('Corrections'),
                                          style: OutlinedButton.styleFrom(
                                            foregroundColor: const Color(0xFFD97706),
                                            side: const BorderSide(color: Color(0xFFFCD34D)),
                                            backgroundColor: const Color(0xFFFFFBEB),
                                            padding: const EdgeInsets.symmetric(vertical: 10),
                                            textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: OutlinedButton.icon(
                                          onPressed: widget.onReject,
                                          icon: const Icon(Icons.cancel_outlined, size: 16),
                                          label: const Text('Reject'),
                                          style: OutlinedButton.styleFrom(
                                            foregroundColor: const Color(0xFFDC2626),
                                            side: const BorderSide(color: Color(0xFFFECDD3)),
                                            backgroundColor: const Color(0xFFFEF2F2),
                                            padding: const EdgeInsets.symmetric(vertical: 10),
                                            textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              );
                            }
                            return Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton.icon(
                                    onPressed: widget.onRequestCorrection,
                                    icon: const Icon(Icons.edit_note_rounded, size: 16),
                                    label: const Text('Corrections'),
                                    style: OutlinedButton.styleFrom(
                                      foregroundColor: const Color(0xFFD97706),
                                      side: const BorderSide(color: Color(0xFFFCD34D)),
                                      backgroundColor: const Color(0xFFFFFBEB),
                                      padding: const EdgeInsets.symmetric(vertical: 10),
                                      textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: OutlinedButton.icon(
                                    onPressed: widget.onReject,
                                    icon: const Icon(Icons.cancel_outlined, size: 16),
                                    label: const Text('Reject'),
                                    style: OutlinedButton.styleFrom(
                                      foregroundColor: const Color(0xFFDC2626),
                                      side: const BorderSide(color: Color(0xFFFECDD3)),
                                      backgroundColor: const Color(0xFFFEF2F2),
                                      padding: const EdgeInsets.symmetric(vertical: 10),
                                      textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  flex: 2,
                                  child: FilledButton.icon(
                                    onPressed: _onFinalApprovePressed,
                                    icon: const Icon(Icons.check_circle_outline_rounded, size: 16),
                                    label: const Text('Approve Application'),
                                    style: FilledButton.styleFrom(
                                      backgroundColor: isReadyForApproval
                                          ? const Color(0xFF059669)
                                          : const Color(0xFF004E89),
                                      padding: const EdgeInsets.symmetric(vertical: 10),
                                      textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800),
                                    ),
                                  ),
                                ),
                              ],
                            );
                          },
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildPrerequisitesCard({
    required bool hasApprovedService,
    required bool hasAllDocsApproved,
    required bool isReady,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: isReady ? const Color(0xFFF0FDF4) : const Color(0xFFFFFBEB),
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(
          color: isReady ? const Color(0xFF86EFAC) : const Color(0xFFFDE68A),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isReady ? Icons.check_circle_rounded : Icons.pending_actions_rounded,
                size: 18,
                color: isReady ? const Color(0xFF059669) : const Color(0xFFD97706),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  isReady ? 'READY FOR ONBOARDING APPROVAL' : 'APPROVAL PREREQUISITES',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w900,
                    color: isReady ? const Color(0xFF059669) : const Color(0xFFB45309),
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          _buildPrerequisiteItem(
            title: 'Submitted Documents Verification',
            isSatisfied: hasAllDocsApproved,
            detail: hasAllDocsApproved
                ? 'All ${_application.verifiedDocumentsCount} document(s) verified & approved'
                : '${_application.pendingDocumentsCount} document(s) awaiting verification',
          ),
          const SizedBox(height: 6),
          _buildPrerequisiteItem(
            title: 'Trade Service Authorization',
            isSatisfied: hasApprovedService,
            detail: hasApprovedService
                ? '${_application.approvedServicesCount} service(s) authorized for dispatch'
                : 'No approved services (at least 1 required)',
          ),
          if (!isReady && (_application.pendingDocumentsCount > 0 || _application.pendingServicesCount > 0)) ...[
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _isBulkProcessing ? null : _handleQuickApproveAllPrerequisites,
                icon: const Icon(Icons.bolt_rounded, size: 16),
                label: Text(
                  _isBulkProcessing ? 'Approving Prerequisites...' : 'Quick Approve All Prerequisites',
                  style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800),
                ),
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF004E89),
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  static Widget _buildPrerequisiteItem({
    required String title,
    required bool isSatisfied,
    required String detail,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          isSatisfied ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
          size: 15,
          color: isSatisfied ? const Color(0xFF059669) : const Color(0xFFD97706),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w700,
                  color: isSatisfied ? const Color(0xFF0F172A) : const Color(0xFF78350F),
                ),
              ),
              Text(
                detail,
                style: TextStyle(
                  fontSize: 10.5,
                  color: isSatisfied ? const Color(0xFF059669) : const Color(0xFFB45309),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  static Widget _dataRow(String label, String value, {bool isMono = false, bool isBold = false, Color? highlightColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3.5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            flex: 2,
            child: Text(
              label,
              style: const TextStyle(fontSize: 11.5, color: Color(0xFF64748B)),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            flex: 3,
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: TextStyle(
                fontSize: 12,
                fontWeight: isBold ? FontWeight.w800 : FontWeight.w600,
                fontFamily: isMono ? 'monospace' : null,
                color: highlightColor ?? const Color(0xFF0F172A),
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionBox extends StatelessWidget {
  const _SectionBox({
    required this.title,
    required this.icon,
    required this.iconColor,
    required this.children,
    this.trailing,
  });

  final String title;
  final IconData icon;
  final Color iconColor;
  final List<Widget> children;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: iconColor),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF334155),
                    letterSpacing: 0.4,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (trailing != null) ...[
                const SizedBox(width: 6),
                trailing!,
              ],
            ],
          ),
          const SizedBox(height: 6),
          const Divider(height: 1),
          const SizedBox(height: 6),
          ...children,
        ],
      ),
    );
  }
}
