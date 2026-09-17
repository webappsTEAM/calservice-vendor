"""
workforce_api 0030 – Vendor Store, Deals, Coupons, and Grocery Supplier Capability

Provisions:
1. companies_company.business_type column
2. workforce_inventory_item.mrp column
3. workforce_vendor_store table
4. workforce_vendor_deal table
5. workforce_vendor_coupon table with unique constraint on (company, code)
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0029_inventory_management"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE companies_company ADD COLUMN IF NOT EXISTS business_type VARCHAR(50) DEFAULT 'service_provider';",
            reverse_sql="ALTER TABLE companies_company DROP COLUMN IF EXISTS business_type;",
        ),
        migrations.AddField(
            model_name="inventoryitem",
            name="mrp",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Maximum Retail Price (MRP) for strike-through deals and discount display.",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="VendorStore",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("store_name", models.CharField(max_length=255)),
                ("store_slug", models.SlugField(max_length=255, unique=True)),
                ("tagline", models.CharField(blank=True, default="", max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("logo_url", models.CharField(blank=True, default="", max_length=1000)),
                ("banner_url", models.CharField(blank=True, default="", max_length=1000)),
                ("fssai_license_number", models.CharField(blank=True, default="", max_length=100)),
                ("store_address", models.TextField(blank=True, default="")),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("delivery_radius_km", models.DecimalField(decimal_places=2, default=5.0, max_digits=6)),
                ("minimum_order_amount", models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ("estimated_delivery_mins", models.IntegerField(default=30)),
                ("is_accepting_orders", models.BooleanField(db_index=True, default=True)),
                ("opening_time", models.TimeField(blank=True, null=True)),
                ("closing_time", models.TimeField(blank=True, null=True)),
                ("rating_average", models.DecimalField(decimal_places=2, default=5.0, max_digits=3)),
                ("total_reviews", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vendor_store",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "db_table": "workforce_vendor_store",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="VendorDeal",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "deal_type",
                    models.CharField(
                        choices=[
                            ("strike_through", "Strike-Through Discount"),
                            ("flash_sale", "Flash Sale"),
                            ("volume_discount", "Volume Discount"),
                        ],
                        default="strike_through",
                        max_length=30,
                    ),
                ),
                ("original_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("deal_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("deal_start_at", models.DateTimeField(blank=True, null=True)),
                ("deal_end_at", models.DateTimeField(blank=True, null=True)),
                ("badge_text", models.CharField(blank=True, default="", max_length=50)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vendor_deals",
                        to="companies.company",
                    ),
                ),
                (
                    "inventory_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deals",
                        to="workforce_api.inventoryitem",
                    ),
                ),
            ],
            options={
                "db_table": "workforce_vendor_deal",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="VendorCoupon",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(db_index=True, max_length=50)),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                (
                    "discount_type",
                    models.CharField(
                        choices=[("percent", "Percentage (%)"), ("flat", "Flat Amount (₹)")],
                        default="percent",
                        max_length=20,
                    ),
                ),
                ("discount_value", models.DecimalField(decimal_places=2, max_digits=10)),
                ("min_order_amount", models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ("max_discount_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("usage_limit_total", models.IntegerField(blank=True, null=True)),
                ("usage_limit_per_user", models.IntegerField(default=1)),
                ("times_used", models.IntegerField(default=0)),
                ("valid_from", models.DateTimeField(blank=True, null=True)),
                ("valid_until", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vendor_coupons",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "db_table": "workforce_vendor_coupon",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="vendorcoupon",
            constraint=models.UniqueConstraint(fields=["company", "code"], name="unique_vendor_coupon_code"),
        ),
    ]
