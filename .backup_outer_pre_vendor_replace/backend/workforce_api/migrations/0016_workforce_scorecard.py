# Hand-written migration -- see 0013_vehicle_and_doc_categories.py /
# 0014_gt_c02_cash_settlement.py / 0015_sevo_wallet_infrastructure.py for
# why (no way to run `manage.py makemigrations` against a matching
# environment in this sandbox -- the project venv is a Windows venv only
# usable from the user's own machine). Verified by loading via importlib
# against a locally-installed Django to confirm the Migration class
# parses and matches the model definition -- not verified against the
# live database. Run `python manage.py makemigrations --check --dry-run`
# before applying to confirm no drift.
#
# SEVO business-plan implementation, Section 4 (rating + SLA scorecards)
# -- see the WorkforceScorecard model docstring in workforce_api/models.py
# for the full rationale.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workforce_api', '0015_sevo_wallet_infrastructure'),
        ('employees', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkforceScorecard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating_count', models.PositiveIntegerField(default=0)),
                ('average_rating', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('csat_average', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('sla_met_count', models.PositiveIntegerField(default=0)),
                ('sla_breach_count', models.PositiveIntegerField(default=0)),
                ('sla_score', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('tier', models.CharField(choices=[('UNRATED', 'Unrated'), ('BRONZE', 'Bronze'), ('SILVER', 'Silver'), ('GOLD', 'Gold')], db_index=True, default='UNRATED', max_length=10)),
                ('last_recalculated_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='scorecard', to='employees.employee')),
            ],
            options={
                'db_table': 'workforce_scorecard',
            },
        ),
    ]
