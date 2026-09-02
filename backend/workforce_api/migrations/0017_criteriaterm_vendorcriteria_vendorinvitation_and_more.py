# Generated for Technician-Vendor Network

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '__first__'),
        ('employees', '__first__'),
        ('workforce_api', '0016_workforce_scorecard'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VendorCriteria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='technician_criteria', to='companies.company')),
            ],
            options={
                'db_table': 'workforce_vendor_criteria',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CriteriaTerm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attribute_type', models.CharField(choices=[('SKILL', 'Skill'), ('SERVICE_CATEGORY', 'Service Category'), ('LOCATION', 'Location / City'), ('EXPERIENCE_YEARS', 'Experience (Years)'), ('AVAILABILITY', 'Availability'), ('EMPLOYMENT_TYPE', 'Employment Type'), ('MIN_RATING', 'Minimum Rating')], default='SKILL', max_length=40)),
                ('operator', models.CharField(choices=[('EQUALS', 'Equals'), ('IN', 'In'), ('GTE', 'Greater Than or Equal'), ('LTE', 'Less Than or Equal'), ('CONTAINS', 'Contains')], default='EQUALS', max_length=20)),
                ('value', models.JSONField(default=dict)),
                ('group_id', models.IntegerField(db_index=True, default=1)),
                ('criteria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='terms', to='workforce_api.vendorcriteria')),
            ],
            options={
                'db_table': 'workforce_criteria_term',
            },
        ),
        migrations.CreateModel(
            name='VendorInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invited_email', models.EmailField(db_index=True, max_length=254)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('REJECTED', 'Rejected'), ('EXPIRED', 'Expired'), ('CANCELLED', 'Cancelled')], db_index=True, default='PENDING', max_length=20)),
                ('channel', models.CharField(choices=[('DIRECT_EMAIL', 'Direct Email'), ('MATCHING_RESULT', 'Matching Result')], default='DIRECT_EMAIL', max_length=30)),
                ('message', models.TextField(blank=True, default='')),
                ('token', models.CharField(db_index=True, max_length=128, unique=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('matched_criteria', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invitations', to='workforce_api.vendorcriteria')),
                ('technician', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='received_vendor_invitations', to='employees.employee')),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_technician_invitations', to='companies.company')),
            ],
            options={
                'db_table': 'workforce_vendor_invitation',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='VendorTechnicianRelationship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('SUSPENDED', 'Suspended'), ('TERMINATED', 'Terminated')], db_index=True, default='ACTIVE', max_length=20)),
                ('scope_skills', models.JSONField(blank=True, default=list)),
                ('engagement_type', models.CharField(choices=[('PER_JOB', 'Per Job'), ('PART_TIME', 'Part Time'), ('FULL_TIME', 'Full Time'), ('ON_CALL', 'On Call')], default='PER_JOB', max_length=30)),
                ('payment_model', models.CharField(choices=[('DIRECT_TO_TECHNICIAN', 'Direct to Technician'), ('THROUGH_VENDOR', 'Through Vendor')], default='DIRECT_TO_TECHNICIAN', max_length=30)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_vendor_relationships', to=settings.AUTH_USER_MODEL)),
                ('source_invitation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resulting_relationships', to='workforce_api.vendorinvitation')),
                ('technician', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vendor_relationships', to='employees.employee')),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='technician_relationships', to='companies.company')),
            ],
            options={
                'db_table': 'workforce_vendor_technician_relationship',
                'ordering': ['-started_at'],
                'unique_together': {('vendor', 'technician')},
            },
        ),
    ]
