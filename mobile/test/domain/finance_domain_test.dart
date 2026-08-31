import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/finance/domain/employee_wallet.dart';
import 'package:mobile/features/finance/domain/payout_account.dart';
import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/finance/domain/wallet_withdrawal.dart';

void main() {
  group('Finance Domain Models', () {
    test('parses EmployeeWallet correctly and computes eligibility', () {
      final json = {
        'id': 10,
        'employee_id': 42,
        'employee_name': 'Preethi G',
        'currency': 'INR',
        'status': 'ACTIVE',
        'available_balance': '7500.00',
        'pending_balance': '2400.00',
        'lifetime_earnings': '35000.00',
        'total_withdrawn': '15000.00',
        'outstanding_recovery': '0.00',
        'next_settlement_date': '2026-08-30T10:00:00Z',
        'created_at': '2026-08-01T08:00:00Z',
        'updated_at': '2026-08-26T12:00:00Z',
      };

      final wallet = EmployeeWallet.fromJson(json);

      expect(wallet.id, 10);
      expect(wallet.employeeId, 42);
      expect(wallet.employeeName, 'Preethi G');
      expect(wallet.currency, 'INR');
      expect(wallet.status, 'ACTIVE');
      expect(wallet.isActive, isTrue);
      expect(wallet.availableBalance, 7500.0);
      expect(wallet.pendingBalance, 2400.0);
      expect(wallet.lifetimeEarnings, 35000.0);
      expect(wallet.totalWithdrawn, 15000.0);
      expect(wallet.outstandingRecovery, 0.0);
      expect(wallet.nextSettlementDate, isNotNull);
      expect(wallet.isEligibleForWithdrawal, isTrue);
      expect(wallet.withdrawalShortfall, 0.0);
      expect(wallet.withdrawalProgressRatio, 1.0);
    });

    test('computes withdrawal shortfall correctly when below threshold', () {
      final json = {
        'id': 11,
        'employee_id': 43,
        'status': 'ACTIVE',
        'available_balance': '3500.00',
        'pending_balance': '1500.00',
      };

      final wallet = EmployeeWallet.fromJson(json);

      expect(wallet.availableBalance, 3500.0);
      expect(wallet.isEligibleForWithdrawal, isFalse);
      expect(wallet.withdrawalShortfall, 1500.0);
      expect(wallet.withdrawalProgressRatio, closeTo(0.7, 0.01));
    });

    test('parses WalletTransaction and list response correctly', () {
      final listJson = {
        'count': 1,
        'page': 1,
        'page_size': 25,
        'total_pages': 1,
        'results': [
          {
            'id': 101,
            'reference_type': 'JOB_PAYMENT',
            'reference_id': 'SR-2026-8891',
            'transaction_type': 'SERVICE_EARNING',
            'direction': 'CREDIT',
            'status': 'COMPLETED',
            'amount': '2400.00',
            'gross_amount': '4000.00',
            'earn_rate_snapshot': '0.6000',
            'platform_deduction_amount': '1600.00',
            'balance_before': '5100.00',
            'balance_after': '7500.00',
            'balance_type': 'AVAILABLE',
            'description': 'AC Jet Servicing Earning',
            'created_at': '2026-08-26T10:30:00Z',
          }
        ],
      };

      final response = WalletTransactionListResponse.fromJson(listJson);

      expect(response.count, 1);
      expect(response.page, 1);
      expect(response.totalPages, 1);
      expect(response.results.length, 1);

      final txn = response.results.first;
      expect(txn.id, 101);
      expect(txn.referenceId, 'SR-2026-8891');
      expect(txn.transactionType, 'SERVICE_EARNING');
      expect(txn.displayTitle, 'Service Earning');
      expect(txn.isCredit, isTrue);
      expect(txn.isDebit, isFalse);
      expect(txn.isCompleted, isTrue);
      expect(txn.amount, 2400.0);
      expect(txn.grossAmount, 4000.0);
      expect(txn.earnRateSnapshot, 0.6000);
      expect(txn.platformDeductionAmount, 1600.0);
      expect(txn.balanceBefore, 5100.0);
      expect(txn.balanceAfter, 7500.0);
      expect(txn.balanceType, 'AVAILABLE');
    });

    test('parses WalletWithdrawal with embedded payout account and cancellable logic', () {
      final json = {
        'id': 55,
        'amount': '6000.00',
        'currency': 'INR',
        'status': 'REQUESTED',
        'payout_account_id': 3,
        'payout_account_display': {
          'id': 3,
          'bank_name': 'HDFC Bank',
          'account_number_last4': '9876',
          'account_holder_name': 'Preethi G',
        },
        'requested_at': '2026-08-26T11:00:00Z',
        'created_at': '2026-08-26T11:00:00Z',
      };

      final w = WalletWithdrawal.fromJson(json);

      expect(w.id, 55);
      expect(w.amount, 6000.0);
      expect(w.isRequested, isTrue);
      expect(w.isCancellable, isTrue);
      expect(w.statusDisplay, 'Requested');
      expect(w.payoutAccountDisplay, isNotNull);
      expect(w.payoutAccountDisplay!.bankName, 'HDFC Bank');
      expect(w.payoutAccountDisplay!.accountNumberLast4, '9876');
      expect(w.payoutAccountDisplay!.maskedAccountDisplay, '•••• 9876');
    });

    test('parses PayoutAccount and verifies security masking', () {
      final json = {
        'id': 3,
        'account_holder_name': 'Preethi G',
        'bank_name': 'State Bank of India',
        'account_number_last4': '1234',
        'ifsc_code': 'SBIN0001234',
        'account_type': 'SAVINGS',
        'verification_status': 'VERIFIED',
        'is_primary': true,
        'is_active': true,
        'created_at': '2026-08-10T14:00:00Z',
      };

      final account = PayoutAccount.fromJson(json);

      expect(account.id, 3);
      expect(account.accountHolderName, 'Preethi G');
      expect(account.bankName, 'State Bank of India');
      expect(account.accountNumberLast4, '1234');
      expect(account.maskedAccountNumber, '•••• 1234');
      expect(account.ifscCode, 'SBIN0001234');
      expect(account.accountType, 'SAVINGS');
      expect(account.accountTypeDisplay, 'Savings Account');
      expect(account.isVerified, isTrue);
      expect(account.isPrimary, isTrue);
      expect(account.isActive, isTrue);
    });
  });
}
