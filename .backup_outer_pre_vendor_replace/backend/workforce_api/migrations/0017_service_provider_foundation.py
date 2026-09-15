"""
Migration 0017: Workforce Service Provider Foundation
- Drops NOT NULL constraint on employees_employee.company_id to support independent employees (company_id = NULL).
- Migrates existing platform administrators (is_superuser=True or role='super_admin') to canonical role 'superadmin'.
- Preserves all existing employee, company, and job assignments without data loss.
"""
from django.db import migrations


def migrate_platform_superadmins(apps, schema_editor):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Update existing platform superusers or explicit super_admin accounts to canonical 'superadmin'
    updated_count = User.objects.filter(
        models_Q_or_filter(User)
    ).update(role="superadmin")
    print(f"Migrated {updated_count} existing platform administrator(s) to role='superadmin'.")


def models_Q_or_filter(User):
    from django.db.models import Q
    return Q(is_superuser=True) | Q(role="super_admin")


def reverse_platform_superadmins(apps, schema_editor):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Reverse canonical superadmin back to super_admin or admin
    User.objects.filter(role="superadmin", is_superuser=True).update(role="admin")


class Migration(migrations.Migration):

    dependencies = [
        ('workforce_api', '0016_merge_performance_indexes_and_location_hardening'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE employees_employee ALTER COLUMN company_id DROP NOT NULL;
                ALTER TABLE accounts_user ALTER COLUMN role TYPE character varying(50);
            """,
            reverse_sql="-- Irreversible without backfilling null company_id values",
        ),
        migrations.RunPython(
            migrate_platform_superadmins,
            reverse_code=reverse_platform_superadmins,
        ),
    ]
