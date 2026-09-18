import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0031_multi_vendor_orders_ledger_and_cart"),
        ("service_requests", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkforceDispatchState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "dispatch_status",
                    models.CharField(
                        choices=[
                            ("NEVER_ATTEMPTED", "Never Attempted"),
                            ("DISPATCHING", "Dispatching"),
                            ("RETRY_SCHEDULED", "Retry Scheduled"),
                            ("OFFER_ACTIVE", "Offer Active"),
                            ("ASSIGNED", "Assigned"),
                            ("CANCELLED", "Cancelled"),
                            ("COMPLETED", "Completed"),
                            ("EXPIRED", "Expired"),
                        ],
                        db_index=True,
                        default="NEVER_ATTEMPTED",
                        max_length=32,
                    ),
                ),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                (
                    "last_attempt_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "retry_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "unassigned_reason_code",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                (
                    "unassigned_reason_message",
                    models.TextField(blank=True, default=""),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dispatch_state",
                        to="service_requests.servicerequest",
                    ),
                ),
            ],
            options={
                "db_table": "workforce_dispatch_state",
            },
        ),
        migrations.AddIndex(
            model_name="workforcedispatchstate",
            index=models.Index(
                fields=["dispatch_status", "retry_at"],
                name="wf_disp_st_retry_idx",
            ),
        ),
    ]
