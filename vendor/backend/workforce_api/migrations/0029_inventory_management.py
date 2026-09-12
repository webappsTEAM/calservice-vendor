"""
workforce_api 0029 – Inventory Management

Creates workforce_inventory_item: a company-scoped stock table that links
each row to the shared service_requests_service catalogue by integer ID
(catalogue_service_id).  A denormalised name/category/image snapshot is
stored so inventory pages render even if the catalogue table is temporarily
unavailable.

Vendor-level overrides (custom_name, custom_image_url, custom_price) let
each company present items differently without touching the shared catalogue.

Fields
------
  id                      auto primary key
  company_id              FK → companies_company
  catalogue_service_id    integer, the PK in service_requests_service
  catalogue_category_id   integer, the PK in service_requests_catalogcategory
  name_snapshot           denorm snapshot of Service.name
  category_name_snapshot  denorm snapshot of CatalogCategory.name
  catalogue_image_url     denorm snapshot of Service.image
  custom_name             optional company override for display name
  custom_image_url        optional company override for image
  custom_price            optional company-specific selling price (decimal)
  quantity_in_stock       decimal(12,3)
  unit                    kg / g / litre / ml / piece / bunch / dozen / box / bag / packet
  low_stock_threshold     decimal(12,3), alert below this qty
  notes                   free-text notes
  is_available            bool flag (soft-disable without deleting)
  created_at / updated_at timestamps
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0028_reconcile_missing_workforce_tables"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="inventory_items",
                    to="companies.company",
                )),
                ("catalogue_service_id", models.IntegerField(
                    db_index=True,
                    help_text="ID of the matching service_requests_service row.",
                )),
                ("catalogue_category_id", models.IntegerField(
                    db_index=True,
                    help_text="ID of the matching service_requests_catalogcategory row.",
                )),
                ("name_snapshot", models.CharField(max_length=200)),
                ("category_name_snapshot", models.CharField(blank=True, default="", max_length=200)),
                ("catalogue_image_url", models.CharField(
                    blank=True, default="", max_length=1000,
                    help_text="Image URL copied from Service.image at time of add/sync.",
                )),
                ("custom_name", models.CharField(
                    blank=True, default="", max_length=200,
                    help_text="If set, overrides the catalogue display name for this company.",
                )),
                ("custom_image_url", models.CharField(
                    blank=True, default="", max_length=1000,
                    help_text="If set, overrides the catalogue image for this company.",
                )),
                ("custom_price", models.DecimalField(
                    blank=True, decimal_places=2, max_digits=10, null=True,
                    help_text="Company-specific selling price. Null = use catalogue price.",
                )),
                ("quantity_in_stock", models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ("unit", models.CharField(
                    choices=[
                        ("kg", "Kilogram (kg)"),
                        ("g", "Gram (g)"),
                        ("litre", "Litre"),
                        ("ml", "Millilitre (ml)"),
                        ("piece", "Piece"),
                        ("bunch", "Bunch"),
                        ("dozen", "Dozen"),
                        ("box", "Box"),
                        ("bag", "Bag"),
                        ("packet", "Packet"),
                    ],
                    default="kg",
                    max_length=20,
                )),
                ("low_stock_threshold", models.DecimalField(
                    decimal_places=3, default=0, max_digits=12,
                    help_text="Alert threshold – item is flagged LOW STOCK when qty <= this.",
                )),
                ("notes", models.TextField(blank=True, default="")),
                ("is_available", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "workforce_inventory_item",
                "ordering": ["category_name_snapshot", "name_snapshot"],
            },
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.UniqueConstraint(
                fields=["company", "catalogue_service_id"],
                name="unique_inventory_company_service",
            ),
        ),
    ]
