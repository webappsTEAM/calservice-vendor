"""
workforce_api 0034 – Dedicated Seller Hub Category Table
Creates workforce_seller_hub_category table for grocery/seller catalog management.
Completely separate from platform service_requests_catalogcategory.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0033_catalog_category_hierarchy"),
    ]

    operations = [
        migrations.CreateModel(
            name="SellerHubCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(max_length=200, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("icon", models.CharField(blank=True, default="Store", max_length=100)),
                ("image", models.CharField(blank=True, default="", max_length=500)),
                ("sort_order", models.IntegerField(db_index=True, default=0)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.RESTRICT,
                        related_name="children",
                        to="workforce_api.sellerhubcategory",
                    ),
                ),
            ],
            options={
                "db_table": "workforce_seller_hub_category",
                "ordering": ["sort_order", "name", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="sellerhubcategory",
            index=models.Index(fields=["parent", "is_active"], name="wf_seller_cat_parent_act_idx"),
        ),
        migrations.AddIndex(
            model_name="sellerhubcategory",
            index=models.Index(fields=["is_active", "sort_order"], name="wf_seller_cat_act_sort_idx"),
        ),
        migrations.AddIndex(
            model_name="sellerhubcategory",
            index=models.Index(fields=["slug"], name="wf_seller_cat_slug_idx"),
        ),
    ]
