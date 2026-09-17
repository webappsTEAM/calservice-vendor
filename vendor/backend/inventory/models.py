"""
vendor/backend/inventory/models.py

Unmanaged mirrors of the InventoryItem / StockMovement tables owned by
Customer/backend/inventory (see that app's models.py). Both Django projects
share one Postgres database in production; Customer/backend owns migrations
for these tables, this app only reads/writes the same rows -- same pattern
already used by vendor/backend/companies (Company) and
vendor/backend/service_requests (Service, CatalogCategory, etc.).

Field set is kept 1:1 with Customer/backend/inventory/models.py so a row
written from either project is valid to the other.
"""
from django.db import models
from django.conf import settings


class InventoryItem(models.Model):
    class Category(models.TextChoices):
        EQUIPMENT = 'equipment', 'Equipment'
        CONSUMABLE = 'consumable', 'Consumable'
        UNIFORM = 'uniform', 'Uniform'
        VEHICLE = 'vehicle', 'Vehicle'
        PPE = 'ppe', 'PPE'
        TOOL = 'tool', 'Tool'
        PART = 'part', 'Spare Part'
        MATERIAL = 'material', 'Raw Material'

    org = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name='mirror_inventory_items', db_column="org_id")
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=Category.choices)
    sku = models.CharField(max_length=100, blank=True)
    warehouse_name = models.CharField(max_length=255, blank=True, default="Main Warehouse")
    total_quantity = models.PositiveIntegerField(default=0)
    available_quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reorder_threshold = models.PositiveIntegerField(default=0)
    reorder_quantity = models.PositiveIntegerField(default=10)
    pending_purchase_quantity = models.PositiveIntegerField(default=0)
    expected_delivery_date = models.DateField(null=True, blank=True)
    is_returnable = models.BooleanField(default=True)
    requires_photo_on_issue = models.BooleanField(default=False)
    image = models.CharField(max_length=500, blank=True, default="")
    unit = models.CharField(max_length=20, blank=True, default="")
    stock_quantity_grams = models.PositiveIntegerField(null=True, blank=True, default=None)
    default_daily_quantity_grams = models.PositiveIntegerField(null=True, blank=True, default=None)
    last_reset_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "inventory_inventoryitem"

    @property
    def effective_available_quantity(self):
        return max(0, self.total_quantity - self.reserved_quantity)

    def __str__(self):
        return f"{self.name} ({self.sku})"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        RESTOCK = "RESTOCK", "Restock"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        DAILY_RESET = "DAILY_RESET", "Daily Reset"
        SOLD = "SOLD", "Sold"
        RESTOCKED_ON_CANCELLATION = "RESTOCKED_ON_CANCELLATION", "Restocked on Cancellation"

    org = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="stock_movements", db_column="org_id")
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="stock_movements")
    movement_type = models.CharField(max_length=30, choices=MovementType.choices)
    delta_grams = models.IntegerField()
    balance_after_grams = models.PositiveIntegerField()
    reason = models.TextField(blank=True, default="")
    booking_ref = models.CharField(max_length=100, blank=True, default="")
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="entered_stock_movements")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "inventory_stockmovement"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.item_id} | {self.movement_type} | {self.delta_grams:+d}g -> {self.balance_after_grams}g"
