# Generated to cleanly create Seller Hub Orders tables without altering existing tables
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '__first__'),
        ('workforce_api', '0036_seller_hub_inventory'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SellerOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_order_id', models.CharField(db_index=True, help_text='Immutable canonical marketplace order reference from Customer app.', max_length=100, unique=True)),
                ('order_number', models.CharField(db_index=True, help_text='Human-readable merchant display order number (e.g. SO-2026-0001)', max_length=50)),
                ('customer_name', models.CharField(max_length=200)),
                ('customer_phone', models.CharField(blank=True, default='', max_length=50)),
                ('delivery_address', models.TextField(blank=True, default='')),
                ('fulfillment_type', models.CharField(choices=[('DELIVERY', 'Delivery'), ('STORE_PICKUP', 'Store Pickup')], default='DELIVERY', max_length=30)),
                ('delivery_slot', models.CharField(blank=True, default='', max_length=100)),
                ('delivery_notes', models.TextField(blank=True, default='')),
                ('handover_otp_hash', models.CharField(blank=True, max_length=256, null=True)),
                ('handover_ref', models.CharField(blank=True, default='', max_length=100)),
                ('payment_method', models.CharField(default='ONLINE', max_length=50)),
                ('payment_status', models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('COD', 'Cash On Delivery')], default='PAID', max_length=30)),
                ('total_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('currency', models.CharField(default='INR', max_length=10)),
                ('status', models.CharField(choices=[('NEW', 'New Order'), ('ACCEPTED', 'Accepted'), ('PICKING', 'Picking in Progress'), ('PACKED', 'Packed & Ready'), ('READY_FOR_PICKUP', 'Ready for Pickup'), ('HANDED_OVER', 'Handed Over'), ('DELIVERED', 'Delivered'), ('CANCELLED', 'Cancelled')], db_index=True, default='NEW', max_length=30)),
                ('seller_notes', models.TextField(blank=True, default='')),
                ('cancellation_reason', models.TextField(blank=True, default='')),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('picking_at', models.DateTimeField(blank=True, null=True)),
                ('packed_at', models.DateTimeField(blank=True, null=True)),
                ('ready_at', models.DateTimeField(blank=True, null=True)),
                ('handed_over_at', models.DateTimeField(blank=True, null=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cancelled_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cancelled_seller_orders', to=settings.AUTH_USER_MODEL)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seller_orders', to='companies.company')),
            ],
            options={
                'db_table': 'workforce_seller_order',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SellerOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_title', models.CharField(max_length=255)),
                ('sku', models.CharField(max_length=100)),
                ('unit', models.CharField(blank=True, default='', max_length=50)),
                ('pack_size', models.CharField(blank=True, default='', max_length=100)),
                ('ordered_quantity', models.DecimalField(decimal_places=3, help_text='Quantity ordered by customer (decimal-safe for kg, litres, etc.)', max_digits=12)),
                ('fulfilled_quantity', models.DecimalField(decimal_places=3, default=Decimal('0.000'), help_text='Quantity actually picked and packed by merchant.', max_digits=12)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('line_total', models.DecimalField(decimal_places=2, max_digits=12)),
                ('is_picked', models.BooleanField(default=False)),
                ('is_packed', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True, default='')),
                ('batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_items', to='workforce_api.sellerinventorybatch')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='workforce_api.sellerorder')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='workforce_api.sellerproduct')),
            ],
            options={
                'db_table': 'workforce_seller_order_item',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='SellerOrderAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_status', models.CharField(blank=True, default='', max_length=30)),
                ('to_status', models.CharField(max_length=30)),
                ('action', models.CharField(max_length=100)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='seller_order_audit_logs', to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='workforce_api.sellerorder')),
            ],
            options={
                'db_table': 'workforce_seller_order_audit_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='sellerorder',
            index=models.Index(fields=['company', 'status'], name='wf_seller_ord_comp_st_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerorder',
            index=models.Index(fields=['company', 'created_at'], name='wf_seller_ord_comp_dt_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerorder',
            index=models.Index(fields=['source_order_id'], name='wf_seller_ord_src_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerorderitem',
            index=models.Index(fields=['order', 'product'], name='wf_seller_item_ord_prod_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerorderauditlog',
            index=models.Index(fields=['order', 'created_at'], name='wf_seller_ord_log_dt_idx'),
        ),
    ]
