import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_card.dart';
import '../../../shared/widgets/empty_state.dart';
import '../../../shared/widgets/workforce_app_bar.dart';
import '../../admin/presentation/widgets/admin_drawer.dart';
import '../../auth/presentation/auth_controller.dart';
import 'estimates_providers.dart';
import 'widgets/quote_card.dart';

class EstimatesScreen extends ConsumerStatefulWidget {
  const EstimatesScreen({super.key});

  @override
  ConsumerState<EstimatesScreen> createState() => _EstimatesScreenState();
}

class _EstimatesScreenState extends ConsumerState<EstimatesScreen> {
  final TextEditingController _searchController = TextEditingController();

  static const _tabs = [
    {'id': 'all', 'label': 'All Leads'},
    {'id': 'draft', 'label': 'New Requests'},
    {'id': 'assigned', 'label': 'Assigned'},
    {'id': 'in_progress', 'label': 'In Progress'},
    {'id': 'sent', 'label': 'Quotation Sent'},
    {'id': 'accepted', 'label': 'Completed'},
  ];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final activeTab = ref.watch(estimatesFilterTabProvider);
    final selectedDate = ref.watch(estimatesDateFilterProvider);
    final quotesAsync = ref.watch(quotesListProvider);
    final metrics = ref.watch(quotesMetricsProvider);
    final user = ref.watch(authControllerProvider).user;
    final isAdmin = user?.isAdmin == true;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: WorkforceAppBar(
        titleText: 'AC Estimations',
        showBrand: false,
        showStatusSubBar: false,
        showDrawerMenu: isAdmin,
      ),
      drawer: isAdmin ? const AdminDrawer() : null,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(quotesListProvider);
            await ref.read(quotesListProvider.future);
          },
          child: ListView(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.md,
              AppSpacing.sm,
              AppSpacing.md,
              AppSpacing.xxl,
            ),
            children: [
              // ── Breadcrumb / Back Action ────────────────────────────────────
              if (Navigator.of(context).canPop()) ...[
                InkWell(
                  onTap: () => Navigator.of(context).pop(),
                  borderRadius: BorderRadius.circular(6),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 2),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: const [
                        Icon(Icons.arrow_back_rounded, size: 16, color: Color(0xFF004E89)),
                        SizedBox(width: 4),
                        Text(
                          'Back',
                          style: TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF004E89),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 6),
              ],

              // ── Screen Header: Context Badge & Refresh Action ───────────────
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEFF6FF),
                      borderRadius: BorderRadius.circular(5),
                      border: Border.all(
                        color: const Color(0xFFBFDBFE),
                        width: 0.8,
                      ),
                    ),
                    child: const Text(
                      'Vendor Portal',
                      style: TextStyle(
                        fontSize: 9.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                        color: Color(0xFF1E40AF),
                      ),
                    ),
                  ),
                  InkWell(
                    onTap: () {
                      ref.invalidate(quotesListProvider);
                    },
                    borderRadius: BorderRadius.circular(6),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: const [
                          Icon(Icons.refresh_rounded, size: 15, color: Color(0xFF004E89)),
                          SizedBox(width: 4),
                          Text(
                            'Refresh',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF004E89),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),

              // ── Screen Title & Subtitle ─────────────────────────────────────
              const Text(
                'AC Inspection & Quotation Manager',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                  color: Color(0xFF0A2540),
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'Manage AC diagnostic leads, on-site technician inspections, and formal versioned quotations.',
                style: TextStyle(
                  fontSize: 12,
                  color: AppColors.textMuted,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // ── Responsive Metrics Summary Strip ────────────────────────────
              AppCard(
                padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
                child: Row(
                  children: [
                    _SummaryStat(
                      label: 'Total Leads',
                      value: '${metrics['total'] ?? 0}',
                      icon: Icons.calculate_outlined,
                      color: const Color(0xFF004E89),
                    ),
                    _StatDivider(),
                    _SummaryStat(
                      label: 'New Requests',
                      value: '${metrics['drafts'] ?? 0}',
                      icon: Icons.edit_note_rounded,
                      color: const Color(0xFF64748B),
                    ),
                    _StatDivider(),
                    _SummaryStat(
                      label: 'Quotation Sent',
                      value: '${metrics['sent'] ?? 0}',
                      icon: Icons.send_rounded,
                      color: const Color(0xFF0284C7),
                    ),
                    _StatDivider(),
                    _SummaryStat(
                      label: 'Completed',
                      value: '${metrics['accepted'] ?? 0}',
                      icon: Icons.check_circle_rounded,
                      color: const Color(0xFF059669),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // ── Search & Date Filtering Controls ────────────────────────────
              Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: TextField(
                      controller: _searchController,
                      onChanged: (val) {
                        ref.read(estimatesSearchQueryProvider.notifier).state = val.trim();
                      },
                      decoration: InputDecoration(
                        hintText: 'Search customer, ID, brand ...',
                        hintStyle: TextStyle(fontSize: 12, color: AppColors.textMuted),
                        prefixIcon: const Icon(Icons.search_rounded, size: 18),
                        suffixIcon: _searchController.text.isNotEmpty
                            ? IconButton(
                                icon: const Icon(Icons.clear_rounded, size: 16),
                                onPressed: () {
                                  _searchController.clear();
                                  ref.read(estimatesSearchQueryProvider.notifier).state = '';
                                },
                              )
                            : null,
                        filled: true,
                        fillColor: Colors.white,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide(color: AppColors.border),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide(color: AppColors.border),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: Color(0xFF004E89), width: 1.5),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    flex: 2,
                    child: InkWell(
                      onTap: () async {
                        final picked = await showDatePicker(
                          context: context,
                          initialDate: DateTime.now(),
                          firstDate: DateTime(2020),
                          lastDate: DateTime(2030),
                        );
                        if (picked != null) {
                          final formatted =
                              '${picked.day.toString().padLeft(2, '0')}/${picked.month.toString().padLeft(2, '0')}/${picked.year}';
                          ref.read(estimatesDateFilterProvider.notifier).state = formatted;
                        }
                      },
                      borderRadius: BorderRadius.circular(10),
                      child: Container(
                        height: 44,
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: selectedDate != null
                                ? const Color(0xFF004E89)
                                : AppColors.border,
                            width: selectedDate != null ? 1.5 : 1,
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              Icons.calendar_today_rounded,
                              size: 14,
                              color: selectedDate != null
                                  ? const Color(0xFF004E89)
                                  : AppColors.textMuted,
                            ),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(
                                selectedDate ?? 'dd/mm/yyyy',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: selectedDate != null
                                      ? FontWeight.w700
                                      : FontWeight.w500,
                                  color: selectedDate != null
                                      ? const Color(0xFF0A2540)
                                      : AppColors.textMuted,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            if (selectedDate != null)
                              GestureDetector(
                                onTap: () {
                                  ref.read(estimatesDateFilterProvider.notifier).state = null;
                                },
                                child: const Icon(
                                  Icons.close_rounded,
                                  size: 14,
                                  color: Color(0xFF64748B),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),

              // ── Status Filter Tabs ──────────────────────────────────────────
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: _tabs.map((tab) {
                    final isSelected = activeTab == tab['id'];
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(
                          tab['label']!,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                            color: isSelected ? Colors.white : AppColors.textPrimary,
                          ),
                        ),
                        selected: isSelected,
                        onSelected: (selected) {
                          if (selected) {
                            ref.read(estimatesFilterTabProvider.notifier).state = tab['id']!;
                          }
                        },
                        selectedColor: const Color(0xFF004E89),
                        backgroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                          side: BorderSide(
                            color: isSelected ? const Color(0xFF004E89) : AppColors.border,
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // ── Async Quotes List ───────────────────────────────────────────
              quotesAsync.when(
                loading: () => const Center(
                  child: Padding(
                    padding: EdgeInsets.all(AppSpacing.xxl),
                    child: CircularProgressIndicator(),
                  ),
                ),
                error: (err, _) => Center(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.xl),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.error_outline_rounded,
                          size: 40,
                          color: Color(0xFFE11D48),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        const Text(
                          'Request failed',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF0F172A),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          err.toString(),
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        ElevatedButton.icon(
                          onPressed: () => ref.invalidate(quotesListProvider),
                          icon: const Icon(Icons.refresh_rounded, size: 16),
                          label: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                ),
                data: (quotes) {
                  if (quotes.isEmpty) {
                    return AppCard(
                      padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 16),
                      child: Column(
                        children: const [
                          EmptyState(
                            icon: Icons.air_rounded,
                            title: 'No Estimation Leads Found',
                            message:
                                'No matching AC inspection requests found for current filter criteria.',
                          ),
                        ],
                      ),
                    );
                  }

                  return Column(
                    children: quotes.map((quote) => QuoteCard(quote: quote)).toList(),
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

class _SummaryStat extends StatelessWidget {
  const _SummaryStat({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: color),
          const SizedBox(height: 2),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              value,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w900,
                fontFamily: 'monospace',
              ),
            ),
          ),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 9.5,
                fontWeight: FontWeight.w600,
                color: AppColors.textMuted,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatDivider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 1,
      height: 26,
      color: AppColors.border,
      margin: const EdgeInsets.symmetric(horizontal: 1),
    );
  }
}
