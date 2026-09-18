# Generated to cleanly create Seller Hub Inventory tables without altering existing tables
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '__first__'),
        ('workforce_api', '0035_seller_product_catalog'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SellerInventory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('on_hand_qty', models.DecimalField(decimal_places=3, default=Decimal('0.000'), help_text='Physical inventory on hand in warehouse / storefront.', max_digits=12)),
                ('reserved_qty', models.DecimalField(decimal_places=3, default=Decimal('0.000'), help_text='Stock locked for active processing.', max_digits=12)),
                ('low_stock_threshold', models.DecimalField(decimal_places=3, default=Decimal('10.000'), help_text='Threshold below which inventory is marked as Low Stock.', max_digits=12)),
                ('reorder_level', models.DecimalField(decimal_places=3, default=Decimal('20.000'), help_text='Suggested replenishment reorder point.', max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seller_inventories', to='companies.company')),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='inventory', to='workforce_api.sellerproduct')),
            ],
            options={
                'db_table': 'workforce_seller_inventory',
                'ordering': ['-updated_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SellerInventoryBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_number', models.CharField(db_index=True, max_length=100)),
                ('received_date', models.DateField(default=django.utils.timezone.now)),
                ('expiry_date', models.DateField(blank=True, db_index=True, null=True)),
                ('initial_quantity', models.DecimalField(decimal_places=3, max_digits=12)),
                ('current_quantity', models.DecimalField(decimal_places=3, max_digits=12)),
                ('cost_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('EXPIRING_SOON', 'Expiring Soon'), ('EXPIRED', 'Expired'), ('DEPLETED', 'Depleted')], db_index=True, default='ACTIVE', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('inventory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batches', to='workforce_api.sellerinventory')),
            ],
            options={
                'db_table': 'workforce_seller_inventory_batch',
                'ordering': ['expiry_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SellerInventoryMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('movement_type', models.CharField(choices=[('OPENING_STOCK', 'Opening Stock'), ('STOCK_IN', 'Stock In / Purchase'), ('STOCK_OUT', 'Stock Out / Transfer'), ('ADJUSTMENT_INCREASE', 'Stock Adjustment (Increase)'), ('ADJUSTMENT_DECREASE', 'Stock Adjustment (Decrease)'), ('DAMAGE', 'Damaged / Broken Stock'), ('EXPIRED', 'Expired Stock Write-off'), ('RESERVED', 'Order Stock Reserved'), ('RESERVATION_RELEASED', 'Reservation Released'), ('ORDER_DEDUCTED', 'Order Fulfilled / Stock Deducted')], db_index=True, max_length=40)),
                ('quantity_change', models.DecimalField(decimal_places=3, help_text='Positive for additions, negative for reductions.', max_digits=12)),
                ('balance_before', models.DecimalField(decimal_places=3, help_text='On-hand balance before the operation.', max_digits=12)),
                ('balance_after', models.DecimalField(decimal_places=3, help_text='On-hand balance after the operation.', max_digits=12)),
                ('reason', models.TextField(blank=True, default='', help_text='Mandatory business reason for adjustments, damages, or expiries.')),
                ('reference_id', models.CharField(blank=True, default='', help_text='Optional PO number, Invoice reference, or Batch number.', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='seller_inventory_movements', to=settings.AUTH_USER_MODEL)),
                ('batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movements', to='workforce_api.sellerinventorybatch')),
                ('inventory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movements', to='workforce_api.sellerinventory')),
            ],
            options={
                'db_table': 'workforce_seller_inventory_movement',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='sellerinventory',
            index=models.Index(fields=['company', 'on_hand_qty'], name='wf_seller_inv_comp_qty_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerinventory',
            index=models.Index(fields=['product', 'on_hand_qty'], name='wf_seller_inv_prod_qty_idx'),
        ),
        migrations.AddConstraint(
            model_name='sellerinventory',
            constraint=models.UniqueConstraint(fields=('company', 'product'), name='unique_seller_product_inventory'),
        ),
        migrations.AddIndex(
            model_name='sellerinventorybatch',
            index=models.Index(fields=['inventory', 'expiry_date'], name='wf_seller_batch_inv_exp_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerinventorybatch',
            index=models.Index(fields=['inventory', 'status'], name='wf_seller_batch_inv_st_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerinventorymovement',
            index=models.Index(fields=['inventory', 'movement_type'], name='wf_seller_mov_inv_type_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerinventorymovement',
            index=models.Index(fields=['inventory', 'created_at'], name='wf_seller_mov_inv_dt_idx'),
        ),
    ]
