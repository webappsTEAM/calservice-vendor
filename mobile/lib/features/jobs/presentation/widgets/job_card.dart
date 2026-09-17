import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_error.dart';
import '../../../../core/theme/app_theme.dart';
import '../../data/job_actions_repository.dart';
import '../../domain/job.dart';
import '../../domain/job_presentation.dart';
import '../jobs_providers.dart';
import 'category_helper.dart';
import 'job_customer_row.dart';
import 'job_status_badge.dart';

/// Classic, premium Workforce Job Card adhering to the design specification:
/// 1. Top Row: Service Category Icon + Name (left) | Status Badge (right)
/// 2. Second Row: Job Request ID (left) | Earnings & "Earn on finish" (right)
/// 3. Job Title with (+N other items) suffix
/// 4. Compact Info Rows: 📅 Date & Time | 📍 Location (with graceful overflow)
/// 5. Customer Section: Avatar initial + Name + Quick Call & Directions buttons
/// 6. Bottom Action Bar: Status-dependent actions (Accept / Decline / Continue / Completed / View Details)
class JobCard extends ConsumerStatefulWidget {
  const JobCard({
    super.key,
    required this.job,
    this.hasActiveJob = false,
  });

  final Job job;
  final bool hasActiveJob;

  @override
  ConsumerState<JobCard> createState() => _JobCardState();
}

class _JobCardState extends ConsumerState<JobCard> {
  bool _isAccepting = false;
  bool _isDeclining = false;
  String? _inlineError;

  Future<void> _refreshJobs() async {
    ref.invalidate(activeJobsProvider);
    ref.invalidate(completedJobsProvider);
    await Future.wait([
      ref.read(activeJobsProvider.future),
      ref.read(completedJobsProvider.future),
    ]);
  }

