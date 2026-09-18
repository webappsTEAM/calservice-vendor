"""
workforce_api 0032 – VendorStore onboarding and GST number fields
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0031_multi_vendor_orders_ledger_and_cart"),
    ]

    operations = [
        migrations.AddField(
            model_name="vendorstore",
            name="gst_number",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="vendorstore",
            name="onboarding",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
