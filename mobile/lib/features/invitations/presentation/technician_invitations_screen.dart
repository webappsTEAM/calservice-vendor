import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_error.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_card.dart';
import '../../../shared/widgets/empty_state.dart';
import '../data/invitations_repository.dart';
import '../domain/technician_invitation.dart';
import 'invitations_providers.dart';
import 'widgets/invitation_card.dart';

/// Classic Vendor Invitations Screen for Flutter Mobile.
///
/// Features:
/// 1. Classic App Bar with SEVO Peacock gradient, title, back navigation, and refresh action.
/// 2. Header subtitle explaining private invitations context.
/// 3. Independent Worker Status card (or Active Vendor Partner card when partnered).
/// 4. Horizontally scrollable status filter tabs (Pending, Accepted, Declined, All History) with real counts.
/// 5. Classic invitation cards with vendor info, note, matched criteria, timestamps, and status badges.
/// 6. Accept & Decline confirmation dialogs with platform workforce explanations.
/// 7. Real API persistence, auto-refresh, and feedback snackbars.
/// 8. Responsive layout supporting 320px-412px widths with zero RenderFlex overflow.
class TechnicianInvitationsScreen extends ConsumerStatefulWidget {
  const TechnicianInvitationsScreen({super.key});

  @override
  ConsumerState<TechnicianInvitationsScreen> createState() =>
      _TechnicianInvitationsScreenState();
}

