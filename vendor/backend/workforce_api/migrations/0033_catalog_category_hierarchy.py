"""
workforce_api 0033 – CatalogCategory hierarchical parent_id column and index
Supports multi-level parent/child categories in service_requests_catalogcategory.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0032_vendor_store_onboarding"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'service_requests_catalogcategory' 
                    AND column_name = 'parent_id'
                ) THEN
                    ALTER TABLE service_requests_catalogcategory 
                    ADD COLUMN parent_id BIGINT NULL 
                    REFERENCES service_requests_catalogcategory(id) ON DELETE CASCADE;
                END IF;
            END $$;

            CREATE INDEX IF NOT EXISTS service_requests_catalogcategory_parent_id_idx 
            ON service_requests_catalogcategory(parent_id);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS service_requests_catalogcategory_parent_id_idx;
            ALTER TABLE service_requests_catalogcategory DROP COLUMN IF EXISTS parent_id;
            """
        ),
    ]
