import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/status_chip.dart';
import '../../../../shared/widgets/workforce_avatar.dart';
import '../../data/admin_dashboard_api.dart';
import '../../domain/admin_application.dart';
import '../admin_dashboard_providers.dart';

/// Complete enterprise mobile dossier review for a single candidate/technician.
/// Implements full 7-tab review dossier (Overview, Registration, Services, Documents,
/// Experience & Skills, Bank Details, Audit History) with individual and bulk actions.
class AdminApplicationDetailScreen extends ConsumerStatefulWidget {
  const AdminApplicationDetailScreen({super.key, required this.applicationId});

  final int applicationId;

  @override
  ConsumerState<AdminApplicationDetailScreen> createState() =>
      _AdminApplicationDetailScreenState();
}

class _AdminApplicationDetailScreenState
    extends ConsumerState<AdminApplicationDetailScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isProcessing = false;
  String? _processingActionMsg;

  // Multi-selection state for Services and Documents
  final Set<int> _selectedServiceIds = {};
  final Set<String> _selectedDocCategories = {};

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 7, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
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
    ref.invalidate(adminApplicationDetailProvider(widget.applicationId));
    ref.invalidate(adminApplicationsListProvider(null));
    ref.invalidate(adminDashboardDataProvider);
    await ref.read(adminApplicationDetailProvider(widget.applicationId).future);
  }

  // ── Document Actions ────────────────────────────────────────────────────────

  Future<void> _viewDocument(String? urlString) async {
    if (urlString == null || urlString.isEmpty) {
      _showFeedback('Document file URL is not available.', isError: true);
      return;
    }
    try {
      final uri = Uri.parse(urlString);
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched && mounted) {
        _showFeedback('Could not open file in browser/viewer: $urlString', isError: true);
      }
    } catch (e) {
      if (mounted) {
        _showFeedback('Failed to open document: $e', isError: true);
      }
    }
  }

  Future<void> _handleDocAction(String category, String action) async {
    String reason = '';
    if (action == 'reject') {
      final reasonCtrl = TextEditingController();
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Reject Document'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Specify reason for rejecting document "${category.replaceAll('_', ' ')}":'),
              const SizedBox(height: 10),
              TextField(
                controller: reasonCtrl,
                decoration: const InputDecoration(
                  hintText: 'e.g. Blurry photo or unreadable text...',
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
        _showFeedback('A rejection reason is required.', isError: true);
        return;
      }
    }

    setState(() {
      _isProcessing = true;
      _processingActionMsg = action == 'approve' ? 'Approving document...' : 'Rejecting document...';
    });

    try {
      final res = await ref.read(adminDashboardApiProvider).verifyDocument(
            applicationId: widget.applicationId,
            docCategory: category,
            action: action,
            reason: reason,
          );
      _selectedDocCategories.remove(category);
      await _refreshDossier();
      final msg = res['message'] ?? 'Document marked as ${action}d.';
      _showFeedback(msg);
    } catch (e) {
      _showFeedback(_extractErrorMessage(e, 'Document verification failed.'), isError: true);
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Future<void> _handleBulkDocumentAction(String action, {bool allPending = false}) async {
    final targetCategories = allPending ? <String>[] : _selectedDocCategories.toList();
    if (!allPending && targetCategories.isEmpty) {
      _showFeedback('Please select at least one document.', isError: true);
      return;
    }

    String reason = '';
    if (action == 'reject') {
      final reasonCtrl = TextEditingController();
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Reject Selected Documents'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Enter specific reason for rejecting the selected document(s):'),
              const SizedBox(height: 10),
              TextField(
                controller: reasonCtrl,
                decoration: const InputDecoration(
                  hintText: 'e.g. Identification copy does not match applicant...',
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
              child: const Text('Confirm Rejection'),
            ),
          ],
        ),
      );

      if (confirmed != true) return;
      reason = reasonCtrl.text.trim();
      if (reason.isEmpty) {
        _showFeedback('A rejection reason is required.', isError: true);
        return;
      }
    }

    setState(() {
      _isProcessing = true;
      _processingActionMsg = 'Processing ${action}d documents in bulk...';
    });

    try {
      final res = await ref.read(adminDashboardApiProvider).bulkVerifyDocuments(
            applicationId: widget.applicationId,
            categories: targetCategories,
            action: action,
            reason: reason,
            allPending: allPending,
          );
      _selectedDocCategories.clear();
      await _refreshDossier();
      final msg = res['message'] ?? 'Documents ${action}d successfully.';
      _showFeedback(msg);
    } catch (e) {
      _showFeedback(_extractErrorMessage(e, 'Bulk document $action failed.'), isError: true);
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  // ── Service Actions ─────────────────────────────────────────────────────────

  Future<void> _handleServiceAction(int serviceId, String action) async {
    String reason = '';
    if (action == 'reject') {
      final reasonCtrl = TextEditingController();
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Reject Service Authorization'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Enter reason for declining this service authorization:'),
              const SizedBox(height: 10),
              TextField(
                controller: reasonCtrl,
                decoration: const InputDecoration(
                  hintText: 'e.g. Candidate does not meet trade certification...',
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
    }

    setState(() {
      _isProcessing = true;
      _processingActionMsg = action == 'approve' ? 'Authorizing service...' : 'Rejecting service...';
    });

    try {
      final res = await ref.read(adminDashboardApiProvider).decideService(
            employeeId: widget.applicationId,
            serviceId: serviceId,
            action: action,
            reason: reason,
          );
      _selectedServiceIds.remove(serviceId);
      await _refreshDossier();
      final msg = res['message'] ?? 'Service ${action}d successfully.';
      _showFeedback(msg);
    } catch (e) {
      _showFeedback(_extractErrorMessage(e, 'Service authorization update failed.'), isError: true);
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Future<void> _handleBulkServiceAction(String action, {bool allPending = false}) async {
    final targetIds = allPending ? <int>[] : _selectedServiceIds.toList();
    if (!allPending && targetIds.isEmpty) {
      _showFeedback('Please select at least one service.', isError: true);
      return;
    }

    String reason = '';
    if (action == 'reject') {
      final reasonCtrl = TextEditingController();
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Reject Selected Services'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Enter reason for declining selected service authorizations:'),
              const SizedBox(height: 10),
              TextField(
                controller: reasonCtrl,
                decoration: const InputDecoration(
                  hintText: 'e.g. Staffing quota full or missing equipment...',
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
              child: const Text('Confirm Rejection'),
            ),
          ],
        ),
      );

      if (confirmed != true) return;
      reason = reasonCtrl.text.trim();
    }

    setState(() {
      _isProcessing = true;
      _processingActionMsg = 'Processing ${action}d services in bulk...';
    });

    try {
      final res = await ref.read(adminDashboardApiProvider).bulkDecideServices(
            applicationId: widget.applicationId,
            serviceIds: targetIds,
            action: action,
            reason: reason,
            allPending: allPending,
          );
      _selectedServiceIds.clear();
      await _refreshDossier();
      final msg = res['message'] ?? 'Services ${action}d successfully.';
      _showFeedback(msg);
    } catch (e) {
      _showFeedback(_extractErrorMessage(e, 'Bulk service $action failed.'), isError: true);
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  // ── Final Application Decision Actions ──────────────────────────────────────

  Future<void> _handleFinalApprove(AdminApplication app) async {
    // Check local prerequisite warnings for immediate helpful feedback
    final unapprovedDocs = app.documentsList.where((d) => !d.isApproved).map((d) => d.title).toList();
    final hasApprovedService = app.allRequestedServices.any((s) => s.isApproved);

    if (unapprovedDocs.isNotEmpty || !hasApprovedService) {
      final proceed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: Color(0xFFD97706), size: 24),
              SizedBox(width: 8),
              Text('Approval Notice'),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'The backend requires all submitted documents to be verified and at least one service to be approved before final approval.',
                style: TextStyle(fontSize: 13),
              ),
              const SizedBox(height: 12),
              if (unapprovedDocs.isNotEmpty) ...[
                const Text('Unapproved Documents:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                ...unapprovedDocs.map((d) => Text(' • $d', style: const TextStyle(fontSize: 11.5, color: Color(0xFFDC2626)))),
                const SizedBox(height: 8),
              ],
              if (!hasApprovedService) ...[
                const Text('• No services are currently approved.', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Color(0xFFDC2626))),
                const SizedBox(height: 8),
              ],
              const Text(
                'Would you like to proceed with approval attempt anyway?',
                style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Review Items First'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFF059669)),
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Proceed'),
            ),
          ],
        ),
      );
      if (proceed != true) return;
    } else {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Approve Technician?'),
          content: Text(
            'Are you sure you want to approve ${app.name}? They will be authorized for workforce operations and ready for field dispatch.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFF059669)),
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Approve Technician'),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
    }

    setState(() {
      _isProcessing = true;
      _processingActionMsg = 'Approving technician for operations...';
    });

    try {
      final res = await ref.read(adminDashboardApiProvider).approveApplication(widget.applicationId);
      await _refreshDossier();
      final msg = res['message'] ?? 'Technician approved! Status is now OFFLINE (ready for field dispatch).';
      _showFeedback(msg);
    } catch (e) {
      _showFeedback(_extractErrorMessage(e, 'Approval failed. Verify all documents and at least 1 service are approved.'), isError: true);
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Future<void> _handleRequestCorrection() async {
    final notesController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Request Application Correction'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Enter specific instructions for the technician. They will be notified to correct flagged documents/fields and resubmit.',
              style: TextStyle(fontSize: 12.5, color: Color(0xFF475569)),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: notesController,
              decoration: const InputDecoration(
                hintText: 'e.g. Aadhaar card photo is blurry. Please re-upload clear front & back photos.',
                border: OutlineInputBorder(),
              ),
              maxLines: 4,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFD97706)),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Send Request'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final notes = notesController.text.trim();
      if (notes.isEmpty) {
        _showFeedback('Please enter correction notes.', isError: true);
        return;
      }
      setState(() {
        _isProcessing = true;
        _processingActionMsg = 'Dispatching correction request...';
      });
      try {
        await ref
            .read(adminDashboardApiProvider)
            .requestCorrection(widget.applicationId, notes: notes);
        await _refreshDossier();
        _showFeedback('Correction request dispatched to technician.');
      } catch (e) {
        _showFeedback(_extractErrorMessage(e, 'Failed to request corrections.'), isError: true);
      } finally {
        if (mounted) setState(() => _isProcessing = false);
      }
    }
  }

  Future<void> _handleFinalReject() async {
    final reasonController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Reject Candidate Application'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Provide formal rationale for declining this applicant:',
              style: TextStyle(fontSize: 12.5, color: Color(0xFF475569)),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: reasonController,
              decoration: const InputDecoration(
                hintText: 'e.g. Candidate does not meet trade certification standards.',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
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
            child: const Text('Confirm Rejection'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final reason = reasonController.text.trim();
      setState(() {
        _isProcessing = true;
        _processingActionMsg = 'Rejecting application...';
      });
      try {
        await ref
            .read(adminDashboardApiProvider)
            .rejectApplication(widget.applicationId, reason: reason);
        await _refreshDossier();
        _showFeedback('Candidate application rejected.');
      } catch (e) {
        _showFeedback(_extractErrorMessage(e, 'Rejection failed.'), isError: true);
      } finally {
        if (mounted) setState(() => _isProcessing = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(adminApplicationDetailProvider(widget.applicationId));

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFF0A2540), // Deep Peacock Navy
                Color(0xFF004E89), // Peacock Blue
              ],
            ),
          ),
        ),
        title: Text(
          'Dossier #${widget.applicationId}',
          style: const TextStyle(fontWeight: FontWeight.w800, color: Colors.white, fontSize: 16),
        ),
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.white),
            tooltip: 'Refresh Dossier',
            onPressed: _isProcessing ? null : _refreshDossier,
          ),
        ],
      ),
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline_rounded, color: Color(0xFFDC2626), size: 40),
                const SizedBox(height: 12),
                Text('Failed to load dossier: $err', textAlign: TextAlign.center),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _refreshDossier,
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
        data: (app) {
          final isDecided = app.isApproved || app.isRejected;

          return Column(
            children: [
              // ── Header Summary Card with Final Action Bar ─────────────────
              _buildTopSummaryBanner(app),

              // ── Tab Bar (7 Dossier Sections) ──────────────────────────────
              Container(
                color: Colors.white,
                child: TabBar(
                  controller: _tabController,
                  isScrollable: true,
                  labelColor: const Color(0xFF004E89),
                  unselectedLabelColor: const Color(0xFF64748B),
                  indicatorColor: const Color(0xFF004E89),
                  indicatorWeight: 3,
                  labelStyle: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800),
                  tabAlignment: TabAlignment.start,
                  tabs: [
                    const Tab(
                      icon: Icon(Icons.person_outline_rounded, size: 18),
                      text: 'Overview',
                    ),
                    const Tab(
                      icon: Icon(Icons.description_outlined, size: 18),
                      text: 'Registration',
                    ),
                    Tab(
                      icon: const Icon(Icons.handyman_outlined, size: 18),
                      child: Row(
                        children: [
                          const Text('Services'),
                          const SizedBox(width: 4),
                          _badge(app.requestedServicesCount.toString(),
                              color: const Color(0xFFEFF6FF), textColor: const Color(0xFF004E89)),
                        ],
                      ),
                    ),
                    Tab(
                      icon: const Icon(Icons.shield_outlined, size: 18),
                      child: Row(
                        children: [
                          const Text('Documents'),
                          const SizedBox(width: 4),
                          _badge(app.uploadedDocumentsCount.toString(),
                              color: const Color(0xFFEFF6FF), textColor: const Color(0xFF004E89)),
                        ],
                      ),
                    ),
                    const Tab(
                      icon: Icon(Icons.military_tech_outlined, size: 18),
                      text: 'Experience & Skills',
                    ),
                    const Tab(
                      icon: Icon(Icons.account_balance_outlined, size: 18),
                      text: 'Bank Details',
                    ),
                    const Tab(
                      icon: Icon(Icons.history_rounded, size: 18),
                      text: 'Audit History',
                    ),
                  ],
                ),
              ),

              // ── Action Loading Banner ─────────────────────────────────────
              if (_isProcessing)
                Container(
                  color: const Color(0xFFEFF6FF),
                  padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF2563EB)),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        _processingActionMsg ?? 'Processing request...',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF1E40AF)),
                      ),
                    ],
                  ),
                ),

              // ── Tab Views ──────────────────────────────────────────────────
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildOverviewTab(app),
                    _buildRegistrationTab(app),
                    _buildServicesTab(app),
                    _buildDocumentsTab(app),
                    _buildExperienceTab(app),
                    _buildBankDetailsTab(app),
                    _buildAuditHistoryTab(app),
                  ],
                ),
              ),

              // ── Bottom Fixed Action Bar (if pending / under review) ─────────
              if (!isDecided) _buildBottomDecisionBar(app),
            ],
          );
        },
      ),
    );
  }

  Widget _badge(String text, {required Color color, required Color textColor}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 5.5, vertical: 1),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 10.5,
          fontWeight: FontWeight.w800,
          color: textColor,
        ),
      ),
    );
  }

  // ── Top Summary Card ────────────────────────────────────────────────────────

  Widget _buildTopSummaryBanner(AdminApplication app) {
    final approvedServices = app.allRequestedServices.where((s) => s.isApproved).length;
    final totalServices = app.allRequestedServices.length;
    final approvedDocs = app.documentsList.where((d) => d.isApproved).length;
    final totalDocs = app.documentsList.length;

    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              WorkforceAvatar(
                imageUrl: app.avatar,
                name: app.name,
                initial: app.initial,
                radius: 24,
                fontSize: 18,
                backgroundColor: const Color(0xFF004E89).withValues(alpha: 0.1),
                foregroundColor: const Color(0xFF004E89),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            app.name ?? 'Technician #${app.id}',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Color(0xFF0F172A)),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                        StatusChip(status: app.registrationStatus, dense: true),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'ID: ${app.employeeId ?? 'PENDING'}${app.phone != null ? ' • ${app.phone}' : ''}${app.email != null ? ' • ${app.email}' : ''}',
                      style: const TextStyle(
                        fontSize: 11,
                        fontFamily: 'monospace',
                        color: Color(0xFF64748B),
                        fontWeight: FontWeight.w600,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          // Verification Readiness Posture Pills
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4.5),
                  decoration: BoxDecoration(
                    color: approvedServices > 0 ? const Color(0xFFECFDF5) : const Color(0xFFFFFBEB),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: approvedServices > 0 ? const Color(0xFFA7F3D0) : const Color(0xFFFDE68A),
                      width: 0.8,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        approvedServices > 0 ? Icons.check_circle_rounded : Icons.pending_rounded,
                        size: 13,
                        color: approvedServices > 0 ? const Color(0xFF059669) : const Color(0xFFD97706),
                      ),
                      const SizedBox(width: 5),
                      Flexible(
                        child: Text(
                          'Services: $approvedServices/$totalServices Authorized',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: approvedServices > 0 ? const Color(0xFF065F46) : const Color(0xFF92400E),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4.5),
                  decoration: BoxDecoration(
                    color: (totalDocs > 0 && approvedDocs == totalDocs)
                        ? const Color(0xFFECFDF5)
                        : (app.pendingDocumentsCount > 0 ? const Color(0xFFFEF3C7) : const Color(0xFFF1F5F9)),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: (totalDocs > 0 && approvedDocs == totalDocs)
                          ? const Color(0xFFA7F3D0)
                          : const Color(0xFFE2E8F0),
                      width: 0.8,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        (totalDocs > 0 && approvedDocs == totalDocs)
                            ? Icons.verified_rounded
                            : Icons.description_outlined,
                        size: 13,
                        color: (totalDocs > 0 && approvedDocs == totalDocs)
                            ? const Color(0xFF059669)
                            : const Color(0xFF475569),
                      ),
                      const SizedBox(width: 5),
                      Flexible(
                        child: Text(
                          'Docs: $approvedDocs/$totalDocs Verified',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: (totalDocs > 0 && approvedDocs == totalDocs)
                                ? const Color(0xFF065F46)
                                : const Color(0xFF334155),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ── TAB 1: OVERVIEW ─────────────────────────────────────────────────────────

  Widget _buildOverviewTab(AdminApplication app) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: [
        // Candidate Details Card
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.person_pin_rounded, color: Color(0xFF2563EB), size: 18),
                  SizedBox(width: 8),
                  Text(
                    'CANDIDATE DETAILS',
                    style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF334155), letterSpacing: 0.5),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              const Divider(height: 1),
              const SizedBox(height: AppSpacing.sm),
              _dataRow('Phone', app.phone ?? '—', isMono: true),
              _dataRow('Email', app.email ?? '—'),
              _dataRow('City / Territory', app.city),
              _dataRow('Service Radius', app.serviceRadius, isBold: true, highlightColor: const Color(0xFF2563EB)),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),

        // Services Summary Card
        Container(
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
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.handyman_outlined, color: Color(0xFF059669), size: 18),
                      SizedBox(width: 8),
                      Text(
                        'SERVICES SUMMARY',
                        style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF334155), letterSpacing: 0.5),
                      ),
                    ],
                  ),
                  TextButton(
                    onPressed: () => _tabController.animateTo(2),
                    style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
                    child: const Text('Review Services →', style: TextStyle(fontSize: 11.5)),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              const Divider(height: 1),
              const SizedBox(height: AppSpacing.sm),
              _dataRow('Requested Services', '${app.requestedServicesCount} services'),
              _dataRow('Approved Services', '${app.approvedServicesCount}',
                  highlightColor: const Color(0xFF059669), isBold: true),
              _dataRow('Pending Authorization', '${app.pendingServicesCount}',
                  highlightColor: const Color(0xFFD97706), isBold: true),
              if (app.rejectedServicesCount > 0)
                _dataRow('Declined Services', '${app.rejectedServicesCount}',
                    highlightColor: const Color(0xFFDC2626), isBold: true),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),

        // Documents Summary Card
        Container(
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
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.shield_outlined, color: Color(0xFF2563EB), size: 18),
                      SizedBox(width: 8),
                      Text(
                        'DOCUMENTS LODGED',
                        style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF334155), letterSpacing: 0.5),
                      ),
                    ],
                  ),
                  TextButton(
                    onPressed: () => _tabController.animateTo(3),
                    style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
                    child: const Text('Review Docs →', style: TextStyle(fontSize: 11.5)),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              const Divider(height: 1),
              const SizedBox(height: AppSpacing.sm),
              _dataRow('Total Uploads', '${app.uploadedDocumentsCount} files'),
              _dataRow('Verified & Approved', '${app.verifiedDocumentsCount}',
                  highlightColor: const Color(0xFF059669), isBold: true),
              _dataRow('Pending Review', '${app.pendingDocumentsCount}',
                  highlightColor: const Color(0xFFD97706), isBold: true),
              if (app.rejectedDocumentsCount > 0)
                _dataRow('Rejected / Flagged', '${app.rejectedDocumentsCount}',
                    highlightColor: const Color(0xFFDC2626), isBold: true),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }

  // ── TAB 2: REGISTRATION DETAILS ─────────────────────────────────────────────

  Widget _buildRegistrationTab(AdminApplication app) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: [
        // Personal Information
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.badge_outlined, color: Color(0xFF2563EB), size: 18),
                  SizedBox(width: 8),
                  Text(
                    'PERSONAL INFORMATION',
                    style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF334155), letterSpacing: 0.5),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              const Divider(height: 1),
              const SizedBox(height: AppSpacing.sm),
              _dataRow('Date of Birth', app.dob),
              _dataRow('Gender', app.gender),
              _dataRow('Emergency Contact', app.emergencyName),
              _dataRow('Emergency Phone', app.emergencyPhone, isMono: true),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),

        // Address & Dispatch Territory
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.map_outlined, color: Color(0xFF059669), size: 18),
                  SizedBox(width: 8),
                  Text(
                    'ADDRESS & DISPATCH TERRITORY',
                    style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF334155), letterSpacing: 0.5),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              const Divider(height: 1),
              const SizedBox(height: AppSpacing.sm),
              _dataRow('Street Address', app.streetAddress),
              _dataRow('City / State', '${app.city}, ${app.state}'),
              _dataRow('Pincode', app.pincode, isMono: true),
              _dataRow('Max Dispatch Radius', app.serviceRadius, isBold: true, highlightColor: const Color(0xFF2563EB)),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }

  // ── TAB 3: SERVICES AUTHORIZATION MATRIX (Critical) ─────────────────────────

  Widget _buildServicesTab(AdminApplication app) {
    final services = app.allRequestedServices;
    final allPending = services.where((s) => s.isPending).toList();
    final allSelected = services.isNotEmpty && _selectedServiceIds.length == services.length;

    return ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: [
        // Matrix Information & Bulk Control Header
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'PER-SERVICE AUTHORIZATION MATRIX',
                style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF1E293B), letterSpacing: 0.5),
              ),
              const SizedBox(height: 2),
              const Text(
                'Technicians can ONLY be dispatched jobs for services explicitly marked as APPROVED.',
                style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
              ),
              const SizedBox(height: AppSpacing.sm),
              const Divider(height: 1),
              const SizedBox(height: AppSpacing.sm),

              // Bulk Controls
              Wrap(
                spacing: 8,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  if (_selectedServiceIds.isNotEmpty) ...[
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEFF6FF),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: const Color(0xFFBFDBFE)),
                      ),
                      child: Text(
                        '${_selectedServiceIds.length} Selected',
                        style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF2563EB)),
                      ),
                    ),
                    FilledButton.icon(
                      onPressed: _isProcessing ? null : () => _handleBulkServiceAction('approve'),
                      icon: const Icon(Icons.check_circle_outline_rounded, size: 15),
                      label: Text('Approve (${_selectedServiceIds.length})'),
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFF059669),
                        visualDensity: VisualDensity.compact,
                        textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                      ),
                    ),
                    FilledButton.icon(
                      onPressed: _isProcessing ? null : () => _handleBulkServiceAction('reject'),
                      icon: const Icon(Icons.cancel_outlined, size: 15),
                      label: Text('Reject (${_selectedServiceIds.length})'),
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFFDC2626),
                        visualDensity: VisualDensity.compact,
                        textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                      ),
                    ),
                  ] else ...[
                    if (allPending.isNotEmpty) ...[
                      OutlinedButton.icon(
                        onPressed: _isProcessing ? null : () => _handleBulkServiceAction('approve', allPending: true),
                        icon: const Icon(Icons.done_all_rounded, size: 15, color: Color(0xFF059669)),
                        label: Text('Approve All Pending (${allPending.length})', style: const TextStyle(fontSize: 11.5, color: Color(0xFF059669), fontWeight: FontWeight.w700)),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Color(0xFFA7F3D0)),
                          backgroundColor: const Color(0xFFECFDF5),
                          visualDensity: VisualDensity.compact,
                        ),
                      ),
                      OutlinedButton.icon(
                        onPressed: _isProcessing ? null : () => _handleBulkServiceAction('reject', allPending: true),
                        icon: const Icon(Icons.remove_circle_outline_rounded, size: 15, color: Color(0xFFDC2626)),
                        label: Text('Reject All Pending (${allPending.length})', style: const TextStyle(fontSize: 11.5, color: Color(0xFFDC2626), fontWeight: FontWeight.w700)),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Color(0xFFFECDD3)),
                          backgroundColor: const Color(0xFFFFF1F2),
                          visualDensity: VisualDensity.compact,
                        ),
                      ),
                    ],
                  ],
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.sm),

        // Select All Header Bar
        if (services.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
            child: Row(
              children: [
                Checkbox(
                  value: allSelected,
                  activeColor: const Color(0xFF2563EB),
                  onChanged: (val) {
                    setState(() {
                      if (allSelected) {
                        _selectedServiceIds.clear();
                      } else {
                        _selectedServiceIds.addAll(services.map((s) => s.id));
                      }
                    });
                  },
                ),
                Text(
                  allSelected ? 'Deselect All Services' : 'Select All Services (${services.length})',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF475569)),
                ),
              ],
            ),
          ),

        // Service List
        if (services.isEmpty)
          Container(
            padding: const EdgeInsets.all(AppSpacing.xl),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(AppRadius.card),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: const Center(
              child: Text(
                'No services requested in this application dossier.',
                style: TextStyle(fontSize: 12.5, color: Color(0xFF94A3B8)),
              ),
            ),
          )
        else
          ...services.map((svc) {
            final isChecked = _selectedServiceIds.contains(svc.id);
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isChecked ? const Color(0xFFEFF6FF).withValues(alpha: 0.5) : Colors.white,
                borderRadius: BorderRadius.circular(AppRadius.card),
                border: Border.all(
                  color: isChecked ? const Color(0xFF93C5FD) : const Color(0xFFE2E8F0),
                  width: isChecked ? 1.5 : 1.0,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Checkbox(
                        value: isChecked,
                        activeColor: const Color(0xFF2563EB),
                        onChanged: (val) {
                          setState(() {
                            if (val == true) {
                              _selectedServiceIds.add(svc.id);
                            } else {
                              _selectedServiceIds.remove(svc.id);
                            }
                          });
                        },
                      ),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              svc.name,
                              style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: Color(0xFF0F172A)),
                            ),
                            const SizedBox(height: 1),
                            Text(
                              'Category: ${svc.category ?? 'General'} • ID: #${svc.id}',
                              style: const TextStyle(fontSize: 11, color: Color(0xFF64748B), fontFamily: 'monospace'),
                            ),
                          ],
                        ),
                      ),
                      StatusChip(status: svc.status, dense: true),
                    ],
                  ),
                  if (svc.rejectionReason != null && svc.rejectionReason!.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Padding(
                      padding: const EdgeInsets.only(left: 48),
                      child: Text(
                        'Reason: ${svc.rejectionReason}',
                        style: const TextStyle(fontSize: 11, color: Color(0xFFDC2626), fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                  const SizedBox(height: 6),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      FilledButton(
                        onPressed: _isProcessing || svc.isApproved
                            ? null
                            : () => _handleServiceAction(svc.id, 'approve'),
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFF059669),
                          disabledBackgroundColor: const Color(0xFFD1FAE5),
                          disabledForegroundColor: const Color(0xFF065F46),
                          visualDensity: VisualDensity.compact,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                          textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                        ),
                        child: Text(svc.isApproved ? 'Approved ✓' : 'Approve'),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton(
                        onPressed: _isProcessing || svc.isRejected
                            ? null
                            : () => _handleServiceAction(svc.id, 'reject'),
                        style: OutlinedButton.styleFrom(
                          side: BorderSide(color: svc.isRejected ? const Color(0xFFFECDD3) : const Color(0xFFFDA4AF)),
                          backgroundColor: svc.isRejected ? const Color(0xFFFFF1F2) : Colors.white,
                          foregroundColor: const Color(0xFFDC2626),
                          visualDensity: VisualDensity.compact,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                          textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                        ),
                        child: Text(svc.isRejected ? 'Rejected ✗' : 'Reject'),
                      ),
                    ],
                  ),
                ],
              ),
            );
          }),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }

  // ── TAB 4: DOCUMENTS VERIFICATION (Critical) ────────────────────────────────

  Widget _buildDocumentsTab(AdminApplication app) {
    final docs = app.documentsList;
    final allPending = docs.where((d) => d.isPending).toList();
    final allSelected = docs.isNotEmpty && _selectedDocCategories.length == docs.length;

    return ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: [
        // Matrix Information & Bulk Control Header
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'UPLOADED IDENTIFICATION & COMPLIANCE FILES',
                style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF1E293B), letterSpacing: 0.5),
              ),
              const SizedBox(height: 2),
              const Text(
                'Verify mandatory government IDs, trade qualifications, address proofs, and banking credentials.',
                style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
              ),
              const SizedBox(height: AppSpacing.sm),
              const Divider(height: 1),
              const SizedBox(height: AppSpacing.sm),

              // Bulk Controls
              Wrap(
                spacing: 8,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  if (_selectedDocCategories.isNotEmpty) ...[
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEFF6FF),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: const Color(0xFFBFDBFE)),
                      ),
                      child: Text(
                        '${_selectedDocCategories.length} Selected',
                        style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF2563EB)),
                      ),
                    ),
                    FilledButton.icon(
                      onPressed: _isProcessing ? null : () => _handleBulkDocumentAction('approve'),
                      icon: const Icon(Icons.check_circle_outline_rounded, size: 15),
                      label: Text('Approve (${_selectedDocCategories.length})'),
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFF059669),
                        visualDensity: VisualDensity.compact,
                        textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                      ),
                    ),
                    FilledButton.icon(
                      onPressed: _isProcessing ? null : () => _handleBulkDocumentAction('reject'),
                      icon: const Icon(Icons.cancel_outlined, size: 15),
                      label: Text('Reject (${_selectedDocCategories.length})'),
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFFDC2626),
                        visualDensity: VisualDensity.compact,
                        textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                      ),
                    ),
                  ] else ...[
                    if (allPending.isNotEmpty) ...[
                      OutlinedButton.icon(
                        onPressed: _isProcessing ? null : () => _handleBulkDocumentAction('approve', allPending: true),
                        icon: const Icon(Icons.done_all_rounded, size: 15, color: Color(0xFF059669)),
                        label: Text('Approve All Pending (${allPending.length})', style: const TextStyle(fontSize: 11.5, color: Color(0xFF059669), fontWeight: FontWeight.w700)),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Color(0xFFA7F3D0)),
                          backgroundColor: const Color(0xFFECFDF5),
                          visualDensity: VisualDensity.compact,
                        ),
                      ),
                      OutlinedButton.icon(
                        onPressed: _isProcessing ? null : () => _handleBulkDocumentAction('reject', allPending: true),
                        icon: const Icon(Icons.remove_circle_outline_rounded, size: 15, color: Color(0xFFDC2626)),
                        label: Text('Reject All Pending (${allPending.length})', style: const TextStyle(fontSize: 11.5, color: Color(0xFFDC2626), fontWeight: FontWeight.w700)),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Color(0xFFFECDD3)),
                          backgroundColor: const Color(0xFFFFF1F2),
                          visualDensity: VisualDensity.compact,
                        ),
                      ),
                    ],
                  ],
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.sm),

        // Select All Header Bar
        if (docs.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
            child: Row(
              children: [
                Checkbox(
                  value: allSelected,
                  activeColor: const Color(0xFF2563EB),
                  onChanged: (val) {
                    setState(() {
                      if (allSelected) {
                        _selectedDocCategories.clear();
                      } else {
                        _selectedDocCategories.addAll(docs.map((d) => d.category));
                      }
                    });
                  },
                ),
                Text(
                  allSelected ? 'Deselect All Documents' : 'Select All Documents (${docs.length})',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF475569)),
                ),
              ],
            ),
          ),

        // Documents List
        if (docs.isEmpty)
          Container(
            padding: const EdgeInsets.all(AppSpacing.xl),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(AppRadius.card),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: const Center(
              child: Text(
                'No documents uploaded in this application dossier.',
                style: TextStyle(fontSize: 12.5, color: Color(0xFF94A3B8)),
              ),
            ),
          )
        else
          ...docs.map((doc) {
            final isChecked = _selectedDocCategories.contains(doc.category);
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isChecked ? const Color(0xFFEFF6FF).withValues(alpha: 0.5) : Colors.white,
                borderRadius: BorderRadius.circular(AppRadius.card),
                border: Border.all(
                  color: isChecked ? const Color(0xFF93C5FD) : const Color(0xFFE2E8F0),
                  width: isChecked ? 1.5 : 1.0,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Checkbox(
                        value: isChecked,
                        activeColor: const Color(0xFF2563EB),
                        onChanged: (val) {
                          setState(() {
                            if (val == true) {
                              _selectedDocCategories.add(doc.category);
                            } else {
                              _selectedDocCategories.remove(doc.category);
                            }
                          });
                        },
                      ),
                      const Icon(Icons.file_present_rounded, color: Color(0xFF2563EB), size: 22),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              doc.title,
                              style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: Color(0xFF0F172A)),
                            ),
                            const SizedBox(height: 1),
                            Text(
                              'Category: ${doc.category.toUpperCase()}',
                              style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                            ),
                          ],
                        ),
                      ),
                      StatusChip(status: doc.status, dense: true),
                    ],
                  ),
                  if (doc.documentNumber != null && doc.documentNumber!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Padding(
                      padding: const EdgeInsets.only(left: 48),
                      child: Text(
                        'Document No: ${doc.documentNumber}',
                        style: const TextStyle(fontSize: 11.5, fontFamily: 'monospace', color: Color(0xFF334155)),
                      ),
                    ),
                  ],
                  if (doc.rejectionReason != null && doc.rejectionReason!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Padding(
                      padding: const EdgeInsets.only(left: 48),
                      child: Text(
                        'Rejection Flag: ${doc.rejectionReason}',
                        style: const TextStyle(fontSize: 11, color: Color(0xFFDC2626), fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      if (doc.fileUrl != null && doc.fileUrl!.isNotEmpty)
                        OutlinedButton.icon(
                          onPressed: () => _viewDocument(doc.fileUrl),
                          icon: const Icon(Icons.open_in_new_rounded, size: 14),
                          label: const Text('View File'),
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: Color(0xFFCBD5E1)),
                            visualDensity: VisualDensity.compact,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                          ),
                        ),
                      const SizedBox(width: 8),
                      FilledButton(
                        onPressed: _isProcessing || doc.isApproved
                            ? null
                            : () => _handleDocAction(doc.category, 'approve'),
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFF059669),
                          disabledBackgroundColor: const Color(0xFFD1FAE5),
                          disabledForegroundColor: const Color(0xFF065F46),
                          visualDensity: VisualDensity.compact,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                          textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                        ),
                        child: Text(doc.isApproved ? 'Verified ✓' : 'Verify'),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton(
                        onPressed: _isProcessing || doc.isRejected
                            ? null
                            : () => _handleDocAction(doc.category, 'reject'),
                        style: OutlinedButton.styleFrom(
                          side: BorderSide(color: doc.isRejected ? const Color(0xFFFECDD3) : const Color(0xFFFDA4AF)),
                          backgroundColor: doc.isRejected ? const Color(0xFFFFF1F2) : Colors.white,
                          foregroundColor: const Color(0xFFDC2626),
                          visualDensity: VisualDensity.compact,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                          textStyle: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                        ),
                        child: Text(doc.isRejected ? 'Rejected ✗' : 'Reject'),
                      ),
                    ],
                  ),
                ],
              ),
            );
          }),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }

  // ── TAB 5: EXPERIENCE & SKILLS ──────────────────────────────────────────────

  Widget _buildExperienceTab(AdminApplication app) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: [
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.military_tech_outlined, color: Color(0xFF2563EB), size: 18),
                  SizedBox(width: 8),
                  Text(
                    'PROFESSIONAL EXPERIENCE & EQUIPMENT',
                    style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF334155), letterSpacing: 0.5),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              const Divider(height: 1),
              const SizedBox(height: AppSpacing.sm),
              _dataRow('Years of Experience', app.experienceYears, isBold: true),
              _dataRow('Vehicle Transport', app.vehicleType.toUpperCase()),
              _dataRow('Driver License Number', app.licenseNumber, isMono: true),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }

  // ── TAB 6: BANK DETAILS ─────────────────────────────────────────────────────

  Widget _buildBankDetailsTab(AdminApplication app) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: [
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.account_balance_outlined, color: Color(0xFF059669), size: 18),
                  SizedBox(width: 8),
                  Text(
                    'DIRECT DEPOSIT & PAYOUT CREDENTIALS',
                    style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF334155), letterSpacing: 0.5),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              const Divider(height: 1),
              const SizedBox(height: AppSpacing.sm),
              _dataRow('Account Holder', app.bankAccountHolder),
              _dataRow('Account Number', app.maskedBankAccount, isMono: true, isBold: true),
              _dataRow('IFSC Code', app.bankIfsc.toUpperCase(), isMono: true, isBold: true),
              _dataRow('UPI ID', app.bankUpiId, isMono: true),
              const SizedBox(height: AppSpacing.md),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.lock_outline_rounded, size: 16, color: Color(0xFF64748B)),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Direct deposit credentials are encrypted and restricted to authorized workforce administrators.',
                        style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }

  // ── TAB 7: AUDIT HISTORY ────────────────────────────────────────────────────

  Widget _buildAuditHistoryTab(AdminApplication app) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: [
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.history_rounded, color: Color(0xFF2563EB), size: 18),
                  SizedBox(width: 8),
                  Text(
                    'DOSSIER AUDIT & VERIFICATION TIMELINE',
                    style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF334155), letterSpacing: 0.5),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              _timelineItem(
                step: '1',
                title: 'Application Submitted',
                subtitle: 'Candidate completed registration form and uploaded identification documents.',
                timestamp: app.createdAt != null
                    ? '${app.createdAt!.day}/${app.createdAt!.month}/${app.createdAt!.year}'
                    : 'Recorded',
                isActive: true,
              ),
              const SizedBox(height: AppSpacing.md),
              _timelineItem(
                step: '2',
                title: 'Current Status: ${app.registrationStatus.toUpperCase()}',
                subtitle: app.isApproved
                    ? 'Technician approved by admin ${app.approvedBy ?? ''} for field dispatch.'
                    : (app.isRejected
                        ? 'Application rejected: ${app.rejectionNotes}'
                        : (app.isCorrectionRequired
                            ? 'Correction requested: ${app.correctionNotes}'
                            : 'Registration dossier under administrative review.')),
                timestamp: app.approvedAt != null
                    ? '${app.approvedAt!.day}/${app.approvedAt!.month}/${app.approvedAt!.year}'
                    : 'Pending decision',
                isActive: app.isApproved,
                isPending: app.isPending,
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }

  // ── Bottom Fixed Decision Bar ───────────────────────────────────────────────

  Widget _buildBottomDecisionBar(AdminApplication app) {
    return Container(
      padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, AppSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 10,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _isProcessing ? null : _handleRequestCorrection,
                icon: const Icon(Icons.edit_note_rounded, size: 16),
                label: const Text('Correction'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFD97706),
                  side: const BorderSide(color: Color(0xFFFCD34D)),
                  backgroundColor: const Color(0xFFFEF3C7),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _isProcessing ? null : _handleFinalReject,
                icon: const Icon(Icons.cancel_outlined, size: 16),
                label: const Text('Reject'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFDC2626),
                  side: const BorderSide(color: Color(0xFFFECDD3)),
                  backgroundColor: const Color(0xFFFFF1F2),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              flex: 2,
              child: FilledButton.icon(
                onPressed: _isProcessing ? null : () => _handleFinalApprove(app),
                icon: const Icon(Icons.check_circle_outline_rounded, size: 17),
                label: const Text('Approve Technician'),
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF059669),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Helper Widgets ──────────────────────────────────────────────────────────

  Widget _dataRow(String label, String value, {bool isMono = false, bool isBold = false, Color? highlightColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: isBold ? FontWeight.w800 : FontWeight.w600,
                fontFamily: isMono ? 'monospace' : null,
                color: highlightColor ?? const Color(0xFF0F172A),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _timelineItem({
    required String step,
    required String title,
    required String subtitle,
    required String timestamp,
    bool isActive = false,
    bool isPending = false,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CircleAvatar(
          radius: 14,
          backgroundColor: isActive
              ? const Color(0xFF059669)
              : (isPending ? const Color(0xFFD97706) : const Color(0xFF94A3B8)),
          child: Text(
            step,
            style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Color(0xFF0F172A))),
                  Text(timestamp, style: const TextStyle(fontSize: 10.5, color: Color(0xFF94A3B8))),
                ],
              ),
              const SizedBox(height: 2),
              Text(subtitle, style: const TextStyle(fontSize: 11.5, color: Color(0xFF64748B))),
            ],
          ),
        ),
      ],
    );
  }
}
