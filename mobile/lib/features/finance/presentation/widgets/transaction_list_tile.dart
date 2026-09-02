import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/wallet_transaction.dart';

/// Renders a single transaction card with direction indicators, badges, and timestamps.
class TransactionListTile extends StatelessWidget {
  const TransactionListTile({
    super.key,
    required this.transaction,
    required this.onTap,
  });

  final WalletTransaction transaction;
  final VoidCallback onTap;

  String _formatDate(DateTime? dt) {
    if (dt == null) return '—';
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    final day = dt.day.toString().padLeft(2, '0');
    final month = months[dt.month - 1];
    final year = dt.year;
    final hour12 = dt.hour == 0 ? 12 : (dt.hour > 12 ? dt.hour - 12 : dt.hour);
    final min = dt.minute.toString().padLeft(2, '0');
    final ampm = dt.hour >= 12 ? 'PM' : 'AM';
    return '$day $month $year · $hour12:$min $ampm';
  }

  @override
  Widget build(BuildContext context) {
    final isCredit = transaction.isCredit;
    final amountPrefix = isCredit ? '+ ' : '- ';
    final amountColor = isCredit ? const Color(0xFF059669) : const Color(0xFFE11D48);
    final iconBg = isCredit ? const Color(0xFFECFDF5) : const Color(0xFFFFF1F2);
    final iconColor = isCredit ? const Color(0xFF059669) : const Color(0xFFE11D48);

    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.card),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // 1. Transaction Icon
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: iconBg,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isCredit
                        ? const Color(0xFFA7F3D0)
                        : const Color(0xFFFECDD3),
                    width: 0.8,
                  ),
                ),
                child: Icon(
                  transaction.iconData,
                  size: 20,
                  color: iconColor,
                ),
              ),
              const SizedBox(width: AppSpacing.md),

              // 2. Transaction Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      transaction.displayTitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Row(
                      children: [
                        if (transaction.referenceId != null &&
                            transaction.referenceId!.isNotEmpty) ...[
                          Flexible(
                            child: Text(
                              transaction.referenceId!,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 11,
                                fontFamily: 'monospace',
                                fontWeight: FontWeight.w600,
                                color: AppColors.textMuted,
                              ),
                            ),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '•',
                            style: TextStyle(
                              fontSize: 10,
                              color: AppColors.textMuted,
                            ),
                          ),
                          const SizedBox(width: 4),
                        ],
                        Flexible(
                          child: Text(
                            _formatDate(transaction.createdAt),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 11,
                              color: AppColors.textMuted,
                            ),
                          ),
                        ),
                      ],
                    ),
                    if (transaction.isPendingSettlement) ...[
                      const SizedBox(height: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFFFBEB),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: const Color(0xFFFDE68A), width: 0.6),
                        ),
                        child: const Text(
                          'T+7 Hold (Pending)',
                          style: TextStyle(
                            fontSize: 9.5,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF92400E),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: AppSpacing.sm),

              // 3. Amount & Direction
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      '$amountPrefix₹${transaction.amount.toStringAsFixed(2)}',
                      style: TextStyle(
                        fontSize: 14.5,
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w900,
                        color: amountColor,
                      ),
                    ),
                  ),
                  if (transaction.balanceAfter != null) ...[
                    const SizedBox(height: 3),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text(
                        'Bal: ₹${transaction.balanceAfter!.toStringAsFixed(2)}',
                        style: TextStyle(
                          fontSize: 10.5,
                          fontFamily: 'monospace',
                          color: AppColors.textMuted,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(width: 4),
              Icon(
                Icons.chevron_right_rounded,
                size: 18,
                color: AppColors.textMuted,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
