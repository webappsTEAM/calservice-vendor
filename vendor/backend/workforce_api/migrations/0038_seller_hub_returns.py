# Generated to cleanly create Seller Hub Returns tables without altering existing tables
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '__first__'),
        ('workforce_api', '0037_seller_hub_orders'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SellerReturn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_return_id', models.CharField(db_index=True, help_text='Immutable canonical marketplace return reference from Customer app.', max_length=100, unique=True)),
                ('return_number', models.CharField(db_index=True, help_text='Human-readable merchant return reference (e.g. RET-2026-0001)', max_length=50)),
                ('customer_name', models.CharField(max_length=200)),
                ('customer_phone', models.CharField(blank=True, default='', max_length=50)),
                ('customer_address', models.TextField(blank=True, default='')),
                ('reason', models.CharField(choices=[('DAMAGED', 'Damaged / Broken on Delivery'), ('DEFECTIVE', 'Defective / Quality Issue'), ('EXPIRED', 'Expired / Spoiled Product'), ('WRONG_ITEM', 'Incorrect Item Delivered'), ('NOT_AS_DESCRIBED', 'Item Not as Described'), ('CUSTOMER_PREFERENCE', 'Customer Changed Mind / Unopened'), ('OTHER', 'Other Reason')], default='DAMAGED', max_length=50)),
                ('customer_notes', models.TextField(blank=True, default='')),
                ('evidence_urls', models.JSONField(blank=True, default=list, help_text='List of photographic evidence URLs uploaded by customer.')),
                ('status', models.CharField(choices=[('REQUESTED', 'Return Requested'), ('UNDER_SELLER_REVIEW', 'Under Seller Review'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('PICKUP_SCHEDULED', 'Pickup Scheduled'), ('RECEIVED', 'Received at Warehouse'), ('QUALITY_CHECK', 'Under Quality Inspection'), ('RESTOCKED', 'Restocked to Inventory'), ('DISCARDED', 'Scrapped / Disposed'), ('ESCALATED_TO_ADMIN', 'Escalated to Platform Admin'), ('CLOSED', 'Case Closed')], db_index=True, default='REQUESTED', max_length=30)),
                ('seller_decision', models.CharField(blank=True, default='', max_length=50)),
                ('seller_notes', models.TextField(blank=True, default='')),
                ('rejection_reason', models.TextField(blank=True, default='')),
                ('quality_check_status', models.CharField(choices=[('PENDING', 'Pending Inspection'), ('PASSED', 'Passed (Fit for Restock)'), ('FAILED', 'Failed (Damaged / Unusable)'), ('PARTIAL_PASS', 'Partial Pass')], default='PENDING', max_length=30)),
                ('quality_check_notes', models.TextField(blank=True, default='')),
                ('restock_decision', models.CharField(blank=True, default='', max_length=50)),
                ('restock_notes', models.TextField(blank=True, default='')),
                ('pickup_ref', models.CharField(blank=True, default='', max_length=100)),
                ('admin_resolution_notes', models.TextField(blank=True, default='')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('received_at', models.DateTimeField(blank=True, null=True)),
                ('inspected_at', models.DateTimeField(blank=True, null=True)),
                ('restocked_at', models.DateTimeField(blank=True, null=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seller_returns', to='companies.company')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='returns', to='workforce_api.sellerorder')),
                ('quality_checked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inspected_seller_returns', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'workforce_seller_return',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SellerReturnItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_title', models.CharField(max_length=255)),
                ('sku', models.CharField(max_length=100)),
                ('unit', models.CharField(blank=True, default='', max_length=50)),
                ('pack_size', models.CharField(blank=True, default='', max_length=100)),
                ('returned_quantity', models.DecimalField(decimal_places=3, help_text='Quantity requested for return by customer (decimal-safe).', max_digits=12)),
                ('restocked_quantity', models.DecimalField(decimal_places=3, default=Decimal('0.000'), help_text='Quantity verified, intact, and added back to inventory balance.', max_digits=12)),
                ('scrapped_quantity', models.DecimalField(decimal_places=3, default=Decimal('0.000'), help_text='Quantity damaged/spoiled that was scrapped and not returned to inventory.', max_digits=12)),
                ('item_condition', models.CharField(default='UNOPENED', help_text='Condition upon inspection: UNOPENED, OPENED_INTACT, DAMAGED, EXPIRED, WRONG_ITEM', max_length=50)),
                ('qc_result', models.CharField(default='PENDING', help_text='QC Inspection result: PENDING, PASSED, FAILED', max_length=30)),
                ('notes', models.TextField(blank=True, default='')),
                ('batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='returned_order_items', to='workforce_api.sellerinventorybatch')),
                ('order_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='return_items', to='workforce_api.sellerorderitem')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='returned_items', to='workforce_api.sellerproduct')),
                ('return_case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='workforce_api.sellerreturn')),
            ],
            options={
                'db_table': 'workforce_seller_return_item',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='SellerReturnAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_status', models.CharField(blank=True, default='', max_length=30)),
                ('to_status', models.CharField(max_length=30)),
                ('action', models.CharField(max_length=100)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='seller_return_audit_logs', to=settings.AUTH_USER_MODEL)),
                ('return_case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='workforce_api.sellerreturn')),
            ],
            options={
                'db_table': 'workforce_seller_return_audit_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='sellerreturn',
            index=models.Index(fields=['company', 'status'], name='wf_seller_ret_comp_st_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerreturn',
            index=models.Index(fields=['company', 'created_at'], name='wf_seller_ret_comp_dt_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerreturn',
            index=models.Index(fields=['source_return_id'], name='wf_seller_ret_src_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerreturn',
            index=models.Index(fields=['order'], name='wf_seller_ret_ord_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerreturnitem',
            index=models.Index(fields=['return_case', 'product'], name='wf_seller_ret_it_prod_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerreturnauditlog',
            index=models.Index(fields=['return_case', 'created_at'], name='wf_seller_ret_log_dt_idx'),
        ),
    ]
