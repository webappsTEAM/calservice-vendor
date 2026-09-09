import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/app_card.dart';
import '../../../../shared/widgets/empty_state.dart';
import '../../../../shared/widgets/workforce_app_bar.dart';
import '../../data/admin_dashboard_api.dart';
import '../../domain/admin_quotation.dart';
import '../widgets/admin_drawer.dart';
import 'admin_quotation_providers.dart';

/// Super Admin / SEVO Platform Quotation Approvals Screen.
///
/// Features two authorization queues:
/// 1. Awaiting SEVO Approval: Quotes accepted by the customer. Approving creates
///    the work booking and issues the commercial invoice.
/// 2. Held before sending: Quotes held by high-value threshold or structural clearance.
class AdminQuotationApprovalsScreen extends ConsumerStatefulWidget {
  const AdminQuotationApprovalsScreen({super.key});

  @override
  ConsumerState<AdminQuotationApprovalsScreen> createState() =>
      _AdminQuotationApprovalsScreenState();
}

class _AdminQuotationApprovalsScreenState
    extends ConsumerState<AdminQuotationApprovalsScreen> {
  String? _flashMessage;
  bool _isActionInProgress = false;
  int? _busyQuoteId;

  String _formatTimeAgo(DateTime? date) {
    if (date == null) return '';
    final diff = DateTime.now().difference(date);
    if (diff.inMinutes < 60) return '${diff.inMinutes.clamp(1, 60)}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }

  Future<void> _refresh() async {
    ref.invalidate(adminQuotesPendingApprovalProvider);
    ref.invalidate(adminQuotesPendingReviewProvider);
  }

  Future<void> _decideQuote({
    required AdminQuotation quote,
    required bool approve,
    required bool isPreSendTab,
  }) async {
    final verb = isPreSendTab
        ? (approve ? 'Release & send' : 'Reject')
        : (approve ? 'Approve' : 'Reject');

    String notes = '';
    if (!approve) {
      final reasonController = TextEditingController();
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.card),
          ),
          title: Text('$verb ${quote.quoteNumber}',
              style: const TextStyle(
                  fontSize: 16, fontWeight: FontWeight.w800)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Enter rejection reason (recorded in audit trail):',
                style: TextStyle(fontSize: 13, color: Color(0xFF475569)),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reasonController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Rejection Reason',
                  border: OutlineInputBorder(),
                  hintText: 'e.g. Scope discrepancy or rate card mismatch',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFDC2626),
              ),
              child: Text(verb),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
      notes = reasonController.text.trim();
    } else {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.card),
          ),
          title: Text('$verb ${quote.quoteNumber}?',
              style: const TextStyle(
                  fontSize: 16, fontWeight: FontWeight.w800)),
          content: Text(
            isPreSendTab
                ? 'Release quote proposal of ₹${quote.netPayable.toStringAsFixed(2)} to ${quote.customerName}?'
                : 'Approving this quotation will create the work booking and issue the invoice.',
            style: const TextStyle(fontSize: 13, color: Color(0xFF475569)),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF0F172A),
              ),
              child: Text(verb),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
    }

    setState(() {
      _isActionInProgress = true;
      _busyQuoteId = quote.id;
    });

    try {
      final api = ref.read(adminDashboardApiProvider);
      if (isPreSendTab) {
        await api.preSendReviewQuote(
          quote.id,
          action: approve ? 'APPROVE' : 'REJECT',
          notes: notes,
          reason: notes,
        );
        if (mounted) {
          setState(() {
            _flashMessage = approve
                ? '${quote.quoteNumber} released and sent to the customer.'
                : '${quote.quoteNumber} rejected.';
          });
        }
      } else {
        final res = await api.adminReviewQuote(
          quote.id,
          action: approve ? 'APPROVE' : 'REJECT',
          notes: notes,
          reason: notes,
        );
        if (mounted) {
          final invoice = res['invoice'];
          if (invoice is Map<String, dynamic> &&
              invoice['invoice_number'] != null) {
            final invNum = invoice['invoice_number'];
            final total = invoice['total_amount']?.toString() ??
                quote.totalAmount.toStringAsFixed(2);
            setState(() {
              _flashMessage =
                  '${quote.quoteNumber} approved. Invoice $invNum issued for ₹$total.';
            });
          } else {
            setState(() {
              _flashMessage = approve
                  ? '${quote.quoteNumber} approved and booking issued.'
                  : '${quote.quoteNumber} rejected.';
            });
          }
        }
      }
      await _refresh();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to $verb ${quote.quoteNumber}: $e'),
            backgroundColor: const Color(0xFFDC2626),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isActionInProgress = false;
          _busyQuoteId = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final activeTab = ref.watch(adminQuotationTabProvider);
    final isAcceptanceTab = activeTab == 'acceptance';

    final quotesAsync = isAcceptanceTab
        ? ref.watch(adminQuotesPendingApprovalProvider)
        : ref.watch(adminQuotesPendingReviewProvider);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: const WorkforceAppBar(
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _refresh,
          color: const Color(0xFF0F172A),
          child: ListView(
            padding: const EdgeInsets.all(AppSpacing.md),
            children: [
              // ── Screen Header ──────────────────────────────────────────────
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x040F172A),
                      blurRadius: 8,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 42,
                          height: 42,
                          decoration: BoxDecoration(
                            color: const Color(0xFF0F172A),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(
                            Icons.approval_rounded,
                            color: Colors.white,
                            size: 22,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Quotation Approvals',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF0F172A),
                                  letterSpacing: -0.2,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                isAcceptanceTab
                                    ? 'The customer has accepted. Approving creates the work booking and issues the invoice.'
                                    : 'Above the category review threshold, or needing structural clearance. Releasing sends the quote to the customer.',
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF64748B),
                                  height: 1.35,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    const Divider(height: 1, color: Color(0xFFF1F5F9)),
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        OutlinedButton.icon(
                          onPressed: _isActionInProgress ? null : _refresh,
                          icon: const Icon(Icons.refresh_rounded, size: 15),
                          label: const Text('Refresh'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF475569),
                            side: const BorderSide(color: Color(0xFFCBD5E1)),
                            visualDensity: VisualDensity.compact,
                            textStyle: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // ── Queue Filter Tabs ──────────────────────────────────────────
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    ChoiceChip(
                      label: const Text(
                        'Awaiting SEVO Approval',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                      ),
                      selected: isAcceptanceTab,
                      onSelected: (val) {
                        if (val) {
                          setState(() => _flashMessage = null);
                          ref.read(adminQuotationTabProvider.notifier).state =
                              'acceptance';
                        }
                      },
                      selectedColor: const Color(0xFF0F172A),
                      labelStyle: TextStyle(
                        color: isAcceptanceTab ? Colors.white : const Color(0xFF334155),
                      ),
                      backgroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                        side: BorderSide(
                          color: isAcceptanceTab
                              ? const Color(0xFF0F172A)
                              : const Color(0xFFE2E8F0),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    ChoiceChip(
                      label: const Text(
                        'Held before sending',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                      ),
                      selected: !isAcceptanceTab,
                      onSelected: (val) {
                        if (val) {
                          setState(() => _flashMessage = null);
                          ref.read(adminQuotationTabProvider.notifier).state =
                              'presend';
                        }
                      },
                      selectedColor: const Color(0xFF0F172A),
                      labelStyle: TextStyle(
                        color: !isAcceptanceTab ? Colors.white : const Color(0xFF334155),
                      ),
                      backgroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                        side: BorderSide(
                          color: !isAcceptanceTab
                              ? const Color(0xFF0F172A)
                              : const Color(0xFFE2E8F0),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // ── Live Flash Notification ────────────────────────────────────
              if (_flashMessage != null)
                Container(
                  margin: const EdgeInsets.only(bottom: AppSpacing.md),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFECFDF5),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFA7F3D0)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.check_circle_rounded,
                          color: Color(0xFF059669), size: 20),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _flashMessage!,
                          style: const TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF065F46),
                          ),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close_rounded, size: 16),
                        color: const Color(0xFF047857),
                        visualDensity: VisualDensity.compact,
                        onPressed: () => setState(() => _flashMessage = null),
                      ),
                    ],
                  ),
                ),

              // ── Async Quotation List ───────────────────────────────────────
              quotesAsync.when(
                loading: () => const Center(
                  child: Padding(
                    padding: EdgeInsets.all(AppSpacing.xxl),
                    child: CircularProgressIndicator(color: Color(0xFF0F172A)),
                  ),
                ),
                error: (err, _) => AppCard(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: Column(
                    children: [
                      const Icon(
                        Icons.error_outline_rounded,
                        color: Color(0xFFDC2626),
                        size: 36,
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'Unable to load approval queue',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        err.toString(),
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFF64748B),
                        ),
                      ),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: _refresh,
                        icon: const Icon(Icons.refresh_rounded, size: 16),
                        label: const Text('Try again'),
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFF0F172A),
                        ),
                      ),
                    ],
                  ),
                ),
                data: (quotes) {
                  if (quotes.isEmpty) {
                    return AppCard(
                      padding: const EdgeInsets.symmetric(
                          vertical: 40, horizontal: 16),
                      child: const EmptyState(
                        icon: Icons.article_outlined,
                        title: 'Nothing waiting in this queue.',
                        message:
                            'No quotations require administrative action at this time.',
                      ),
                    );
                  }

                  return Column(
                    children: quotes.map((q) {
                      final isBusy = _busyQuoteId == q.id;
                      return Container(
                        margin: const EdgeInsets.only(bottom: AppSpacing.md),
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                          boxShadow: const [
                            BoxShadow(
                              color: Color(0x040F172A),
                              blurRadius: 6,
                              offset: Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Card Header: Quote Number + Badges + Amount
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Wrap(
                                        spacing: 6,
                                        runSpacing: 4,
                                        crossAxisAlignment:
                                            WrapCrossAlignment.center,
                                        children: [
                                          Text(
                                            q.quoteNumber,
                                            style: const TextStyle(
                                              fontSize: 14,
                                              fontWeight: FontWeight.w800,
                                              fontFamily: 'monospace',
                                              color: Color(0xFF0F172A),
                                            ),
                                          ),
                                          if (q.quoteVersion > 1)
                                            Container(
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                      horizontal: 6,
                                                      vertical: 1.5),
                                              decoration: BoxDecoration(
                                                color: const Color(0xFFF1F5F9),
                                                borderRadius:
                                                    BorderRadius.circular(4),
                                              ),
                                              child: Text(
                                                'v${q.quoteVersion}',
                                                style: const TextStyle(
                                                  fontSize: 10.5,
                                                  fontWeight: FontWeight.w700,
                                                  color: Color(0xFF64748B),
                                                ),
                                              ),
                                            ),
                                          if (q.requiresStructuralClearance &&
                                              !q.isStructurallyCleared)
                                            Container(
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                      horizontal: 7,
                                                      vertical: 2),
                                              decoration: BoxDecoration(
                                                color: const Color(0xFFFEF3C7),
                                                borderRadius:
                                                    BorderRadius.circular(6),
                                                border: Border.all(
                                                    color:
                                                        const Color(0xFFFDE68A)),
                                              ),
                                              child: const Text(
                                                'Structural clearance needed',
                                                style: TextStyle(
                                                  fontSize: 10,
                                                  fontWeight: FontWeight.w700,
                                                  color: Color(0xFF92400E),
                                                ),
                                              ),
                                            ),
                                        ],
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        '${q.serviceName} · ${q.customerName}',
                                        style: const TextStyle(
                                          fontSize: 13,
                                          fontWeight: FontWeight.w600,
                                          color: Color(0xFF334155),
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        '${q.serviceCategory} · job #${q.jobId}${q.submittedForApprovalAt != null ? ' · accepted ${_formatTimeAgo(q.submittedForApprovalAt)}' : ''}',
                                        style: const TextStyle(
                                          fontSize: 11,
                                          color: Color(0xFF94A3B8),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.end,
                                  children: [
                                    Text(
                                      '₹${q.netPayable.toStringAsFixed(0)}',
                                      style: const TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.w900,
                                        color: Color(0xFF0F172A),
                                      ),
                                    ),
                                    Text(
                                      'incl. GST ₹${q.taxAmount.toStringAsFixed(0)}',
                                      style: const TextStyle(
                                        fontSize: 10.5,
                                        color: Color(0xFF94A3B8),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                            const SizedBox(height: 14),
                            const Divider(height: 1, color: Color(0xFFF1F5F9)),
                            const SizedBox(height: 12),

                            // Action Buttons
                            Row(
                              children: [
                                Expanded(
                                  child: FilledButton.icon(
                                    onPressed: isBusy
                                        ? null
                                        : () => _decideQuote(
                                              quote: q,
                                              approve: true,
                                              isPreSendTab: !isAcceptanceTab,
                                            ),
                                    icon: isBusy
                                        ? const SizedBox(
                                            width: 14,
                                            height: 14,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: Colors.white,
                                            ),
                                          )
                                        : Icon(
                                            !isAcceptanceTab
                                                ? Icons.send_rounded
                                                : Icons.check_circle_outline_rounded,
                                            size: 15,
                                          ),
                                    label: Text(
                                      !isAcceptanceTab
                                          ? 'Release & send'
                                          : 'Approve',
                                    ),
                                    style: FilledButton.styleFrom(
                                      backgroundColor: const Color(0xFF0F172A),
                                      foregroundColor: Colors.white,
                                      padding: const EdgeInsets.symmetric(
                                          vertical: 10),
                                      textStyle: const TextStyle(
                                        fontSize: 12.5,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: OutlinedButton.icon(
                                    onPressed: isBusy
                                        ? null
                                        : () => _decideQuote(
                                              quote: q,
                                              approve: false,
                                              isPreSendTab: !isAcceptanceTab,
                                            ),
                                    icon: const Icon(
                                      Icons.cancel_outlined,
                                      size: 15,
                                      color: Color(0xFFDC2626),
                                    ),
                                    label: const Text('Reject'),
                                    style: OutlinedButton.styleFrom(
                                      foregroundColor: const Color(0xFFDC2626),
                                      side: const BorderSide(
                                          color: Color(0xFFCBD5E1)),
                                      padding: const EdgeInsets.symmetric(
                                          vertical: 10),
                                      textStyle: const TextStyle(
                                        fontSize: 12.5,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
