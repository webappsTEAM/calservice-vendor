# 08. Wallets, Financial Ledgers & Settlements

## 1. Accounting Principles & Double-Entry Ledger

The Workforce platform enforces double-entry bookkeeping across all financial interactions. Direct balance alterations without an accompanying immutable `FinancialLedgerEntry` are strictly prevented.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DOUBLE-ENTRY LEDGER FLOW                        │
│                                                                        │
│                       Customer Pays ₹1,000 (COD)                       │
│                                   │                                    │
│       ┌───────────────────────────┴───────────────────────────┐        │
│       ▼                                                       ▼        │
│  [DEBIT] Technician Wallet Floating Cash              [CREDIT] Booking  │
│  (Tech holds ₹1,000 physical cash)                    Payment Collected │
│                                                                        │
│                       Job Completed Successfully                       │
│                                   │                                    │
│       ┌───────────────────────────┴───────────────────────────┐        │
│       ▼                                                       ▼        │
│  [CREDIT] Vendor Settlement Balance: ₹850             [CREDIT] Platform │
│  (Net payout after commission)                        Commission: ₹150 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Cash on Delivery (COD) & Cash Collection

When a customer pays cash to a technician upon job completion:
1. Technician submits cash collection via `POST /api/workforce/jobs/{id}/cash-collection/`.
2. Technician's `floating_cash_balance` increases by the collected cash amount.
3. Once floating cash exceeds the vendor's configured limit (e.g. ₹5,000), further dispatches to the technician are paused until cash is remitted to the company account.

---

## 3. Platform Commissions & Vendor Net Settlement

- **Configurable Commission Rules:** Defined per service category (e.g., 15% on AC repair, 10% on grocery delivery).
- **Automated Deduction:** Upon job completion, the platform fee is deducted atomically and credited to the platform treasury ledger.
- **Vendor Net Credit:** The remaining balance is credited to the vendor company's `WalletAccount.balance`.

---

## 4. Bank Account Verification & Payout Withdrawals

1. **Bank Account Registration:** Vendors and technicians link bank accounts with Account Holder Name, Account Number, and IFSC Code.
2. **Withdrawal Request:** Vendor requests payout via `/api/workforce/wallet/withdraw/`.
3. **Locking & Verification:** The requested payout amount is moved from `balance` to `pending_balance`.
4. **Admin Approval & Settlement:** Platform finance admin reviews and executes payout via bank NEFT/IMPS/UPI and logs the Unique Transaction Reference (UTR).
5. **Ledger Finalization:** `pending_balance` is cleared, and an immutable withdrawal ledger record is stamped.
