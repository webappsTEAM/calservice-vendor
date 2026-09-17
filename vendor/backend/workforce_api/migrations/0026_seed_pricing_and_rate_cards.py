"""
Seed the commercial catalogue: pricing policies and rate cards.

Sources: painting_and_mason_quote_plan.md sections 3.1, 3.2, 4 and 8, and the
behaviour already in the code for AC estimation.

Two deliberate choices:

* AC Services keeps its flat Rs.199 consultation fee. That is what the four
  hardcoded literals in service_requests/vendor_views.py charged, so seeding it
  means nothing changes for AC on the day this deploys. The SEVO admin can move
  it to the distance rule from the pricing screen whenever they choose.

* The four pre-existing masonry services (Brick & Block, Plastering, Wall &
  Partition, Wall Breaking) are seeded QUOTE_ONLY with no rate. Neither plan
  document prices them and Caldim confirmed the quote prices them per site, so
  a fabricated rate would be worse than none: the evaluator refuses QUOTE_ONLY
  and tells the technician to enter the price, rather than silently applying a
  number nobody agreed.

Idempotent, and reversible by deleting only the rows it created.
"""
from decimal import Decimal

from django.db import migrations

HUB_LAT, HUB_LON = 12.7409, 77.8253

POLICIES = [
    {
        "service_category": "painting",
        "display_name": "Painting & Waterproofing",
        "consultation_fee_mode": "DISTANCE_BAND",
        "free_radius_km": Decimal("15.00"),
        "beyond_radius_amount": Decimal("300.00"),
        "high_value_review_threshold": Decimal("30000.00"),
        "advance_percent": Decimal("100.00"),
    },
    {
        "service_category": "painting & waterproofing",
        "display_name": "Painting & Waterproofing",
        "consultation_fee_mode": "DISTANCE_BAND",
        "free_radius_km": Decimal("15.00"),
        "beyond_radius_amount": Decimal("300.00"),
        "high_value_review_threshold": Decimal("30000.00"),
        "advance_percent": Decimal("100.00"),
    },
    {
        "service_category": "mason",
        "display_name": "Masonry & Civil",
        "consultation_fee_mode": "DISTANCE_BAND",
        "free_radius_km": Decimal("15.00"),
        "beyond_radius_amount": Decimal("300.00"),
        "high_value_review_threshold": None,
        "advance_percent": Decimal("50.00"),
    },
    {
        "service_category": "masonry",
        "display_name": "Masonry & Civil",
        "consultation_fee_mode": "DISTANCE_BAND",
        "free_radius_km": Decimal("15.00"),
        "beyond_radius_amount": Decimal("300.00"),
        "high_value_review_threshold": None,
        "advance_percent": Decimal("50.00"),
    },
    {
        "service_category": "masonry & civil",
        "display_name": "Masonry & Civil",
        "consultation_fee_mode": "DISTANCE_BAND",
        "free_radius_km": Decimal("15.00"),
        "beyond_radius_amount": Decimal("300.00"),
        "high_value_review_threshold": None,
        "advance_percent": Decimal("50.00"),
    },
    {
        "service_category": "AC Services",
        "display_name": "AC Repair & Service",
        "consultation_fee_mode": "FLAT",
        "consultation_fee_amount": Decimal("199.00"),
        "high_value_review_threshold": None,
        "advance_percent": Decimal("100.00"),
    },
]

PAINT = "painting"
MASON = "mason"

