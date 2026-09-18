# Generated manually to cleanly create Seller Product Catalog tables without altering existing tables
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '__first__'),
        ('workforce_api', '0034_seller_hub_category'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SellerCatalogUploadBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(max_length=255)),
                ('total_rows', models.IntegerField(default=0)),
                ('imported_rows', models.IntegerField(default=0)),
                ('failed_rows', models.IntegerField(default=0)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed'), ('PARTIALLY_FAILED', 'Partially Failed')], db_index=True, default='PENDING', max_length=20)),
                ('error_report', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seller_catalog_batches', to='companies.company')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_catalog_batches', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'workforce_seller_catalog_upload_batch',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SellerProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('brand', models.CharField(blank=True, db_index=True, default='', max_length=150)),
                ('sku', models.CharField(db_index=True, max_length=100)),
                ('barcode', models.CharField(blank=True, db_index=True, default='', max_length=100)),
                ('unit', models.CharField(default='piece', max_length=50)),
                ('pack_size', models.CharField(default='1', max_length=50)),
                ('mrp', models.DecimalField(decimal_places=2, max_digits=10)),
                ('selling_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tax_rate', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=5)),
                ('hsn_code', models.CharField(blank=True, default='', max_length=50)),
                ('storage_info', models.CharField(blank=True, default='', max_length=255)),
                ('expiry_info', models.CharField(blank=True, default='', max_length=255)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('SUBMITTED', 'Submitted'), ('UNDER_REVIEW', 'Under Review'), ('CHANGES_REQUESTED', 'Changes Requested'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('PAUSED', 'Paused')], db_index=True, default='DRAFT', max_length=30)),
                ('admin_review_note', models.TextField(blank=True, default='')),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='products', to='workforce_api.sellerhubcategory')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seller_products', to='companies.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_seller_products', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_seller_products', to=settings.AUTH_USER_MODEL)),
                ('upload_batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='workforce_api.sellercataloguploadbatch')),
            ],
            options={
                'db_table': 'workforce_seller_product',
                'ordering': ['-updated_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SellerProductAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=50)),
                ('from_status', models.CharField(blank=True, default='', max_length=30)),
                ('to_status', models.CharField(max_length=30)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='seller_product_audit_logs', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='workforce_api.sellerproduct')),
            ],
            options={
                'db_table': 'workforce_seller_product_audit_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SellerProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_url', models.CharField(max_length=500)),
                ('is_primary', models.BooleanField(default=False)),
                ('sort_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='workforce_api.sellerproduct')),
            ],
            options={
                'db_table': 'workforce_seller_product_image',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='sellerproduct',
            index=models.Index(fields=['company', 'status'], name='wf_seller_prod_comp_st_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerproduct',
            index=models.Index(fields=['category', 'status'], name='wf_seller_prod_cat_st_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerproduct',
            index=models.Index(fields=['status', 'updated_at'], name='wf_seller_prod_st_upd_idx'),
        ),
        migrations.AddConstraint(
            model_name='sellerproduct',
            constraint=models.UniqueConstraint(fields=('company', 'sku'), name='unique_seller_product_sku_per_company'),
        ),
    ]
