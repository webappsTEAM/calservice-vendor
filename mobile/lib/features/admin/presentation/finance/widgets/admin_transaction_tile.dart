import 'package:flutter/material.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/finance/presentation/widgets/transaction_detail_sheet.dart';

/// List tile representing a single ledger transaction from the admin perspective.
class AdminTransactionTile extends StatelessWidget {
  const AdminTransactionTile({
    super.key,
    required this.transaction,
    this.technicianName,
  });

  final WalletTransaction transaction;
  final String? technicianName;

  IconData _iconForType(String type) {
    switch (type) {
      case 'SERVICE_EARNING':
        return Icons.handyman_rounded;
      case 'PLATFORM_COMMISSION':
        return Icons.percent_rounded;
      case 'SETTLEMENT_RELEASE':
        return Icons.lock_open_rounded;
      case 'WITHDRAWAL':
        return Icons.payments_rounded;
      case 'ADJUSTMENT_CREDIT':
      case 'ADJUSTMENT_DEBIT':
        return Icons.tune_rounded;
      case 'RECOVERY_DEBIT':
      case 'REFUND':
        return Icons.undo_rounded;
      default:
        return Icons.receipt_long_rounded;
    }
  }

  Color _iconColor(String direction) {
    return direction == 'CREDIT' ? const Color(0xFF059669) : const Color(0xFFDC2626);
  }

  @override
  Widget build(BuildContext context) {
    final isCredit = transaction.direction == 'CREDIT';
    final sign = isCredit ? '+' : '-';
    final amountColor = isCredit ? const Color(0xFF059669) : const Color(0xFFDC2626);

    return InkWell(
      onTap: () => TransactionDetailSheet.show(context, transaction),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: AppColors.border, width: 0.8)),
        ),
        child: Row(
          children: [
            // Icon
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: _iconColor(transaction.direction).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                _iconForType(transaction.transactionType),
                color: _iconColor(transaction.direction),
                size: 18,
              ),
            ),
            const SizedBox(width: 10),

            // Description & Reference
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          transaction.displayTitle,
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (transaction.isPendingSettlement)
                        Container(
                          margin: const EdgeInsets.only(left: 6),
                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                          decoration: BoxDecoration(
                            color: const Color(0xFFFEF3C7),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Text(
                            'T+7 HOLD',
                            style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF92400E),
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${technicianName != null ? "$technicianName • " : ""}${(transaction.referenceId != null && transaction.referenceId!.isNotEmpty) ? transaction.referenceId! : (transaction.description ?? "")}',
                    style: TextStyle(
                      fontSize: 11,
                      color: AppColors.textMuted,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),

            // Amount & Timestamp
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '$sign₹${transaction.amount.toStringAsFixed(2)}',
                  style: TextStyle(
                    fontSize: 13.5,
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.w800,
                    color: amountColor,
                  ),
                ),
                if (transaction.createdAt != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    '${transaction.createdAt!.day}/${transaction.createdAt!.month} ${transaction.createdAt!.hour}:${transaction.createdAt!.minute.toString().padLeft(2, "0")}',
                    style: TextStyle(fontSize: 10, color: AppColors.textMuted),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}
