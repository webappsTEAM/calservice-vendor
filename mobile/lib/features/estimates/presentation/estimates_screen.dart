import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_card.dart';
import '../../../shared/widgets/empty_state.dart';
import '../../../shared/widgets/workforce_app_bar.dart';
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
    {'id': 'all', 'label': 'All Quotes'},
    {'id': 'draft', 'label': 'Drafts'},
    {'id': 'sent', 'label': 'Sent'},
    {'id': 'accepted', 'label': 'Accepted'},
    {'id': 'declined', 'label': 'Declined'},
  ];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final activeTab = ref.watch(estimatesFilterTabProvider);
    final quotesAsync = ref.watch(quotesListProvider);
    final metrics = ref.watch(quotesMetricsProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: const WorkforceAppBar(
        titleText: 'Estimates & Quotes',
        showBrand: false,
        showStatusSubBar: false,
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(quotesListProvider);
          await ref.read(quotesListProvider.future);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.sm,
            AppSpacing.lg,
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

            // ── Screen Title & Subtitle ─────────────────────────────────────
            const Text(
              'Estimates & Quotations',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                color: Color(0xFF0A2540),
              ),
            ),
            const SizedBox(height: 2),
            Text(
              'Calculate prices, prepare customer quotations & track proposal statuses.',
              style: TextStyle(
                fontSize: 12,
                color: AppColors.textMuted,
                height: 1.35,
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── Metrics Strip ───────────────────────────────────────────────
            AppCard(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
              child: Row(
                children: [
                  _SummaryStat(
                    label: 'Total Quotes',
                    value: '${metrics['total'] ?? 0}',
                    icon: Icons.calculate_outlined,
                    color: const Color(0xFF004E89),
                  ),
                  _StatDivider(),
                  _SummaryStat(
                    label: 'Drafts',
                    value: '${metrics['drafts'] ?? 0}',
                    icon: Icons.edit_note_rounded,
                    color: const Color(0xFF64748B),
                  ),
                  _StatDivider(),
                  _SummaryStat(
                    label: 'Sent',
                    value: '${metrics['sent'] ?? 0}',
                    icon: Icons.send_rounded,
                    color: const Color(0xFF0284C7),
                  ),
                  _StatDivider(),
                  _SummaryStat(
                    label: 'Accepted',
                    value: '${metrics['accepted'] ?? 0}',
                    icon: Icons.check_circle_rounded,
                    color: const Color(0xFF059669),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),

            // ── Search Input ────────────────────────────────────────────────
            TextField(
              controller: _searchController,
              onChanged: (val) {
                ref.read(estimatesSearchQueryProvider.notifier).state = val.trim();
              },
              decoration: InputDecoration(
                hintText: 'Search quotes by number, client, or service...',
                hintStyle: TextStyle(fontSize: 12.5, color: AppColors.textMuted),
                prefixIcon: const Icon(Icons.search_rounded, size: 20),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear_rounded, size: 18),
                        onPressed: () {
                          _searchController.clear();
                          ref.read(estimatesSearchQueryProvider.notifier).state = '';
                        },
                      )
                    : null,
                filled: true,
                fillColor: Colors.white,
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
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
            const SizedBox(height: AppSpacing.md),

            // ── Filter Tabs ─────────────────────────────────────────────────
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
                      const Icon(Icons.error_outline_rounded, size: 40, color: Color(0xFFE11D48)),
                      const SizedBox(height: AppSpacing.md),
                      const Text(
                        'Failed to load estimates',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
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
                      children: [
                        const EmptyState(
                          icon: Icons.calculate_outlined,
                          title: 'No Quotations Found',
                          message:
                              'Quotations created for estimation service jobs will appear here automatically.',
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
          Icon(icon, size: 16, color: color),
          const SizedBox(height: 3),
          Text(
            value,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w900,
              fontFamily: 'monospace',
            ),
          ),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 9.5,
              fontWeight: FontWeight.w600,
              color: AppColors.textMuted,
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
      height: 28,
      color: AppColors.border,
      margin: const EdgeInsets.symmetric(horizontal: 2),
    );
  }
}
