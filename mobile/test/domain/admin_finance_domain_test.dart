import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';

void main() {
  group('AdminWallet Domain Model Tests', () {
    test('parses AdminWallet from json correctly', () {
      final json = {
        'id': 10,
        'employee_id': 101,
        'employee_name': 'Ramesh Kumar',
        'currency': 'INR',
        'status': 'ACTIVE',
        'available_balance': 12500.50,
        'pending_balance': 3400.00,
        'lifetime_earnings': 45000.00,
        'total_withdrawn': 29100.00,
        'outstanding_recovery': 0.00,
        'next_settlement_date': '2026-09-02T10:00:00Z',
      };

      final wallet = AdminWallet.fromJson(json);

      expect(wallet.id, 10);
      expect(wallet.employeeId, 101);
      expect(wallet.employeeName, 'Ramesh Kumar');
      expect(wallet.availableBalance, 12500.50);
      expect(wallet.pendingBalance, 3400.00);
      expect(wallet.lifetimeEarnings, 45000.00);
      expect(wallet.totalWithdrawn, 29100.00);
      expect(wallet.isActive, isTrue);
      expect(wallet.isLocked, isFalse);
      expect(wallet.statusDisplay, 'Active');
    });

    test('computes AdminWalletSummary from wallet list', () {
      final wallets = [
        AdminWallet.fromJson({
          'id': 1,
          'employee_id': 101,
          'employee_name': 'Tech 1',
          'status': 'ACTIVE',
          'available_balance': 5000.0,
          'pending_balance': 1500.0,
          'lifetime_earnings': 20000.0,
          'total_withdrawn': 13500.0,
        }),
        AdminWallet.fromJson({
          'id': 2,
          'employee_id': 102,
          'employee_name': 'Tech 2',
          'status': 'LOCKED',
          'available_balance': 8000.0,
          'pending_balance': 2000.0,
          'lifetime_earnings': 30000.0,
          'total_withdrawn': 20000.0,
        }),
      ];

      final summary = AdminWalletSummary.fromWallets(wallets);

      expect(summary.totalWallets, 2);
      expect(summary.totalAvailableBalance, 13000.0);
      expect(summary.totalPendingBalance, 3500.0);
      expect(summary.totalDisbursed, 33500.0);
      expect(summary.activeWalletsCount, 1);
      expect(summary.lockedWalletsCount, 1);
    });

    test('parses AdminWithdrawal with masked account and status getters', () {
      final json = {
        'id': 501,
        'amount': 7500.00,
        'currency': 'INR',
        'status': 'PROCESSING',
        'employee_id': 101,
        'employee_name': 'Ramesh Kumar',
        'payout_account_id': 12,
        'payout_account_display': {
          'id': 12,
          'bank_name': 'HDFC Bank',
          'account_number_last4': '4321',
          'account_holder_name': 'Ramesh Kumar',
        },
        'bank_transaction_id': null,
      };

      final withdrawal = AdminWithdrawal.fromJson(json);

      expect(withdrawal.id, 501);
      expect(withdrawal.amount, 7500.0);
      expect(withdrawal.isProcessing, isTrue);
      expect(withdrawal.isRequested, isFalse);
      expect(withdrawal.statusDisplay, 'Processing');
      expect(withdrawal.payoutAccountDisplay?.maskedAccountDisplay, '•••• 4321');
    });

    test('parses AdminBankAccount and enforces masked account display', () {
      final json = {
        'id': 22,
        'employee_id': 101,
        'employee_name': 'Ramesh Kumar',
        'bank_name': 'State Bank of India',
        'account_holder_name': 'Ramesh Kumar',
        'account_number_last4': '9876',
        'ifsc_code': 'SBIN0001234',
        'account_type': 'SAVINGS',
        'verification_status': 'PENDING_REVIEW',
        'is_primary': true,
        'is_active': true,
      };

      final account = AdminBankAccount.fromJson(json);

      expect(account.id, 22);
      expect(account.bankName, 'State Bank of India');
      expect(account.maskedAccountNumber, '•••• 9876');
      expect(account.isPendingReview, isTrue);
      expect(account.isVerified, isFalse);
      expect(account.statusDisplay, 'Pending Review');
      expect(account.accountTypeDisplay, 'Savings Account');
    });

    test('parses AdminWallet with string-serialized decimals from DRF API correctly', () {
      final json = {
        'id': 1,
        'employee_id': 21,
        'employee_name': 'Mani S',
        'currency': 'INR',
        'status': 'ACTIVE',
        'available_balance': '0.00',
        'pending_balance': '0.00',
        'lifetime_earnings': '0.00',
        'total_withdrawn': '0.00',
        'outstanding_recovery': '0.00',
        'next_settlement_date': null,
      };

      final wallet = AdminWallet.fromJson(json);

      expect(wallet.id, 1);
      expect(wallet.employeeId, 21);
      expect(wallet.employeeName, 'Mani S');
      expect(wallet.availableBalance, 0.0);
      expect(wallet.pendingBalance, 0.0);
      expect(wallet.lifetimeEarnings, 0.0);
      expect(wallet.totalWithdrawn, 0.0);
      expect(wallet.outstandingRecovery, 0.0);
      expect(wallet.status, 'ACTIVE');
      expect(wallet.isActive, isTrue);
    });
  });
}