  Future<void> _accept() async {
    setState(() {
      _isAccepting = true;
      _inlineError = null;
    });

    try {
      await ref.read(jobActionsRepositoryProvider).acceptOffer(widget.job.id);
      await _refreshJobs();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Job offer accepted! Heading to customer site.'),
            backgroundColor: Color(0xFF059669),
          ),
        );
      }
    } on DioException catch (e) {
      final data = e.response?.data;
      final code = data is Map ? data['code'] as String? : null;
      String message;
      switch (code) {
        case 'JOB_ALREADY_ACCEPTED':
          message = 'This job was already accepted by another technician.';
          break;
        case 'OFFER_EXPIRED':
          message = 'This job offer has expired.';
          break;
        case 'EMPLOYEE_ALREADY_BUSY':
          message = 'You already have an active job in progress.';
          break;
        default:
          message = describeDioError(e, fallback: 'Failed to accept job offer.');
      }
      if (mounted) setState(() => _inlineError = message);
      if (code == 'JOB_ALREADY_ACCEPTED' || code == 'OFFER_EXPIRED') {
        await _refreshJobs();
      }
    } catch (_) {
      if (mounted) setState(() => _inlineError = 'Failed to accept job offer.');
    } finally {
      if (mounted) setState(() => _isAccepting = false);
    }
  }

  Future<void> _decline() async {
    final reason = await _showDeclineReasonModal(context);
    if (reason == null || !mounted) return;

    setState(() {
      _isDeclining = true;
      _inlineError = null;
    });

    try {
      await ref.read(jobActionsRepositoryProvider).rejectOffer(widget.job.id, reason);
      await _refreshJobs();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Job offer declined.')),
        );
      }
    } on DioException catch (e) {
      if (mounted) {
        setState(() => _inlineError = describeDioError(e, fallback: 'Failed to decline job offer.'));
      }
    } catch (_) {
      if (mounted) setState(() => _inlineError = 'Failed to decline job offer.');
    } finally {
      if (mounted) setState(() => _isDeclining = false);
    }
  }

  Future<String?> _showDeclineReasonModal(BuildContext context) {
    String selectedReason = 'Too far';
    String customReason = '';

    return showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.fromLTRB(
                AppSpacing.lg,
                AppSpacing.lg,
                AppSpacing.lg,
                MediaQuery.of(context).viewInsets.bottom + AppSpacing.lg,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.cancel_outlined, size: 20, color: Color(0xFFDC2626)),
                      const SizedBox(width: AppSpacing.sm),
                      Expanded(
                        child: Text(
                          'Decline Job Offer — ${widget.job.requestId}',
                          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, size: 20),
                        onPressed: () => Navigator.of(context).pop(),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  const Text(
                    'Please select a reason for declining this job offer. The system will dispatch the job to the next available professional.',
                    style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  ...[
                    'Too far',
                    'Busy / Heavy traffic',
                    'Vehicle issue',
                    'Service mismatch',
                    'Personal reason',
                    'Other',
                  ].map((reason) {
                    final isSelected = selectedReason == reason;
                    return InkWell(
                      onTap: () => setModalState(() => selectedReason = reason),
                      borderRadius: BorderRadius.circular(AppRadius.chip),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
                        child: Row(
                          children: [
                            Container(
                              width: 18,
                              height: 18,
                              margin: const EdgeInsets.only(right: 10, left: 4),
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: isSelected ? const Color(0xFFDC2626) : const Color(0xFF94A3B8),
                                  width: isSelected ? 5 : 1.5,
                                ),
                              ),
                            ),
                            Text(
                              reason,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                                color: const Color(0xFF1E293B),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                  if (selectedReason == 'Other') ...[
                    const SizedBox(height: AppSpacing.xs),
                    TextField(
                      autofocus: true,
                      onChanged: (val) => customReason = val,
                      decoration: const InputDecoration(
                        hintText: 'Specify reason...',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.lg),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: const Text('Keep Offer'),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: ElevatedButton(
                          onPressed: () {
                            final finalReason = selectedReason == 'Other'
                                ? (customReason.trim().isNotEmpty ? customReason.trim() : 'Other')
                                : selectedReason;
                            Navigator.of(context).pop(finalReason);
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFFDC2626),
                            foregroundColor: Colors.white,
                          ),
                          child: const Text('Confirm Decline'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final presentation = buildJobPresentation(widget.job, hasActiveJob: widget.hasActiveJob);
    final categoryName = widget.job.serviceCategory ?? 'Service Request';
    final categoryIcon = iconForCategory(widget.job.serviceCategory ?? widget.job.displayTitle);

    // Additional items suffix if cartData has > 1 items
    final extraItemsCount = widget.job.cartData.length > 1 ? widget.job.cartData.length - 1 : 0;
    final extraItemsSuffix = extraItemsCount > 0
        ? ' (+$extraItemsCount other item${extraItemsCount > 1 ? 's' : ''})'
        : '';

    // Formatted schedule text
    final scheduleText = widget.job.preferredDate != null && widget.job.preferredTime != null
        ? '${widget.job.preferredDate} • ${widget.job.preferredTime}'
        : (widget.job.preferredDate ?? widget.job.preferredTime ?? 'Flexible schedule');

    // Amount text
    final formattedAmount = widget.job.totalAmount != null
        ? '₹${widget.job.totalAmount! >= 1000 ? widget.job.totalAmount!.toStringAsFixed(2) : widget.job.totalAmount!.toStringAsFixed(0)}'
        : '₹—';

    final isOffer = presentation.isOffer;
    final isCompleted = widget.job.status.toLowerCase() == 'completed' ||
        presentation.state == JobPresentationState.completed;
    final isCancelled = ['cancelled', 'rejected', 'declined'].contains(widget.job.status.toLowerCase());
    final isInProgress = !isOffer && !isCompleted && !isCancelled;

    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.cardStandard),
        side: BorderSide(
          color: isOffer ? const Color(0xFFFBBF24) : AppColors.border,
          width: isOffer ? 1.4 : 1,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.cardStandard),
        onTap: () => context.push('/jobs/${widget.job.id}'),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // ── 1. Top Row: Category (Left) + Status Badge (Right) ─────────
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        Icon(categoryIcon, size: 16, color: AppColors.peacockBlue),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            categoryName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF334155),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  JobStatusBadge(
                    status: presentation.badgeStatus,
                    label: presentation.displayStatus,
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),

              // ── 2. Second Row: Job Request ID + Earnings Amount ────────────
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        widget.job.requestId,
                        style: const TextStyle(
                          fontSize: 13,
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF004E89),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        formattedAmount,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w900,
                          color: Color(0xFF0F172A),
                          fontFamily: 'monospace',
                          height: 1.1,
                        ),
                      ),
                      const SizedBox(height: 2),
                      const Text(
                        'Earn on finish',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF64748B),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 6),

              // ── 3. Job Title ───────────────────────────────────────────────
              Text.rich(
                TextSpan(
                  text: widget.job.displayTitle,
                  style: const TextStyle(
                    fontSize: 14.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0F172A),
                    height: 1.3,
                  ),
                  children: [
                    if (extraItemsSuffix.isNotEmpty)
                      TextSpan(
                        text: extraItemsSuffix,
                        style: const TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF2563EB),
                        ),
                      ),
                  ],
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: AppSpacing.sm),

              // ── 4. Information Section: Date/Time + Location ───────────────
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(AppRadius.chip),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.calendar_today_rounded, size: 13, color: Color(0xFF64748B)),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            scheduleText,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF334155),
                            ),
                          ),
                        ),
                      ],
                    ),
                    if (widget.job.address != null && widget.job.address!.isNotEmpty) ...[
                      const SizedBox(height: 5),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Padding(
                            padding: EdgeInsets.only(top: 1.5),
                            child: Icon(Icons.place_rounded, size: 13, color: Color(0xFF64748B)),
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              widget.job.address!,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 11.5,
                                color: Color(0xFF475569),
                                height: 1.3,
                              ),
                            ),
                          ),
                          if (widget.job.distanceKm != null) ...[
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                              decoration: BoxDecoration(
                                color: const Color(0xFFEFF6FF),
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: const Color(0xFFBFDBFE), width: 0.8),
                              ),
                              child: Text(
                                '${widget.job.distanceKm!.toStringAsFixed(1)} km',
                                style: const TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                  color: Color(0xFF1D4ED8),
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.sm),

              // ── 5. Customer Section ────────────────────────────────────────
              JobCustomerRow(job: widget.job),

              if (_inlineError != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _inlineError!,
                  style: const TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFFDC2626),
                  ),
                ),
              ],

              const SizedBox(height: AppSpacing.sm),
              const Divider(height: 1, color: Color(0xFFE2E8F0)),
              const SizedBox(height: AppSpacing.sm),

              // ── 6. Bottom Action Bar ───────────────────────────────────────
              _buildActionBar(
                context,
                isOffer: isOffer,
                isCompleted: isCompleted,
                isCancelled: isCancelled,
                isInProgress: isInProgress,
                amountText: formattedAmount,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionBar(
    BuildContext context, {
    required bool isOffer,
    required bool isCompleted,
    required bool isCancelled,
    required bool isInProgress,
    required String amountText,
  }) {
    if (isOffer) {
      return Row(
        children: [
          Expanded(
            flex: 1,
            child: OutlinedButton(
              onPressed: (_isAccepting || _isDeclining) ? null : _decline,
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFFDC2626),
                side: const BorderSide(color: Color(0xFFFECDD3)),
                backgroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 4),
                textStyle: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
              ),
              child: _isDeclining
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFFDC2626)),
                    )
                  : const FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text('Decline'),
                    ),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            flex: 2,
            child: ElevatedButton(
              onPressed: (_isAccepting || _isDeclining) ? null : _accept,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.peacockBlue,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 6),
                textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, letterSpacing: 0.3),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
                elevation: 0,
              ),
              child: _isAccepting
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text('Accept • $amountText'),
                    ),
            ),
          ),
        ],
      );
    }

    if (isCompleted) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          OutlinedButton.icon(
            onPressed: () => context.push('/jobs/${widget.job.id}'),
            icon: const Icon(Icons.visibility_outlined, size: 15),
            label: const FittedBox(fit: BoxFit.scaleDown, child: Text('View Details')),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.peacockNavy,
              side: const BorderSide(color: Color(0xFFCBD5E1)),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: const Color(0xFFECFDF5),
              borderRadius: BorderRadius.circular(AppRadius.chip),
              border: Border.all(color: const Color(0xFFA7F3D0)),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.check_circle_rounded, size: 14, color: Color(0xFF059669)),
                SizedBox(width: 4),
                Text(
                  'Completed',
                  style: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF065F46),
                  ),
                ),
              ],
            ),
          ),
        ],
      );
    }

    if (isCancelled) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          OutlinedButton(
            onPressed: () => context.push('/jobs/${widget.job.id}'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.textSecondary,
              side: const BorderSide(color: Color(0xFFCBD5E1)),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
            ),
            child: const FittedBox(fit: BoxFit.scaleDown, child: Text('View Details')),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(AppRadius.chip),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: const Text(
              'Cancelled',
              style: TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w700,
                color: Color(0xFF64748B),
              ),
            ),
          ),
        ],
      );
    }

    // In Progress / Accepted Job
    return Row(
      children: [
        Expanded(
          flex: 1,
          child: OutlinedButton(
            onPressed: () => context.push('/jobs/${widget.job.id}'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.peacockNavy,
              side: const BorderSide(color: Color(0xFFCBD5E1)),
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
              textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
            ),
            child: const FittedBox(fit: BoxFit.scaleDown, child: Text('View Details')),
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          flex: 1,
          child: ElevatedButton(
            onPressed: () => context.push('/jobs/${widget.job.id}'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.peacockNavy,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
              textStyle: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.chip)),
              elevation: 0,
            ),
            child: const FittedBox(
              fit: BoxFit.scaleDown,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('Continue Job'),
                  SizedBox(width: 4),
                  Icon(Icons.arrow_forward_rounded, size: 14),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
