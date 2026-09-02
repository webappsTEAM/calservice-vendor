import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_theme.dart';

/// Modal bottom sheet allowing search and selection of database tables for filtering.
class IndexTableFilterSheet extends StatefulWidget {
  const IndexTableFilterSheet({
    super.key,
    required this.tables,
    required this.selectedTable,
    required this.onSelected,
  });

  final List<String> tables;
  final String selectedTable;
  final ValueChanged<String> onSelected;

  static Future<void> show(
    BuildContext context, {
    required List<String> tables,
    required String selectedTable,
    required ValueChanged<String> onSelected,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
      ),
      builder: (ctx) => IndexTableFilterSheet(
        tables: tables,
        selectedTable: selectedTable,
        onSelected: onSelected,
      ),
    );
  }

  @override
  State<IndexTableFilterSheet> createState() => _IndexTableFilterSheetState();
}

class _IndexTableFilterSheetState extends State<IndexTableFilterSheet> {
  late TextEditingController _searchController;
  late String _query;

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController();
    _query = '';
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final filteredTables = widget.tables.where((t) {
      if (_query.isEmpty) return true;
      return t.toLowerCase().contains(_query.toLowerCase());
    }).toList();

    return SafeArea(
      child: Container(
        height: MediaQuery.of(context).size.height * 0.65,
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.md,
          AppSpacing.sm,
          AppSpacing.md,
          AppSpacing.md,
        ),
        child: Column(
          children: [
            // Drag Handle
            Center(
              child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: const Color(0xFFCBD5E1),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.sm),

            // Sheet Title & Close
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Filter by Table',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0A2540),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.xs),

            // Search Filter Field
            TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search table name...',
                prefixIcon: const Icon(Icons.search_rounded, size: 18),
                suffixIcon: _query.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear_rounded, size: 16),
                        onPressed: () {
                          setState(() {
                            _searchController.clear();
                            _query = '';
                          });
                        },
                      )
                    : null,
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              ),
              onChanged: (val) => setState(() => _query = val.trim()),
            ),
            const SizedBox(height: AppSpacing.sm),

            // "All Tables" Default Option
            ListTile(
              dense: true,
              leading: const Icon(Icons.all_inclusive_rounded, size: 18, color: Color(0xFF004E89)),
              title: const Text(
                'All Tables',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
              ),
              trailing: widget.selectedTable == 'ALL'
                  ? const Icon(Icons.check_rounded, color: Color(0xFF004E89), size: 18)
                  : null,
              onTap: () {
                widget.onSelected('ALL');
                Navigator.of(context).pop();
              },
            ),
            const Divider(height: 1),

            // Filtered Tables List
            Expanded(
              child: filteredTables.isEmpty
                  ? Center(
                      child: Text(
                        'No tables found matching "$_query"',
                        style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                      ),
                    )
                  : ListView.builder(
                      itemCount: filteredTables.length,
                      itemBuilder: (ctx, i) {
                        final tbl = filteredTables[i];
                        final isSelected = widget.selectedTable == tbl;

                        return ListTile(
                          dense: true,
                          title: Text(
                            tbl,
                            style: TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 12.5,
                              fontWeight: isSelected ? FontWeight.w800 : FontWeight.w500,
                              color: isSelected ? const Color(0xFF004E89) : const Color(0xFF1E293B),
                            ),
                          ),
                          trailing: isSelected
                              ? const Icon(Icons.check_rounded, color: Color(0xFF004E89), size: 18)
                              : null,
                          onTap: () {
                            widget.onSelected(tbl);
                            Navigator.of(context).pop();
                          },
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
