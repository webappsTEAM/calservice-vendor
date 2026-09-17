# 09. Commission & Financial Settlement Model

## Settlement Formula
Every completed grocery order generates immutable ledger credits to the vendor's wallet:

$$\text{Net Vendor Payable} = \text{Gross Order Sales} - \text{Vendor Coupon Discounts} - \text{Platform Commission}$$

### Example Breakdown:
- **Customer Gross Item Total**: ₹500.00
- **Store Coupon Discount**: -₹50.00
- **Net Customer Paid**: ₹450.00
- **Platform Commission (5% on ₹500)**: -₹25.00
- **Net Credited to Vendor Wallet**: ₹425.00

## Configurable Commission Engine
Commission is managed via `CommissionRule`:
```python
class CommissionRule(models.Model):
    company = ForeignKey(Company, null=True, blank=True)  # Null = applies globally
    category_slug = CharField(default="vegetables")
    commission_percent = DecimalField(default=5.00)
    fixed_fee = DecimalField(default=0.00)
    is_active = BooleanField(default=True)
```
Platform administrators can adjust commission rates on a per-vendor or per-category basis without changing code.

## Double-Entry Financial Ledger
Instead of simply modifying `wallet.balance += amount`, all credits and debits create permanent audit entries in `FinancialLedgerEntry`:
- `CREDIT` (Category: `SALE`): Automatically created when an order transitions to `DELIVERED`.
- `DEBIT` (Category: `PAYOUT`): Created when earnings are transferred to vendor's verified bank account.
- `DEBIT` (Category: `COMMISSION`): Platform revenue deduction.
