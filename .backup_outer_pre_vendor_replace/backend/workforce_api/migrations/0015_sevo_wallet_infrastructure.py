# Hand-written migration -- see 0013_vehicle_and_doc_categories.py /
# 0014_gt_c02_cash_settlement.py for why (no way to run
# `manage.py makemigrations` against a matching environment in this
# sandbox -- the project venv is a Windows venv only usable from the
# user's own machine). Verified by loading via importlib against a
# locally-installed Django to confirm the Migration class parses and
# matches the model definitions -- not verified against the live
# database. Run `python manage.py makemigrations --check --dry-run`
# before applying to confirm no drift.
#
# SEVO business-plan implementation, Section 1 (wallet infrastructure) and
# Section 8 (Social Security Code registration tracking) -- see the model
# docstrings in workforce_api/models.py for the full rationale.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workforce_api', '0014_gt_c02_cash_settlement'),
        ('employees', '__first__'),
        ('companies', '__first__'),
        ('service_requests', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='WalletAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_type', models.CharField(choices=[('PROVIDER_HEAD', 'Provider Head Wallet'), ('INDIVIDUAL_WORKER', 'Individual Worker Wallet')], db_index=True, max_length=30)),
                ('kyc_tier', models.CharField(choices=[('TIER_0', 'Tier 0 - Provisional'), ('TIER_1', 'Tier 1 - Verified'), ('TIER_2', 'Tier 2 - Trusted')], db_index=True, default='TIER_0', max_length=10)),
                ('kyc_tier_updated_at', models.DateTimeField(blank=True, null=True)),
                ('payout_bank_account_name', models.CharField(blank=True, default='', max_length=200)),
                ('payout_bank_account_number_masked', models.CharField(blank=True, default='', max_length=50)),
                ('payout_ifsc', models.CharField(blank=True, default='', max_length=20)),
                ('payout_upi_id', models.CharField(blank=True, default='', max_length=100)),
                ('razorpayx_contact_id', models.CharField(blank=True, default='', max_length=100)),
                ('razorpayx_fund_account_id', models.CharField(blank=True, default='', max_length=100)),
                ('auto_withdrawal_enabled', models.BooleanField(default=False)),
                ('auto_withdrawal_frequency', models.CharField(blank=True, choices=[('DAILY', 'Daily'), ('WEEKLY', 'Weekly')], default='', max_length=10)),
                ('auto_withdrawal_day_of_week', models.IntegerField(blank=True, help_text='0=Monday .. 6=Sunday. Only used when frequency=WEEKLY.', null=True)),
                ('minimum_balance_alert_threshold', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('low_balance_alert_sent_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='head_wallet', to='companies.company')),
                ('employee', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='individual_wallet', to='employees.employee')),
            ],
            options={
                'db_table': 'workforce_wallet_account',
            },
        ),
        migrations.AddIndex(
            model_name='walletaccount',
            index=models.Index(fields=['account_type', 'kyc_tier'], name='workforce_w_account_5f0a1a_idx'),
        ),
        migrations.AddConstraint(
            model_name='walletaccount',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(('account_type', 'PROVIDER_HEAD'), ('company__isnull', False), ('employee__isnull', True))
                    | models.Q(('account_type', 'INDIVIDUAL_WORKER'), ('employee__isnull', False), ('company__isnull', True))
                ),
                name='wallet_account_type_matches_owner',
            ),
        ),
        migrations.CreateModel(
            name='WalletLedgerEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_type', models.CharField(choices=[('JOB_CREDIT', 'Job Earnings Credit'), ('COMMISSION_DEBIT', 'SEVO Commission'), ('WITHDRAWAL_DEBIT', 'Withdrawal to Bank/UPI'), ('CLAWBACK_DEBIT', 'Dispute Clawback'), ('REFUND_ADJUSTMENT', 'Refund Adjustment'), ('PROMO_CREDIT', 'Promotional Credit'), ('COD_COMMISSION_PAYABLE', 'Cash Job Commission Payable')], db_index=True, max_length=30)),
                ('signed_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('gross_job_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('commission_rate_applied', models.DecimalField(blank=True, decimal_places=4, help_text='e.g. 0.1000 for 10%. Recorded per-entry since the rate can change (promo -> standard).', max_digits=5, null=True)),
                ('status', models.CharField(choices=[('HELD', 'Held (dispute window)'), ('RELEASED', 'Released (withdrawable)'), ('CLAWED_BACK', 'Clawed back')], db_index=True, default='RELEASED', max_length=15)),
                ('hold_release_at', models.DateTimeField(blank=True, help_text='JOB_CREDIT entries are held until this timestamp (dispute window) before counting toward balance.', null=True)),
                ('notes', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('job', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='wallet_ledger_entries', to='service_requests.servicerequest')),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ledger_entries', to='workforce_api.walletaccount')),
                ('worker_performed', models.ForeignKey(blank=True, help_text='Who actually did the job, independent of which wallet was paid.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='jobs_performed_ledger_entries', to='employees.employee')),
            ],
            options={
                'db_table': 'workforce_wallet_ledger_entry',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='walletledgerentry',
            index=models.Index(fields=['wallet', 'status', 'created_at'], name='workforce_w_wallet__1e2b3c_idx'),
        ),
        migrations.AddIndex(
            model_name='walletledgerentry',
            index=models.Index(fields=['job', 'entry_type'], name='workforce_w_job_id_2f9d4e_idx'),
        ),
        migrations.CreateModel(
            name='WithdrawalRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('SUCCESS', 'Success'), ('FAILED', 'Failed'), ('AWAITING_RAZORPAYX_ACTIVATION', 'Awaiting RazorpayX activation')], db_index=True, default='PENDING', max_length=35)),
                ('is_scheduled', models.BooleanField(default=False, help_text='True if triggered by an auto-withdrawal rule rather than an on-demand request.')),
                ('razorpayx_payout_id', models.CharField(blank=True, default='', max_length=100)),
                ('razorpayx_utr', models.CharField(blank=True, default='', help_text='Bank UTR once settled, from RazorpayX webhook.', max_length=100)),
                ('failure_reason', models.CharField(blank=True, default='', max_length=255)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('debit_ledger_entry', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='withdrawal_request', to='workforce_api.walletledgerentry')),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='withdrawal_requests', to='workforce_api.walletaccount')),
            ],
            options={
                'db_table': 'workforce_withdrawal_request',
                'ordering': ['-requested_at'],
            },
        ),
        migrations.AddIndex(
            model_name='withdrawalrequest',
            index=models.Index(fields=['wallet', 'status'], name='workforce_w_wallet__7a6d5f_idx'),
        ),
        migrations.CreateModel(
            name='SocialSecurityRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('days_worked_current_fy', models.PositiveIntegerField(default=0)),
                ('financial_year_start', models.DateField()),
                ('status', models.CharField(choices=[('NOT_YET_ELIGIBLE', 'Not yet eligible (<90 days)'), ('ELIGIBLE_PENDING', 'Eligible, registration pending'), ('REGISTERED', 'Registered on government portal')], db_index=True, default='NOT_YET_ELIGIBLE', max_length=25)),
                ('registered_at', models.DateTimeField(blank=True, null=True)),
                ('registered_by', models.CharField(blank=True, default='', help_text='Admin who submitted the portal registration.', max_length=150)),
                ('portal_reference_id', models.CharField(blank=True, default='', max_length=100)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='social_security_registration', to='employees.employee')),
            ],
            options={
                'db_table': 'workforce_social_security_registration',
            },
        ),
    ]
