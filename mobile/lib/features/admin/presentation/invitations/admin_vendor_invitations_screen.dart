import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/empty_state.dart';
import '../../../../shared/widgets/status_chip.dart';
import '../../../../shared/widgets/workforce_app_bar.dart';
import '../../data/admin_dashboard_api.dart';
import '../../domain/vendor_invitation.dart';
import '../admin_dashboard_providers.dart';
import '../widgets/admin_drawer.dart';

/// Admin Vendor Invitations Screen.
/// Enables service providers to send, monitor, and manage direct invitations to technicians.
class AdminVendorInvitationsScreen extends ConsumerStatefulWidget {
  const AdminVendorInvitationsScreen({super.key});

  @override
  ConsumerState<AdminVendorInvitationsScreen> createState() =>
      _AdminVendorInvitationsScreenState();
}

class _AdminVendorInvitationsScreenState
    extends ConsumerState<AdminVendorInvitationsScreen> {
  String _selectedStatus = 'PENDING';
  int? _actionLoadingId;

  void _openSendInviteSheet() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => _SendInviteSheet(
        onSent: () {
          ref.invalidate(adminVendorInvitationsProvider);
        },
      ),
    );
  }

  Future<void> _handleCancelInvite(VendorSentInvitation invite) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel Invitation'),
        content: Text(
          'Are you sure you want to cancel the invitation sent to ${invite.invitedEmail}?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Keep Invitation'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFDC2626)),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Cancel Invite'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      setState(() => _actionLoadingId = invite.id);
      final api = ref.read(adminDashboardApiProvider);
      await api.cancelVendorInvitation(invite.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Invitation to ${invite.invitedEmail} cancelled.'),
            backgroundColor: const Color(0xFF059669),
          ),
        );
        ref.invalidate(adminVendorInvitationsProvider);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to cancel invitation: $e'),
            backgroundColor: const Color(0xFFDC2626),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _actionLoadingId = null);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusFilter = _selectedStatus == 'ALL' ? null : _selectedStatus;
    final invitationsAsync =
        ref.watch(adminVendorInvitationsProvider(statusFilter));

    return Scaffold(
      appBar: const WorkforceAppBar(
        titleText: 'Send Invitations',
        showStatusSubBar: false,
        showDrawerMenu: true,
      ),
      drawer: const AdminDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(adminVendorInvitationsProvider);
          await ref.read(adminVendorInvitationsProvider(statusFilter).future);
        },
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.md),
          children: [
            // ── Header Card ──────────────────────────────────────────────
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
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEFF6FF),
                          borderRadius: BorderRadius.circular(5),
                          border: Border.all(color: const Color(0xFFBFDBFE)),
                        ),
                        child: const Text(
                          'MY WORKFORCE',
                          style: TextStyle(
                            fontSize: 9.5,
                            fontWeight: FontWeight.w900,
                            color: Color(0xFF004E89),
                            letterSpacing: 0.6,
                          ),
                        ),
                      ),
                      IconButton(
                        onPressed: () => ref.invalidate(adminVendorInvitationsProvider),
                        icon: const Icon(Icons.refresh_rounded, size: 20, color: Color(0xFF004E89)),
                        tooltip: 'Refresh Invitations',
                        visualDensity: VisualDensity.compact,
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Send Invitations',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                      color: Color(0xFF0F172A),
                    ),
                  ),
                  const SizedBox(height: 2),
                  const Text(
                    'Send private invitations and manage technician partnership proposals',
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFF64748B),
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _openSendInviteSheet,
                    icon: const Icon(Icons.send_rounded, size: 16),
                    label: const Text('Send New Invitation'),
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF004E89),
                      foregroundColor: Colors.white,
                      textStyle: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── Status Filter Tabs ────────────────────────────────────────
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildTab('PENDING', 'Pending'),
                  const SizedBox(width: 6),
                  _buildTab('ACCEPTED', 'Accepted'),
                  const SizedBox(width: 6),
                  _buildTab('REJECTED', 'Rejected'),
                  const SizedBox(width: 6),
                  _buildTab('EXPIRED', 'Expired'),
                  const SizedBox(width: 6),
                  _buildTab('ALL', 'All Invites'),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── Invitation Items / Async State ───────────────────────────
            invitationsAsync.when(
              loading: () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(AppSpacing.xl),
                  child: CircularProgressIndicator(),
                ),
              ),
              error: (err, _) => Container(
                padding: const EdgeInsets.all(AppSpacing.lg),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(AppRadius.card),
                  border: Border.all(color: const Color(0xFFFECACA)),
                ),
                child: Column(
                  children: [
                    const Icon(Icons.error_outline_rounded, color: Color(0xFFDC2626), size: 36),
                    const SizedBox(height: 8),
                    Text(
                      'Failed to load invitations: $err',
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 12.5, color: Color(0xFF991B1B)),
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: () => ref.invalidate(adminVendorInvitationsProvider),
                      icon: const Icon(Icons.refresh_rounded, size: 16),
                      label: const Text('Retry'),
                    ),
                  ],
                ),
              ),
              data: (data) {
                final list = data.invitations;
                if (list.isEmpty) {
                  return const EmptyState(
                    icon: Icons.mail_outline_rounded,
                    title: 'No Invitations Found',
                    message: 'No technician invitations matching this status.',
                  );
                }

                return Column(
                  children: list.map((inv) => _buildInviteCard(inv)).toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTab(String value, String label) {
    final isSelected = _selectedStatus == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (_) => setState(() => _selectedStatus = value),
      selectedColor: const Color(0xFF004E89),
      backgroundColor: Colors.white,
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w700,
        color: isSelected ? Colors.white : const Color(0xFF475569),
      ),
      side: BorderSide(
        color: isSelected ? const Color(0xFF004E89) : const Color(0xFFCBD5E1),
      ),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    );
  }

  Widget _buildInviteCard(VendorSentInvitation invite) {
    final isActing = _actionLoadingId == invite.id;

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
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
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  'CODE: ${invite.inviteCode.isNotEmpty ? invite.inviteCode : '#${invite.id}'}',
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF334155),
                  ),
                ),
              ),
              StatusChip(
                status: invite.status,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              const Icon(Icons.mail_rounded, size: 16, color: Color(0xFF004E89)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  invite.invitedEmail,
                  style: const TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0F172A),
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          if (invite.technicianName != null && invite.technicianName!.isNotEmpty) ...[
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(Icons.person_outline_rounded, size: 14, color: Color(0xFF64748B)),
                const SizedBox(width: 4),
                Text(
                  invite.technicianName!,
                  style: const TextStyle(fontSize: 11.5, color: Color(0xFF475569)),
                ),
              ],
            ),
          ],
          if (invite.message != null && invite.message!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Text(
                '"${invite.message}"',
                style: const TextStyle(
                  fontSize: 11,
                  fontStyle: FontStyle.italic,
                  color: Color(0xFF475569),
                ),
              ),
            ),
          ],
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (invite.createdAt != null)
                Text(
                  'Sent: ${invite.createdAt!.split('T').first}',
                  style: const TextStyle(fontSize: 10.5, color: Color(0xFF94A3B8)),
                )
              else
                const SizedBox.shrink(),
              if (invite.isPending)
                isActing
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : TextButton.icon(
                        onPressed: () => _handleCancelInvite(invite),
                        icon: const Icon(Icons.close_rounded, size: 14, color: Color(0xFFDC2626)),
                        label: const Text(
                          'Cancel',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFFDC2626),
                          ),
                        ),
                        style: TextButton.styleFrom(
                          visualDensity: VisualDensity.compact,
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                        ),
                      ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SendInviteSheet extends ConsumerStatefulWidget {
  const _SendInviteSheet({required this.onSent});
  final VoidCallback onSent;

  @override
  ConsumerState<_SendInviteSheet> createState() => _SendInviteSheetState();
}