class _TechnicianInvitationsScreenState
    extends ConsumerState<TechnicianInvitationsScreen> {
  int? _processingId;

  static const _filterTabs = [
    {'id': 'PENDING', 'label': 'Pending'},
    {'id': 'ACCEPTED', 'label': 'Accepted'},
    {'id': 'REJECTED', 'label': 'Declined'},
    {'id': 'ALL', 'label': 'All History'},
  ];

  Future<void> _promptAccept(
    TechnicianInvitation invitation,
    ActiveVendorInfo? activeVendor,
  ) async {
    final isSwitching = activeVendor != null && activeVendor.vendorId != invitation.vendorId;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.card),
        ),
        title: Row(
          children: const [
            Icon(Icons.verified_user_rounded, color: Color(0xFF004E89), size: 22),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                'Accept Invitation',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF0A2540),
                ),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Once accepted, you will join "${invitation.vendorName}" and become dedicated to them according to the platform\'s workforce rules.',
              style: TextStyle(
                fontSize: 13,
                color: AppColors.textPrimary,
                height: 1.4,
              ),
            ),
            if (isSwitching) ...[
              const SizedBox(height: AppSpacing.md),
              Container(
                padding: const EdgeInsets.all(AppSpacing.sm),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFFBEB),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFFDE68A), width: 0.8),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.warning_amber_rounded, size: 18, color: Color(0xFFD97706)),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'You are currently assigned to "${activeVendor.vendorName}". Accepting will switch your primary vendor partnership to "${invitation.vendorName}".',
                        style: const TextStyle(
                          fontSize: 11.5,
                          color: Color(0xFF92400E),
                          height: 1.35,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(
              'Cancel',
              style: TextStyle(
                color: AppColors.textMuted,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF004E89),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: const Text(
              'Accept & Join',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await _executeResponse(invitation, 'ACCEPT');
    }
  }

  Future<void> _promptDecline(TechnicianInvitation invitation) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.card),
        ),
        title: Row(
          children: const [
            Icon(Icons.cancel_outlined, color: Color(0xFFDC2626), size: 22),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                'Decline Invitation',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF0A2540),
                ),
              ),
            ),
          ],
        ),
        content: Text(
          'Are you sure you want to decline the invitation from "${invitation.vendorName}"?',
          style: TextStyle(
            fontSize: 13,
            color: AppColors.textPrimary,
            height: 1.4,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(
              'Keep Invitation',
              style: TextStyle(
                color: AppColors.textMuted,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFFDC2626),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: const Text(
              'Decline Invitation',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await _executeResponse(invitation, 'REJECT');
    }
  }

  Future<void> _executeResponse(
    TechnicianInvitation invitation,
    String decision,
  ) async {
    setState(() => _processingId = invitation.id);

    try {
      final repo = ref.read(invitationsRepositoryProvider);
      await repo.respondToInvitation(
        invitationId: invitation.id,
        decision: decision,
      );

      ref.invalidate(technicianInvitationsProvider);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              decision == 'ACCEPT'
                  ? 'Invitation accepted! You are now partnered with ${invitation.vendorName}.'
                  : 'Invitation declined.',
            ),
            backgroundColor: decision == 'ACCEPT'
                ? const Color(0xFF059669) // Emerald Green
                : const Color(0xFF64748B), // Slate
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        );
      }
    } on DioException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              describeDioError(e, fallback: 'Failed to process invitation response.'),
            ),
            backgroundColor: const Color(0xFFDC2626),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _processingId = null);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final activeTab = ref.watch(invitationsFilterTabProvider);
    final invitationsAsync = ref.watch(technicianInvitationsProvider);

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
          'Vendor Invitations',
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
            tooltip: 'Refresh Invitations',
            onPressed: () => ref.invalidate(technicianInvitationsProvider),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(technicianInvitationsProvider);
          await ref.read(technicianInvitationsProvider.future);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.sm,
            AppSpacing.lg,
            AppSpacing.xxl,
          ),
          children: [
            // ── Context Subtitle ───────────────────────────────────────────
            Text(
              'Private invitations received directly from verified service businesses.',
              style: TextStyle(
                fontSize: 12,
                color: AppColors.textMuted,
                height: 1.35,
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── Async Content ───────────────────────────────────────────────
            invitationsAsync.when(
              loading: () => Column(
                children: [
                  const SizedBox(height: AppSpacing.xxl),
                  Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const CircularProgressIndicator(
                          strokeWidth: 3,
                          color: Color(0xFF004E89),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        Text(
                          'Loading invitations...',
                          style: TextStyle(
                            fontSize: 13,
                            color: AppColors.textMuted,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              error: (err, _) => Center(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.error_outline_rounded,
                        size: 44,
                        color: Color(0xFFE11D48),
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        'Unable to load invitations. Please try again.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 14.5,
                          fontWeight: FontWeight.w800,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.md),
                      FilledButton.icon(
                        onPressed: () => ref.invalidate(technicianInvitationsProvider),
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFF004E89),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ),
                        icon: const Icon(Icons.refresh_rounded, size: 16),
                        label: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              ),
              data: (data) {
                final activeVendor = data.activeVendor;
                final invitations = data.invitations;

                final pendingCount = invitations.where((i) => i.isPending).length;
                final acceptedCount = invitations.where((i) => i.isAccepted).length;
                final declinedCount = invitations.where((i) => i.isRejected).length;

                final filteredList = invitations.where((inv) {
                  if (activeTab == 'ALL') return true;
                  if (activeTab == 'PENDING') return inv.isPending;
                  if (activeTab == 'ACCEPTED') return inv.isAccepted;
                  if (activeTab == 'REJECTED') return inv.isRejected;
                  return inv.status == activeTab;
                }).toList();

                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // ── Independent Worker Status Card / Active Vendor Card ─────
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(AppSpacing.md),
                      decoration: BoxDecoration(
                        color: AppColors.surface,
                        borderRadius: BorderRadius.circular(AppRadius.card),
                        border: Border.all(
                          color: activeVendor != null
                              ? const Color(0xFF059669).withValues(alpha: 0.35)
                              : const Color(0xFF004E89).withValues(alpha: 0.2),
                          width: 1.0,
                        ),
                        boxShadow: AppElevation.subtle,
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: activeVendor != null
                                  ? const Color(0xFFECFDF5)
                                  : const Color(0xFFEFF6FF),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Icon(
                              activeVendor != null
                                  ? Icons.verified_user_rounded
                                  : Icons.person_outline_rounded,
                              size: 22,
                              color: activeVendor != null
                                  ? const Color(0xFF059669)
                                  : const Color(0xFF004E89),
                            ),
                          ),
                          const SizedBox(width: AppSpacing.md),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    if (activeVendor == null) ...[
                                      const Text(
                                        '🟢 ',
                                        style: TextStyle(fontSize: 10),
                                      ),
                                    ],
                                    Expanded(
                                      child: Text(
                                        activeVendor != null
                                            ? 'Partnered: ${activeVendor.vendorName}'
                                            : 'Independent Worker Status',
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                          fontSize: 13.5,
                                          fontWeight: FontWeight.w800,
                                          color: AppColors.textPrimary,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 3),
                                Text(
                                  activeVendor != null
                                      ? 'You are actively partnered with this vendor. To accept an invitation from another organization, you must first relieve from ${activeVendor.vendorName}.'
                                      : 'You are currently free to accept an invitation and join any vendor\'s team. Once you accept, you will be dedicated to that vendor until you choose to relieve yourself.',
                                  style: TextStyle(
                                    fontSize: 11.5,
                                    color: AppColors.textSecondary,
                                    height: 1.35,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),

                    // ── Status Filter Tabs ──────────────────────────────────
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: _filterTabs.map((tab) {
                          final isSelected = activeTab == tab['id'];
                          final count = switch (tab['id']) {
                            'PENDING' => pendingCount,
                            'ACCEPTED' => acceptedCount,
                            'REJECTED' => declinedCount,
                            'ALL' => invitations.length,
                            _ => 0,
                          };

                          final labelText = tab['id'] == 'PENDING' && count == 0
                              ? 'Pending'
                              : '${tab['label']} ($count)';

                          return Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: ChoiceChip(
                              label: Text(
                                labelText,
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: isSelected
                                      ? FontWeight.w800
                                      : FontWeight.w600,
                                  color: isSelected
                                      ? Colors.white
                                      : AppColors.textPrimary,
                                ),
                              ),
                              selected: isSelected,
                              onSelected: (selected) {
                                if (selected) {
                                  ref
                                      .read(invitationsFilterTabProvider.notifier)
                                      .state = tab['id']!;
                                }
                              },
                              selectedColor: const Color(0xFF004E89), // Peacock Blue
                              backgroundColor: AppColors.surface,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(8),
                                side: BorderSide(
                                  color: isSelected
                                      ? const Color(0xFF004E89)
                                      : AppColors.border,
                                ),
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),

                    // ── Invitations List / Empty State ───────────────────────
                    if (filteredList.isEmpty)
                      AppCard(
                        padding: const EdgeInsets.symmetric(
                          vertical: 36,
                          horizontal: 20,
                        ),
                        child: EmptyState(
                          icon: Icons.mail_outline_rounded,
                          title: activeTab == 'PENDING'
                              ? 'No pending invitations'
                              : 'No invitations found in this tab',
                          message: activeTab == 'PENDING'
                              ? 'Keep your skills and availability updated. When vendors match with your profile, your invitations will appear here.'
                              : 'Your past invitation decisions and history will be recorded here.',
                        ),
                      )
                    else
                      Column(
                        children: filteredList.map((inv) {
                          return InvitationCard(
                            invitation: inv,
                            isProcessing: _processingId == inv.id,
                            onAccept: () => _promptAccept(inv, activeVendor),
                            onDecline: () => _promptDecline(inv),
                          );
                        }).toList(),
                      ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
