import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_service_configurations_and_skills(apps, schema_editor):
    Service = apps.get_model("service_requests", "Service")
    WorkforceServiceConfiguration = apps.get_model("workforce_api", "WorkforceServiceConfiguration")
    WorkforceEmployeeService = apps.get_model("workforce_api", "WorkforceEmployeeService")
    Employee = apps.get_model("employees", "Employee")

    # 1. Seed Service Configurations
    try:
        services = Service.objects.all()
        for svc in services:
            name_lower = (svc.name or "").lower()
            cat_name = ""
            if hasattr(svc, "category") and svc.category:
                cat_name = (svc.category.name or "").lower()

            is_ac = "ac " in name_lower or "air conditioner" in name_lower or "hvac" in name_lower or "ac" in cat_name
            is_paint = "paint" in name_lower or "waterproof" in name_lower or "paint" in cat_name
            is_mason = "mason" in name_lower or "tile" in name_lower or "mason" in cat_name

            if is_ac:
                WorkforceServiceConfiguration.objects.update_or_create(
                    service=svc,
                    defaults={
                        "booking_flow": "ESTIMATION",
                        "estimation_required": True,
                        "quotation_required": True,
                        "estimation_form_type": "AC_INSPECTION",
                        "quotation_form_type": "AC_REPAIR",
                        "pricing_mode": "RATE_CARD",
                        "consultation_fee_policy": {"fee_amount": 199.00, "currency": "INR", "waivable": True},
                    }
                )
            elif is_paint:
                WorkforceServiceConfiguration.objects.update_or_create(
                    service=svc,
                    defaults={
                        "booking_flow": "ESTIMATION",
                        "estimation_required": True,
                        "quotation_required": True,
                        "estimation_form_type": "PAINTING_INSPECTION",
                        "quotation_form_type": "PAINTING",
                        "pricing_mode": "MEASUREMENT",
                        "consultation_fee_policy": {"fee_amount": 199.00, "currency": "INR", "waivable": True},
                    }
                )
            elif is_mason:
                WorkforceServiceConfiguration.objects.update_or_create(
                    service=svc,
                    defaults={
                        "booking_flow": "ESTIMATION",
                        "estimation_required": True,
                        "quotation_required": True,
                        "estimation_form_type": "MASON_INSPECTION",
                        "quotation_form_type": "MASONRY",
                        "pricing_mode": "MEASUREMENT",
                        "consultation_fee_policy": {"fee_amount": 199.00, "currency": "INR", "waivable": True},
                    }
                )
    except Exception as e:
        print(f"Warning: Could not seed service configurations: {e}")

    # 2. Backfill approved skills from Employee.bank_details into WorkforceEmployeeService
    try:
        employees = Employee.objects.filter(is_active=True)
        for emp in employees:
            bank_details = emp.bank_details or {}
            onboarding = bank_details.get("onboarding", {})
            svcs = onboarding.get("services", [])
            for s in svcs:
                s_id = s.get("id")
                s_status = (s.get("status") or "").upper()
                if s_id and s_status == "APPROVED":
                    try:
                        svc_obj = Service.objects.filter(id=int(s_id)).first()
                        if svc_obj:
                            WorkforceEmployeeService.objects.update_or_create(
                                employee=emp,
                                service=svc_obj,
                                defaults={"status": "APPROVED"}
                            )
                    except Exception:
                        pass
    except Exception as e:
        print(f"Warning: Could not backfill employee services: {e}")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('service_requests', '__first__'),
        ('employees', '__first__'),
        ('workforce_api', '0021_merge_20260902_1700'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkforceServiceConfiguration',
            fields=[
                ('service', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='workflow_config', serialize=False, to='service_requests.service')),
                ('booking_flow', models.CharField(choices=[('STANDARD', 'Standard Booking'), ('ESTIMATION', 'Estimation Required')], default='STANDARD', max_length=30)),
                ('estimation_required', models.BooleanField(default=False)),
                ('quotation_required', models.BooleanField(default=False)),
                ('estimation_form_type', models.CharField(blank=True, default='', max_length=50)),
                ('quotation_form_type', models.CharField(blank=True, default='', max_length=50)),
                ('pricing_mode', models.CharField(choices=[('FIXED', 'Fixed / Standard Price'), ('RATE_CARD', 'Rate Card Based'), ('MEASUREMENT', 'Measurement / Area Based'), ('FLAT_TIER', 'Tiered Flat Slab')], default='FIXED', max_length=30)),
                ('consultation_fee_policy', models.JSONField(blank=True, default=dict)),
                ('payment_policy', models.JSONField(blank=True, default=dict)),
                ('approval_policy', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'workforce_service_configuration',
            },
        ),
        migrations.CreateModel(
            name='WorkforceEmployeeService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('PENDING', 'Pending Review'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('SUSPENDED', 'Suspended')], db_index=True, default='PENDING', max_length=20)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='authorized_services', to='employees.employee')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='authorized_employees', to='service_requests.service')),
            ],
            options={
                'db_table': 'workforce_employee_service',
            },
        ),
        migrations.AddField(
            model_name='workforcequote',
            name='estimation_quotation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='workforce_quotes', to='service_requests.estimationquotation'),
        ),
        migrations.AddIndex(
            model_name='workforceemployeeservice',
            index=models.Index(fields=['service', 'status'], name='workforce_e_service_36dfa2_idx'),
        ),
        migrations.AddIndex(
            model_name='workforceemployeeservice',
            index=models.Index(fields=['employee', 'status'], name='workforce_e_employe_3457a1_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='workforceemployeeservice',
            unique_together={('employee', 'service')},
        ),
        migrations.RunPython(
            seed_service_configurations_and_skills,
            noop_reverse,
        ),
    ]
