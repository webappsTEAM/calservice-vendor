# Hand-written migration -- see 0013_vehicle_and_doc_categories.py for why
# (no way to run `manage.py makemigrations` against a matching environment
# in this sandbox). Verified by loading via importlib against a locally-
# installed Django to confirm the Migration class parses and matches the
# model definitions -- not verified against the live database. Run
# `python manage.py makemigrations --check --dry-run` before applying.
#
# GT-C-02: adds CashSettlement plus JobPayment.reconciled/reconciled_in --
# see the model docstrings in workforce_api/models.py for the full
# rationale.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workforce_api', '0013_vehicle_and_doc_categories'),
        ('employees', '__first__'),
        ('companies', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='CashSettlement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expected_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('deposited_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discrepancy', models.DecimalField(decimal_places=2, max_digits=10)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cash_settlements', to='companies.company')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cash_settlements', to='employees.employee')),
                ('recorded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cash_settlements_recorded', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'workforce_cash_settlement',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='jobpayment',
            name='reconciled',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='jobpayment',
            name='reconciled_in',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reconciled_payments', to='workforce_api.cashsettlement'),
        ),
    ]
