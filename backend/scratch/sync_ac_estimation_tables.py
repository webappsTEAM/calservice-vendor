import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()
from django.db import connection

sql_statements = [
    """
    CREATE TABLE IF NOT EXISTS service_requests_estimation (
        id BIGSERIAL PRIMARY KEY,
        ac_type VARCHAR(50) DEFAULT 'SPLIT',
        ac_brand VARCHAR(100) DEFAULT 'General',
        ac_capacity VARCHAR(50) DEFAULT '1.5_TON',
        ac_quantity SMALLINT DEFAULT 1,
        customer_symptom TEXT DEFAULT '',
        customer_notes TEXT DEFAULT '',
        status VARCHAR(30) DEFAULT 'REQUESTED',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        service_request_id BIGINT REFERENCES service_requests_servicerequest(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS service_requests_estimationfee (
        id BIGSERIAL PRIMARY KEY,
        amount NUMERIC(10, 2) DEFAULT 199.00,
        currency VARCHAR(10) DEFAULT 'INR',
        status VARCHAR(30) DEFAULT 'PENDING',
        payment_reference VARCHAR(100) DEFAULT '',
        payment_method VARCHAR(50) DEFAULT '',
        collected_at TIMESTAMP WITH TIME ZONE,
        waived_at TIMESTAMP WITH TIME ZONE,
        waived_reason TEXT DEFAULT '',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        estimation_id BIGINT REFERENCES service_requests_estimation(id) ON DELETE CASCADE,
        waived_by_id BIGINT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS service_requests_inspection (
        id BIGSERIAL PRIMARY KEY,
        technician_external_id VARCHAR(100) DEFAULT '',
        technician_name VARCHAR(200) DEFAULT '',
        technician_phone VARCHAR(50) DEFAULT '',
        status VARCHAR(30) DEFAULT 'PENDING',
        diagnosis TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        estimation_id BIGINT REFERENCES service_requests_estimation(id) ON DELETE CASCADE,
        technician_id BIGINT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS service_requests_inspectionfinding (
        id BIGSERIAL PRIMARY KEY,
        finding_type VARCHAR(100) DEFAULT 'Other',
        title VARCHAR(255) NOT NULL,
        diagnosis TEXT DEFAULT '',
        severity VARCHAR(30) DEFAULT 'MEDIUM',
        description TEXT DEFAULT '',
        recommended_action TEXT DEFAULT '',
        quantity NUMERIC(10, 2) DEFAULT 1.00,
        unit VARCHAR(50) DEFAULT 'unit',
        sort_order SMALLINT DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        inspection_id BIGINT REFERENCES service_requests_inspection(id) ON DELETE CASCADE,
        service_id BIGINT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS service_requests_inspectionphoto (
        id BIGSERIAL PRIMARY KEY,
        photo VARCHAR(500) NOT NULL,
        caption VARCHAR(255) DEFAULT '',
        uploaded_by VARCHAR(100) DEFAULT 'technician',
        uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        inspection_id BIGINT REFERENCES service_requests_inspection(id) ON DELETE CASCADE,
        finding_id BIGINT REFERENCES service_requests_inspectionfinding(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS service_requests_estimationquotation (
        id BIGSERIAL PRIMARY KEY,
        version SMALLINT DEFAULT 1,
        quote_ref VARCHAR(100) UNIQUE,
        status VARCHAR(30) DEFAULT 'DRAFT',
        vendor_id VARCHAR(100) DEFAULT '',
        technician_id VARCHAR(100) DEFAULT '',
        subtotal NUMERIC(12, 2) DEFAULT 0.00,
        tax_amount NUMERIC(12, 2) DEFAULT 0.00,
        discount_amount NUMERIC(12, 2) DEFAULT 0.00,
        total_amount NUMERIC(12, 2) DEFAULT 0.00,
        currency VARCHAR(10) DEFAULT 'INR',
        notes TEXT DEFAULT '',
        valid_until DATE,
        customer_approved_at TIMESTAMP WITH TIME ZONE,
        customer_rejected_at TIMESTAMP WITH TIME ZONE,
        rejection_reason VARCHAR(100) DEFAULT '',
        rejection_note TEXT DEFAULT '',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        estimation_id BIGINT REFERENCES service_requests_estimation(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS service_requests_estimationquotationitem (
        id BIGSERIAL PRIMARY KEY,
        catalog_service_id VARCHAR(100) DEFAULT '',
        service_name VARCHAR(255) NOT NULL,
        description TEXT DEFAULT '',
        quantity NUMERIC(10, 2) DEFAULT 1.00,
        unit VARCHAR(50) DEFAULT 'unit',
        unit_price NUMERIC(12, 2) DEFAULT 0.00,
        tax_rate NUMERIC(5, 2) DEFAULT 0.00,
        tax_amount NUMERIC(12, 2) DEFAULT 0.00,
        discount_amount NUMERIC(12, 2) DEFAULT 0.00,
        line_total NUMERIC(12, 2) DEFAULT 0.00,
        sort_order SMALLINT DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        quotation_id BIGINT REFERENCES service_requests_estimationquotation(id) ON DELETE CASCADE,
        service_id BIGINT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS settings_hub_invoice (
        id BIGSERIAL PRIMARY KEY,
        invoice_number VARCHAR(100) UNIQUE,
        amount NUMERIC(12, 2) DEFAULT 0.00,
        currency VARCHAR(10) DEFAULT 'INR',
        status VARCHAR(30) DEFAULT 'PAID',
        billing_date DATE,
        due_date DATE,
        pdf_url VARCHAR(500) DEFAULT '',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        company_id BIGINT
    );
    """
]

with connection.cursor() as cursor:
    for stmt in sql_statements:
        cursor.execute(stmt)
    print("All AC Estimation tables created/verified successfully in PostgreSQL!")
