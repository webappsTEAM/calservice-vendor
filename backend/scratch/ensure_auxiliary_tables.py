import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

tables_to_ensure = [
    """
    CREATE TABLE IF NOT EXISTS workforce_quote_photo (
        id BIGSERIAL PRIMARY KEY,
        quote_id BIGINT NOT NULL REFERENCES workforce_quote(id) ON DELETE CASCADE,
        photo_url VARCHAR(500) NOT NULL,
        photo_type VARCHAR(50),
        caption VARCHAR(255) DEFAULT '',
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS workforce_painting_quote (
        id BIGSERIAL PRIMARY KEY,
        quote_id BIGINT UNIQUE NOT NULL REFERENCES workforce_quote(id) ON DELETE CASCADE,
        property_type VARCHAR(100) DEFAULT 'Apartment',
        rooms_detail JSONB DEFAULT '[]'::jsonb,
        area_sqft NUMERIC(10, 2) DEFAULT 0.00,
        surface_condition VARCHAR(100) DEFAULT 'Good',
        primer_required BOOLEAN DEFAULT FALSE,
        putty_required BOOLEAN DEFAULT FALSE,
        coats_count INTEGER DEFAULT 2,
        brand_preference VARCHAR(100) DEFAULT 'Asian Paints',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS workforce_quote_measurement (
        id BIGSERIAL PRIMARY KEY,
        quote_id BIGINT NOT NULL REFERENCES workforce_quote(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        measurement_type VARCHAR(50) DEFAULT 'ROOM',
        length NUMERIC(8, 2) DEFAULT 0.00,
        width NUMERIC(8, 2) DEFAULT 0.00,
        height NUMERIC(8, 2) DEFAULT 0.00,
        area NUMERIC(10, 2) DEFAULT 0.00,
        quantity NUMERIC(8, 2) DEFAULT 1.00,
        unit VARCHAR(50) DEFAULT 'sqft',
        notes TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
]

for ddl in tables_to_ensure:
    cursor.execute(ddl)
    print("DDL executed successfully.")

print("All missing workforce quote auxiliary tables ensured in new VPS DB.")