class _SendInviteSheetState extends ConsumerState<_SendInviteSheet> {
  final _emailController = TextEditingController();
  final _messageController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _isSending = false;

  @override
  void dispose() {
    _emailController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    try {
      setState(() => _isSending = true);
      final api = ref.read(adminDashboardApiProvider);
      await api.createVendorInvitation(
        invitedEmail: _emailController.text.trim(),
        message: _messageController.text.trim(),
      );

      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Invitation sent successfully.'),
            backgroundColor: Color(0xFF059669),
          ),
        );
        widget.onSent();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to send invite: $e'),
            backgroundColor: const Color(0xFFDC2626),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.md,
        right: AppSpacing.md,
        top: AppSpacing.lg,
        bottom: MediaQuery.of(context).viewInsets.bottom + AppSpacing.lg,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Send Technician Invitation',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                    color: Color(0xFF0F172A),
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close_rounded, size: 20),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Text(
              'Technician Email *',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF334155)),
            ),
            const SizedBox(height: 4),
            TextFormField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              decoration: InputDecoration(
                hintText: 'technician@example.com',
                prefixIcon: const Icon(Icons.email_outlined, size: 18),
                filled: true,
                fillColor: const Color(0xFFF8FAFC),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
              validator: (v) {
                if (v == null || v.trim().isEmpty) return 'Please enter an email address';
                if (!v.contains('@') || !v.contains('.')) return 'Please enter a valid email';
                return null;
              },
            ),
            const SizedBox(height: 12),
            const Text(
              'Invitation Message / Note (Optional)',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF334155)),
            ),
            const SizedBox(height: 4),
            TextFormField(
              controller: _messageController,
              maxLines: 2,
              decoration: InputDecoration(
                hintText: 'We would like to invite you to join our service team.',
                filled: true,
                fillColor: const Color(0xFFF8FAFC),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 44,
              child: FilledButton.icon(
                onPressed: _isSending ? null : _submit,
                icon: _isSending
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.send_rounded, size: 16),
                label: Text(_isSending ? 'Sending...' : 'Send Invitation'),
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF004E89),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
