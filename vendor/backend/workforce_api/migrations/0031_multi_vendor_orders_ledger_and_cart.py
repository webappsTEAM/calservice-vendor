"""
workforce_api 0031 – Multi-Vendor Orders, Cart, Concurrency Ledger, Delivery, and Settlement
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0030_vendor_store_and_capability"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventoryitem",
            name="reserved_quantity",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                help_text="Stock quantity currently reserved by active/pending checkout carts.",
                max_digits=12,
            ),
        ),
        migrations.CreateModel(
            name="InventoryTransaction",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transaction_type", models.CharField(
                    choices=[
                        ("INITIAL_STOCK", "Initial Stock"),
                        ("PURCHASE", "Purchase / Restock"),
                        ("ADJUSTMENT", "Manual Adjustment"),
                        ("RESERVATION", "Cart Reservation"),
                        ("RESERVATION_RELEASE", "Reservation Release"),
                        ("SALE", "Order Sale"),
                        ("CANCELLATION", "Order Cancellation Return"),
                        ("RETURN", "Customer Return"),
                        ("DAMAGE", "Damaged Goods"),
                        ("EXPIRED", "Expired Produce"),
                    ],
                    max_length=30,
                )),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=12)),
                ("balance_after", models.DecimalField(decimal_places=3, max_digits=12)),
                ("reference_id", models.CharField(blank=True, default="", max_length=100)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("inventory_item", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="transactions",
                    to="workforce_api.inventoryitem",
                )),
            ],
            options={
                "db_table": "workforce_inventory_transaction",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CouponRedemption",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_id", models.CharField(db_index=True, max_length=100)),
                ("order_id", models.CharField(blank=True, db_index=True, default="", max_length=100)),
                ("discount_amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("redeemed_at", models.DateTimeField(auto_now_add=True)),
                ("coupon", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="redemptions",
                    to="workforce_api.vendorcoupon",
                )),
            ],
            options={
                "db_table": "workforce_coupon_redemption",
                "ordering": ["-redeemed_at"],
            },
        ),
        migrations.CreateModel(
            name="GroceryCart",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_id", models.CharField(db_index=True, max_length=100, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("vendor_store", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="carts",
                    to="workforce_api.vendorstore",
                )),
            ],
            options={
                "db_table": "workforce_grocery_cart",
            },
        ),
        migrations.CreateModel(
            name="GroceryCartItem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.DecimalField(decimal_places=3, default=1.0, max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cart", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="items",
                    to="workforce_api.grocerycart",
                )),
                ("inventory_item", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="cart_items",
                    to="workforce_api.inventoryitem",
                )),
            ],
            options={
                "db_table": "workforce_grocery_cart_item",
                "unique_together": {("cart", "inventory_item")},
            },
        ),
        migrations.CreateModel(
            name="GroceryOrder",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_number", models.CharField(db_index=True, max_length=50, unique=True)),
                ("customer_id", models.CharField(db_index=True, max_length=100)),
                ("customer_name", models.CharField(blank=True, default="", max_length=200)),
                ("customer_phone", models.CharField(blank=True, default="", max_length=50)),
                ("delivery_address", models.TextField(blank=True, default="")),
                ("delivery_latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("delivery_longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("status", models.CharField(
                    choices=[
                        ("PENDING_PAYMENT", "Pending Payment"),
                        ("CONFIRMED", "Confirmed"),
                        ("VENDOR_PENDING", "Vendor Pending Acceptance"),
                        ("ACCEPTED", "Accepted by Store"),
                        ("PICKING", "Picking & Packing"),
                        ("PACKED", "Packed & Ready"),
                        ("READY_FOR_PICKUP", "Ready for Pickup"),
                        ("OUT_FOR_DELIVERY", "Out for Delivery"),
                        ("DELIVERED", "Delivered"),
                        ("CANCELLED", "Cancelled"),
                        ("VENDOR_REJECTED", "Rejected by Vendor"),
                        ("REFUNDED", "Refunded"),
                    ],
                    db_index=True,
                    default="PENDING_PAYMENT",
                    max_length=30,
                )),
                ("payment_method", models.CharField(
                    choices=[("COD", "Cash on Delivery"), ("ONLINE", "Online Payment")],
                    default="COD",
                    max_length=20,
                )),
                ("payment_status", models.CharField(
                    choices=[("PENDING", "Pending"), ("CAPTURED", "Captured"), ("FAILED", "Failed"), ("REFUNDED", "Refunded")],
                    db_index=True,
                    default="PENDING",
                    max_length=20,
                )),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=10)),
                ("deal_discount", models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ("vendor_coupon_discount", models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ("platform_coupon_discount", models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ("delivery_fee", models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ("tax", models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("applied_coupon_code", models.CharField(blank=True, default="", max_length=50)),
                ("delivery_notes", models.TextField(blank=True, default="")),
                ("placed_at", models.DateTimeField(auto_now_add=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("packed_at", models.DateTimeField(blank=True, null=True)),
                ("out_for_delivery_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("vendor_store", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="orders",
                    to="workforce_api.vendorstore",
                )),
            ],
            options={
                "db_table": "workforce_grocery_order",
                "ordering": ["-placed_at"],
            },
        ),
        migrations.CreateModel(
            name="GroceryOrderItem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_name_snapshot", models.CharField(max_length=200)),
                ("sku_snapshot", models.CharField(blank=True, default="", max_length=100)),
                ("unit_snapshot", models.CharField(default="kg", max_length=20)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=12)),
                ("mrp_snapshot", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("regular_price_snapshot", models.DecimalField(decimal_places=2, max_digits=10)),
                ("deal_price_snapshot", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("final_unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("total_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("inventory_item", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="order_items",
                    to="workforce_api.inventoryitem",
                )),
                ("order", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="items",
                    to="workforce_api.groceryorder",
                )),
            ],
            options={
                "db_table": "workforce_grocery_order_item",
            },
        ),
        migrations.CreateModel(
            name="GroceryOrderStatusHistory",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(max_length=30)),
                ("to_status", models.CharField(max_length=30)),
                ("actor", models.CharField(blank=True, default="", max_length=100)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="status_history",
                    to="workforce_api.groceryorder",
                )),
            ],
            options={
                "db_table": "workforce_grocery_order_status_history",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="GroceryDelivery",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fulfillment_method", models.CharField(
                    choices=[
                        ("VENDOR_DELIVERY", "Vendor Self-Delivery"),
                        ("PLATFORM_RIDER", "CalServices Rider"),
                        ("THIRD_PARTY", "Third-Party Logistics"),
                        ("CUSTOMER_PICKUP", "Customer Pickup"),
                    ],
                    default="VENDOR_DELIVERY",
                    max_length=30,
                )),
                ("status", models.CharField(
                    choices=[
                        ("UNASSIGNED", "Unassigned"),
                        ("ASSIGNED", "Assigned to Rider"),
                        ("ARRIVED_AT_STORE", "Arrived at Store"),
                        ("PICKED_UP", "Picked Up"),
                        ("OUT_FOR_DELIVERY", "Out for Delivery"),
                        ("DELIVERED", "Delivered"),
                        ("FAILED", "Failed"),
                    ],
                    default="UNASSIGNED",
                    max_length=30,
                )),
                ("rider_name", models.CharField(blank=True, default="", max_length=100)),
                ("rider_phone", models.CharField(blank=True, default="", max_length=50)),
                ("delivery_otp", models.CharField(blank=True, default="", max_length=10)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="delivery",
                    to="workforce_api.groceryorder",
                )),
            ],
            options={
                "db_table": "workforce_grocery_delivery",
            },
        ),
        migrations.CreateModel(
            name="CommissionRule",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category_slug", models.CharField(default="vegetables", max_length=100)),
                ("commission_percent", models.DecimalField(decimal_places=2, default=5.0, max_digits=5)),
                ("fixed_fee", models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(
                    blank=True,
                    help_text="Null = applies globally across all vendors.",
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="commission_rules",
                    to="companies.company",
                )),
            ],
            options={
                "db_table": "workforce_commission_rule",
            },
        ),
        migrations.CreateModel(
            name="VendorSettlement",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("settlement_number", models.CharField(max_length=50, unique=True)),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                ("gross_sales", models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ("platform_commission", models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ("vendor_funded_discounts", models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ("net_payable", models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ("status", models.CharField(
                    choices=[("PENDING", "Pending"), ("PROCESSING", "Processing"), ("SETTLED", "Settled"), ("HOLD", "On Hold")],
                    default="PENDING",
                    max_length=20,
                )),
                ("settled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("vendor_store", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="settlements",
                    to="workforce_api.vendorstore",
                )),
            ],
            options={
                "db_table": "workforce_vendor_settlement",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="FinancialLedgerEntry",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entry_type", models.CharField(choices=[("CREDIT", "Credit"), ("DEBIT", "Debit")], max_length=10)),
                ("category", models.CharField(
                    choices=[
                        ("SALE", "Customer Order Sale"),
                        ("COMMISSION", "Platform Commission"),
                        ("DISCOUNT_DEDUCTION", "Store Coupon Deduction"),
                        ("PAYOUT", "Vendor Payout"),
                        ("ADJUSTMENT", "Manual Adjustment"),
                    ],
                    max_length=30,
                )),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("balance_after", models.DecimalField(decimal_places=2, max_digits=12)),
                ("description", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="ledger_entries",
                    to="companies.company",
                )),
                ("order", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="ledger_entries",
                    to="workforce_api.groceryorder",
                )),
                ("settlement", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="ledger_entries",
                    to="workforce_api.vendorsettlement",
                )),
            ],
            options={
                "db_table": "workforce_financial_ledger_entry",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="VendorStoreReview",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_id", models.CharField(db_index=True, max_length=100)),
                ("customer_name", models.CharField(blank=True, default="Anonymous", max_length=200)),
                ("rating", models.IntegerField(default=5)),
                ("review_text", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="review",
                    to="workforce_api.groceryorder",
                )),
                ("vendor_store", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="reviews",
                    to="workforce_api.vendorstore",
                )),
            ],
            options={
                "db_table": "workforce_vendor_store_review",
                "ordering": ["-created_at"],
            },
        ),
    ]
