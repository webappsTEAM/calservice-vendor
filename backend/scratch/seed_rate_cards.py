import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

from workforce_api.models import WorkforceRateCard

RATE_CARD_SEEDS = [
    # Painting - Material
    {"service_category": "painting", "service_name": "Interior Painting", "section": "MATERIAL", "item_name": "Economy Interior Emulsion", "unit": "litre", "default_rate": 280.00, "default_cost": 220.00, "tax_rate": 18.00, "max_discount_percent": 15.00, "sort_order": 1},
    {"service_category": "painting", "service_name": "Interior Painting", "section": "MATERIAL", "item_name": "Premium Interior Emulsion", "unit": "litre", "default_rate": 450.00, "default_cost": 360.00, "tax_rate": 18.00, "max_discount_percent": 15.00, "sort_order": 2},
    {"service_category": "painting", "service_name": "Interior Painting", "section": "MATERIAL", "item_name": "Luxury Interior Emulsion (Royale)", "unit": "litre", "default_rate": 650.00, "default_cost": 520.00, "tax_rate": 18.00, "max_discount_percent": 15.00, "sort_order": 3},
    {"service_category": "painting", "service_name": "Interior Painting", "section": "MATERIAL", "item_name": "Acrylic Wall Putty (2 Coats)", "unit": "kg", "default_rate": 45.00, "default_cost": 32.00, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 4},
    {"service_category": "painting", "service_name": "Interior Painting", "section": "MATERIAL", "item_name": "Interior Primer (Water Based)", "unit": "litre", "default_rate": 210.00, "default_cost": 160.00, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 5},
    {"service_category": "painting", "service_name": "Exterior Painting", "section": "MATERIAL", "item_name": "Weather-Defense Exterior Emulsion", "unit": "litre", "default_rate": 520.00, "default_cost": 410.00, "tax_rate": 18.00, "max_discount_percent": 15.00, "sort_order": 6},
    {"service_category": "painting", "service_name": "Waterproofing", "section": "MATERIAL", "item_name": "SmartCare Damp Proof Waterproof Coating", "unit": "litre", "default_rate": 580.00, "default_cost": 460.00, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 7},

    # Painting - Labour & Prep
    {"service_category": "painting", "service_name": "Interior Painting", "section": "LABOUR", "item_name": "Standard Interior Wall Painting Labour (2 Coats)", "unit": "sqft", "default_rate": 12.00, "default_cost": 9.00, "tax_rate": 18.00, "max_discount_percent": 15.00, "sort_order": 10},
    {"service_category": "painting", "service_name": "Interior Painting", "section": "LABOUR", "item_name": "Ceiling Painting Labour", "unit": "sqft", "default_rate": 14.00, "default_cost": 10.50, "tax_rate": 18.00, "max_discount_percent": 15.00, "sort_order": 11},
    {"service_category": "painting", "service_name": "Interior Painting", "section": "SURFACE_PREP", "item_name": "Sanding, Scraping & Crack Filling", "unit": "sqft", "default_rate": 6.00, "default_cost": 4.50, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 12},
    {"service_category": "painting", "service_name": "Interior Painting", "section": "SURFACE_PREP", "item_name": "Deep Crack Mesh & Polymer Treatment", "unit": "sqft", "default_rate": 18.00, "default_cost": 14.00, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 13},
    {"service_category": "painting", "service_name": "Exterior Painting", "section": "EQUIPMENT", "item_name": "External Scaffolding & Safety Rigging", "unit": "job", "default_rate": 4500.00, "default_cost": 3500.00, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 14},

    # Mason - Brickwork, Plastering, Demolition
    {"service_category": "mason", "service_name": "Brick & Block Work", "section": "MATERIAL", "item_name": "Red Clay Bricks (Standard Grade)", "unit": "piece", "default_rate": 12.00, "default_cost": 9.50, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 20},
    {"service_category": "mason", "service_name": "Brick & Block Work", "section": "MATERIAL", "item_name": "Portland Pozzolana Cement (50kg Bag)", "unit": "bag", "default_rate": 420.00, "default_cost": 360.00, "tax_rate": 18.00, "max_discount_percent": 5.00, "sort_order": 21},
    {"service_category": "mason", "service_name": "Brick & Block Work", "section": "MATERIAL", "item_name": "Manufactured Sand (M-Sand / Plaster Sand)", "unit": "ton", "default_rate": 1600.00, "default_cost": 1300.00, "tax_rate": 18.00, "max_discount_percent": 5.00, "sort_order": 22},
    {"service_category": "mason", "service_name": "Brick & Block Work", "section": "LABOUR", "item_name": "9-inch Brickwork Masonry Labour", "unit": "sqft", "default_rate": 45.00, "default_cost": 35.00, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 23},
    {"service_category": "mason", "service_name": "Plastering & Wall Repair", "section": "LABOUR", "item_name": "Internal Plastering (12mm Smooth Finish)", "unit": "sqft", "default_rate": 28.00, "default_cost": 22.00, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 24},
    {"service_category": "mason", "service_name": "Wall Breaking & Demolition", "section": "LABOUR", "item_name": "Non-Load Bearing Partition Demolition", "unit": "sqft", "default_rate": 35.00, "default_cost": 26.00, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 25},
    {"service_category": "mason", "service_name": "Wall Breaking & Demolition", "section": "TRANSPORT", "item_name": "Construction Debris Disposal & Site Clearance", "unit": "truck_load", "default_rate": 2800.00, "default_cost": 2200.00, "tax_rate": 18.00, "max_discount_percent": 10.00, "sort_order": 26},
]

created_count = 0
for data in RATE_CARD_SEEDS:
    obj, created = WorkforceRateCard.objects.get_or_create(
        service_category=data["service_category"],
        section=data["section"],
        item_name=data["item_name"],
        defaults=data
    )
    if created:
        created_count += 1

print(f"Seeded {created_count} new rate card entries. Total active rate cards: {WorkforceRateCard.objects.count()}")