RATE_CARDS = [
    # ---- Waterproofing (painting plan 3.1) -----------------------------------
    dict(service_category=PAINT, service_name="Waterproofing", section="MATERIAL",
         item_name="3 mm Tar Sheet / Gas Heating Waterproofing", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("100.00"),
         warranty_tier="10_YEAR", advance_percent=Decimal("50.00"), sort_order=10),
    dict(service_category=PAINT, service_name="Waterproofing", section="MATERIAL",
         item_name="Terrace Waterproofing - 4 Coat", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("50.00"),
         warranty_tier="5_YEAR", advance_percent=Decimal("50.00"), sort_order=20),
    dict(service_category=PAINT, service_name="Waterproofing", section="MATERIAL",
         item_name="Terrace Waterproofing - 2 Coat", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("20.00"),
         advance_percent=Decimal("50.00"), sort_order=30),
    dict(service_category=PAINT, service_name="Waterproofing", section="MATERIAL",
         item_name="Roof Repair / Patch Work", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("25.00"),
         advance_percent=Decimal("50.00"), sort_order=40),
    dict(service_category=PAINT, service_name="Waterproofing", section="MATERIAL",
         item_name="PU Coating / Dampness Treatment", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("35.00"),
         advance_percent=Decimal("50.00"), sort_order=50),

    # ---- Painting (painting plan 3.1) ---------------------------------------
    dict(service_category=PAINT, service_name="Interior Painting", section="MATERIAL",
         item_name="Premium Interior Emulsion", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("15.00"), sort_order=60),
    dict(service_category=PAINT, service_name="Interior Painting", section="MATERIAL",
         item_name="Ceiling Painting", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("12.00"), sort_order=70),
    dict(service_category=PAINT, service_name="Exterior Painting", section="MATERIAL",
         item_name="Weatherproof Exterior Emulsion", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("18.00"), sort_order=80),
    dict(service_category=PAINT, service_name="Wood & Metal", section="MATERIAL",
         item_name="PU Coat Gates, Doors & Grills", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("85.00"), sort_order=90),
    dict(service_category=PAINT, service_name="Texture Decor", section="MATERIAL",
         item_name="Royal Texture Play / Stencil Design", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("120.00"), sort_order=100),

    # ---- Fixed slabs (painting plan 3.2) ------------------------------------
    dict(service_category=PAINT, service_name="Waterproofing", section="MATERIAL",
         item_name="Industrial Epoxy Flooring", unit="sqft",
         pricing_model="TIERED",
         pricing_config={"tiers": {"1mm": 60, "2mm": 90, "3mm": 110}},
         default_rate=Decimal("60.00"), advance_percent=Decimal("50.00"), sort_order=110,
         description="Thickness decides the rate: 1 mm Rs.60, 2 mm Rs.90, 3 mm Rs.110 per sq.ft."),
    dict(service_category=PAINT, service_name="Waterproofing", section="MATERIAL",
         item_name="Water Tank Waterproofing", unit="litre",
         pricing_model="CAPACITY_BAND",
         pricing_config={"bands": [
             {"max": 1000, "flat": 1700, "label": "Up to 1,000 L - flat Rs.1,700"},
             {"max": 5000, "rate": 1.5, "label": "1,000-5,000 L - Rs.1.50 per litre"},
             {"max": 10000, "flat": 17000, "label": "5,000-10,000 L - flat Rs.17,000"},
             {"max": None, "flat": 17000, "label": "Above 10,000 L - flat Rs.17,000"},
         ]},
         advance_percent=Decimal("50.00"), sort_order=120,
         description="10,000 L water sump priced at flat Rs.17,000. 1-5 kL priced at Rs.1.50/L."),
    dict(service_category=PAINT, service_name="Waterproofing", section="MATERIAL",
         item_name="Bathroom Waterproofing", unit="sqft",
         pricing_model="SIZE_BAND",
         pricing_config={"bands": [
             {"max": 50, "flat": 3500, "label": "Small / Medium (4x4 to 5x5, up to 50 sq.ft) - flat Rs.3,500"},
             {"max": None, "flat": 8000, "label": "Large (10x10, above 50 sq.ft) - flat Rs.8,000"},
         ]},
         advance_percent=Decimal("50.00"), sort_order=130,
         description="Small/Medium (4x4 to 5x5) flat Rs.3,500; Large (10x10) flat Rs.8,000."),

    # ---- Masonry: the two from the plan (section 4) --------------------------
    dict(service_category=MASON, service_name="Bathroom Tile Fixing", section="LABOUR",
         item_name="Bathroom Tile Fixing", unit="sqft",
         pricing_model="SIZE_BAND",
         pricing_config={"bands": [
             {"max": 80, "flat": 10000, "label": "Up to 80 sq.ft - flat Rs.10,000"},
             {"max": None, "flat": 20000, "label": "Above 80 sq.ft - flat Rs.20,000"},
         ]},
         advance_percent=Decimal("50.00"), sort_order=10,
         description="Surface levelling, adhesive laying, spacers, epoxy waterproof grout."),
    dict(service_category=MASON, service_name="Minor Masonry", section="LABOUR",
         item_name="Minor Masonry & Small Construction", unit="sqft",
         pricing_model="PER_UNIT", default_rate=Decimal("120.00"),
         minimum_quantity=Decimal("500.00"), advance_percent=Decimal("50.00"), sort_order=20,
         description="M-sand, cement, bricks/blocks, wall building, plaster levelling. "
                     "Minimum 500 sq.ft."),

    # ---- Masonry: the four already in the catalogue (D5 - kept, priced per quote)
    dict(service_category=MASON, service_name="Brick & Block Work", section="LABOUR",
         item_name="Brick & Block Work", unit="sqft", pricing_model="QUOTE_ONLY",
         advance_percent=Decimal("50.00"), sort_order=30,
         description="No standard rate agreed; priced on site."),
    dict(service_category=MASON, service_name="Plastering & Wall Repair", section="LABOUR",
         item_name="Plastering & Wall Repair", unit="sqft", pricing_model="QUOTE_ONLY",
         advance_percent=Decimal("50.00"), sort_order=40,
         description="No standard rate agreed; priced on site."),
    dict(service_category=MASON, service_name="Wall & Partition Construction", section="LABOUR",
         item_name="Wall & Partition Construction", unit="sqft", pricing_model="QUOTE_ONLY",
         advance_percent=Decimal("50.00"), sort_order=50,
         description="No standard rate agreed; priced on site."),
    dict(service_category=MASON, service_name="Wall Breaking & Demolition", section="LABOUR",
         item_name="Wall Breaking & Demolition", unit="sqft", pricing_model="QUOTE_ONLY",
         advance_percent=Decimal("50.00"), sort_order=60,
         description="No standard rate agreed; priced on site."),
]


def seed(apps, schema_editor):
    Policy = apps.get_model("workforce_api", "WorkforceServicePricingPolicy")
    RateCard = apps.get_model("workforce_api", "WorkforceRateCard")

    for row in POLICIES:
        Policy.objects.update_or_create(
            service_category=row["service_category"],
            defaults={
                "hub_latitude": HUB_LAT,
                "hub_longitude": HUB_LON,
                "requires_admin_approval": True,
                "allow_customer_supplied_materials": False,
                "is_active": True,
                **row,
            },
        )

    for row in RATE_CARDS:
        data = dict(row)
        RateCard.objects.update_or_create(
            service_category=data.pop("service_category"),
            item_name=data.pop("item_name"),
            defaults={"is_active": True, "tax_rate": Decimal("18.00"), **data},
        )


def unseed(apps, schema_editor):
    Policy = apps.get_model("workforce_api", "WorkforceServicePricingPolicy")
    RateCard = apps.get_model("workforce_api", "WorkforceRateCard")
    Policy.objects.filter(
        service_category__in=[p["service_category"] for p in POLICIES]
    ).delete()
    for row in RATE_CARDS:
        RateCard.objects.filter(
            service_category=row["service_category"], item_name=row["item_name"]
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0025_pricing_policy_rate_cards_and_schedule"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
