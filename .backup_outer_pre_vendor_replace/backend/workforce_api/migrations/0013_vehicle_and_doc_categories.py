# Hand-written migration (no way to run `manage.py makemigrations` against a
# matching environment in this sandbox -- see the migration-authoring note in
# other hand-written migrations from this same remediation pass). Verified by
# loading via importlib against a locally-installed Django to confirm the
# Migration class parses and the field/operation definitions are structurally
# valid -- not verified against the live database. Before applying: run
# `python manage.py makemigrations --check --dry-run` to confirm this matches
# what Django itself would generate, per this codebase's established
# convention for hand-written migrations.
#
# GT-A-01: adds Vehicle, a new managed model -- a driver was previously "an
# Employee with a job title", with no vehicle record anywhere.
# GT-A-02: adds WorkforceRequiredDocument.applies_to_categories (default []),
# so document requirements (e.g. Driving Licence, RC, Insurance, Permit) can
# be scoped to specific job categories instead of gating every job for every
# technician. Default [] preserves current behaviour for every existing row.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workforce_api', '0012_postserviceproof_after_presence_photo'),
        ('employees', '__first__'),
        ('companies', '__first__'),
    ]

    operations = [
        migrations.AddField(
            model_name='workforcerequireddocument',
            name='applies_to_categories',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.CreateModel(
            name='Vehicle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vehicle_type', models.CharField(choices=[('two_wheeler', 'Two Wheeler'), ('three_wheeler', 'Three Wheeler / Auto'), ('mini_truck', 'Mini Truck'), ('pickup', 'Pickup Van'), ('truck', 'Truck'), ('other', 'Other')], default='other', max_length=20)),
                ('registration_number', models.CharField(db_index=True, max_length=30)),
                ('capacity_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('capacity_label', models.CharField(blank=True, default='', max_length=50)),
                ('insurance_expiry', models.DateField(blank=True, null=True)),
                ('permit_expiry', models.DateField(blank=True, null=True)),
                ('puc_expiry', models.DateField(blank=True, null=True)),
                ('rc_verified', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vehicles', to='companies.company')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vehicles', to='employees.employee')),
            ],
            options={
                'db_table': 'workforce_vehicle',
                'ordering': ['-created_at'],
                'unique_together': {('company', 'registration_number')},
            },
        ),
    ]
