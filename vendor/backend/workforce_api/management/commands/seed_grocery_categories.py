"""
Management command: seed_grocery_categories
Idempotently seeds a comprehensive 3-level grocery department category hierarchy.

Rules:
- Default mode is DRY-RUN (no database writes).
- Writes only when --commit flag is provided.
- Uses slug for idempotent matching (get_or_create).
- Never deletes or overwrites existing categories.
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from workforce_api.models import SellerHubCategory


GROCERY_TAXONOMY = [
    {
        "name": "Fruits & Vegetables",
        "slug": "fruits-vegetables",
        "sort_order": 10,
        "children": [
            {
                "name": "Fresh Vegetables",
                "slug": "fresh-vegetables",
                "sort_order": 10,
                "children": [
                    {"name": "Potatoes, Onions & Tomatoes", "slug": "potatoes-onions-tomatoes", "sort_order": 10},
                    {"name": "Leafy Greens & Herbs", "slug": "leafy-greens-herbs", "sort_order": 20},
                    {"name": "Root & Gourd Vegetables", "slug": "root-gourd-vegetables", "sort_order": 30},
                    {"name": "Exotic Vegetables & Mushrooms", "slug": "exotic-vegetables-mushrooms", "sort_order": 40},
                ],
            },
            {
                "name": "Fresh Fruits",
                "slug": "fresh-fruits",
                "sort_order": 20,
                "children": [
                    {"name": "Apples, Pears & Pomegranates", "slug": "apples-pears-pomegranates", "sort_order": 10},
                    {"name": "Bananas & Melons", "slug": "bananas-melons", "sort_order": 20},
                    {"name": "Citrus & Seasonal Fruits", "slug": "citrus-seasonal-fruits", "sort_order": 30},
                    {"name": "Berries & Exotic Fruits", "slug": "berries-exotic-fruits", "sort_order": 40},
                ],
            },
            {
                "name": "Organic & Hydroponic Produce",
                "slug": "organic-hydroponic-produce",
                "sort_order": 30,
                "children": [
                    {"name": "Organic Vegetables", "slug": "organic-vegetables", "sort_order": 10},
                    {"name": "Organic Fruits", "slug": "organic-fruits", "sort_order": 20},
                    {"name": "Hydroponic Salad Greens", "slug": "hydroponic-salad-greens", "sort_order": 30},
                ],
            },
        ],
    },
    {
        "name": "Dairy & Eggs",
        "slug": "dairy-eggs",
        "sort_order": 20,
        "children": [
            {
                "name": "Milk & Cream",
                "slug": "milk-cream",
                "sort_order": 10,
                "children": [
                    {"name": "Fresh Cow & Buffalo Milk", "slug": "fresh-milk", "sort_order": 10},
                    {"name": "Toned & Double Toned Milk", "slug": "toned-milk", "sort_order": 20},
                    {"name": "UHT & Long Life Milk", "slug": "uht-milk", "sort_order": 30},
                    {"name": "Fresh Cream & Whipping Cream", "slug": "fresh-cream", "sort_order": 40},
                ],
            },
            {
                "name": "Curd, Paneer & Butter",
                "slug": "curd-paneer-butter",
                "sort_order": 20,
                "children": [
                    {"name": "Dahi & Greek Yogurt", "slug": "dahi-yogurt", "sort_order": 10},
                    {"name": "Fresh Paneer & Tofu", "slug": "fresh-paneer-tofu", "sort_order": 20},
                    {"name": "Table Butter & White Butter", "slug": "table-butter", "sort_order": 30},
                    {"name": "Desi Ghee & Clarified Butter", "slug": "desi-ghee", "sort_order": 40},
                ],
            },
            {
                "name": "Cheese & Gourmet Dairy",
                "slug": "cheese-gourmet-dairy",
                "sort_order": 30,
                "children": [
                    {"name": "Processed Cheese Slices & Cubes", "slug": "cheese-slices-cubes", "sort_order": 10},
                    {"name": "Mozzarella & Pizza Cheese", "slug": "mozzarella-pizza-cheese", "sort_order": 20},
                    {"name": "Artisanal & Cheddar Cheese", "slug": "cheddar-artisanal-cheese", "sort_order": 30},
                ],
            },
            {
                "name": "Fresh Eggs",
                "slug": "fresh-eggs",
                "sort_order": 40,
                "children": [
                    {"name": "Farm Fresh White Eggs", "slug": "farm-white-eggs", "sort_order": 10},
                    {"name": "Brown & Organic Free-Range Eggs", "slug": "brown-organic-eggs", "sort_order": 20},
                    {"name": "Omega-3 Enriched Eggs", "slug": "omega3-eggs", "sort_order": 30},
                ],
            },
        ],
    },
    {
        "name": "Staples & Grains",
        "slug": "staples-grains",
        "sort_order": 30,
        "children": [
            {
                "name": "Atta, Flours & Sooji",
                "slug": "atta-flours-sooji",
                "sort_order": 10,
                "children": [
                    {"name": "Whole Wheat Chakki Atta", "slug": "whole-wheat-atta", "sort_order": 10},
                    {"name": "Multigrain & Gluten-Free Atta", "slug": "multigrain-atta", "sort_order": 20},
                    {"name": "Maida, Besan & Sooji", "slug": "maida-besan-sooji", "sort_order": 30},
                    {"name": "Rice Flour & Corn Flour", "slug": "rice-corn-flour", "sort_order": 40},
                ],
            },
            {
                "name": "Rice & Rice Products",
                "slug": "rice-rice-products",
                "sort_order": 20,
                "children": [
                    {"name": "Basmati & Biryani Rice", "slug": "basmati-rice", "sort_order": 10},
                    {"name": "Sona Masoori & Daily Rice", "slug": "sona-masoori-rice", "sort_order": 20},
                    {"name": "Brown & Red Rice", "slug": "brown-red-rice", "sort_order": 30},
                    {"name": "Poha, Puffed Rice & Aval", "slug": "poha-puffed-rice", "sort_order": 40},
                ],
            },
            {
                "name": "Dals & Pulses",
                "slug": "dals-pulses",
                "sort_order": 30,
                "children": [
                    {"name": "Toor & Arhar Dal", "slug": "toor-dal", "sort_order": 10},
                    {"name": "Moong Dal & Sprouted Moong", "slug": "moong-dal", "sort_order": 20},
                    {"name": "Chana Dal, Kabuli & Kala Chana", "slug": "chana-dal", "sort_order": 30},
                    {"name": "Urad Dal & Masoor Dal", "slug": "urad-masoor-dal", "sort_order": 40},
                    {"name": "Rajma & Soya Chunks", "slug": "rajma-soya-chunks", "sort_order": 50},
                ],
            },
            {
                "name": "Edible Oils & Ghee",
                "slug": "edible-oils-ghee",
                "sort_order": 40,
                "children": [
                    {"name": "Sunflower & Safflower Oil", "slug": "sunflower-oil", "sort_order": 10},
                    {"name": "Mustard & Groundnut Oil", "slug": "mustard-groundnut-oil", "sort_order": 20},
                    {"name": "Olive Oil & Canola Oil", "slug": "olive-canola-oil", "sort_order": 30},
                    {"name": "Rice Bran & Blended Oil", "slug": "rice-bran-oil", "sort_order": 40},
                ],
            },
            {
                "name": "Spices, Masalas & Seasonings",
                "slug": "spices-masalas-seasonings",
                "sort_order": 50,
                "children": [
                    {"name": "Whole Spices & Herbs", "slug": "whole-spices", "sort_order": 10},
                    {"name": "Powdered Spices (Haldi, Mirch, Dhaniya)", "slug": "powdered-spices", "sort_order": 20},
                    {"name": "Blended Masalas (Garam, Pav Bhaji, Biryani)", "slug": "blended-masalas", "sort_order": 30},
                    {"name": "Iodized Salt, Rock Salt & Sugar", "slug": "salt-sugar-jaggery", "sort_order": 40},
                ],
            },
        ],
    },
    {
        "name": "Snacks & Packaged Foods",
        "slug": "snacks-packaged-foods",
        "sort_order": 40,
        "children": [
            {
                "name": "Biscuits & Cookies",
                "slug": "biscuits-cookies",
                "sort_order": 10,
                "children": [
                    {"name": "Digestive & Marie Biscuits", "slug": "digestive-marie-biscuits", "sort_order": 10},
                    {"name": "Cream Biscuits & Cookies", "slug": "cream-cookies", "sort_order": 20},
                    {"name": "Rusks & Crackers", "slug": "rusks-crackers", "sort_order": 30},
                ],
            },
            {
                "name": "Chips, Namkeen & Savouries",
                "slug": "chips-namkeen-savouries",
                "sort_order": 20,
                "children": [
                    {"name": "Potato Chips & Nachos", "slug": "potato-chips-nachos", "sort_order": 10},
                    {"name": "Traditional Namkeen & Bhujia", "slug": "traditional-namkeen", "sort_order": 20},
                    {"name": "Roasted Nuts & Healthy Snacks", "slug": "roasted-nuts-seeds", "sort_order": 30},
                ],
            },
            {
                "name": "Noodles, Pasta & Instant Foods",
                "slug": "noodles-pasta-instant-foods",
                "sort_order": 30,
                "children": [
                    {"name": "Instant Noodles & Cup Noodles", "slug": "instant-noodles", "sort_order": 10},
                    {"name": "Pasta, Vermicelli & Macaroni", "slug": "pasta-vermicelli", "sort_order": 20},
                    {"name": "Ready-to-Cook Mixes & Ready Meals", "slug": "ready-mixes-meals", "sort_order": 30},
                ],
            },
        ],
    },
    {
        "name": "Beverages",
        "slug": "beverages",
        "sort_order": 50,
        "children": [
            {
                "name": "Tea & Coffee",
                "slug": "tea-coffee",
                "sort_order": 10,
                "children": [
                    {"name": "Black & CTC Tea", "slug": "black-ctc-tea", "sort_order": 10},
                    {"name": "Green, Herbal & Specialty Tea", "slug": "green-herbal-tea", "sort_order": 20},
                    {"name": "Instant Coffee & Filter Coffee", "slug": "instant-filter-coffee", "sort_order": 30},
                ],
            },
            {
                "name": "Juices, Soft Drinks & Water",
                "slug": "juices-soft-drinks-water",
                "sort_order": 20,
                "children": [
                    {"name": "100% Fruit Juices & Nectars", "slug": "fruit-juices-nectars", "sort_order": 10},
                    {"name": "Carbonated Drinks & Sodas", "slug": "carbonated-drinks-sodas", "sort_order": 20},
                    {"name": "Packaged Drinking Water & Sparkling Water", "slug": "packaged-drinking-water", "sort_order": 30},
                    {"name": "Syrups, Squash & Energy Drinks", "slug": "syrups-energy-drinks", "sort_order": 40},
                ],
            },
        ],
    },
    {
        "name": "Household & Cleaning",
        "slug": "household-cleaning",
        "sort_order": 60,
        "children": [
            {
                "name": "Laundry & Dishwashing",
                "slug": "laundry-dishwashing",
                "sort_order": 10,
                "children": [
                    {"name": "Detergent Powders & Liquids", "slug": "detergent-powders-liquids", "sort_order": 10},
                    {"name": "Fabric Conditioners & Bleach", "slug": "fabric-conditioners", "sort_order": 20},
                    {"name": "Dishwash Bars, Liquids & Tablets", "slug": "dishwash-bars-liquids", "sort_order": 30},
                ],
            },
            {
                "name": "Home & Surface Cleaners",
                "slug": "home-surface-cleaners",
                "sort_order": 20,
                "children": [
                    {"name": "Floor Cleaners & Disinfectants", "slug": "floor-cleaners-disinfectants", "sort_order": 10},
                    {"name": "Toilet & Bathroom Cleaners", "slug": "toilet-bathroom-cleaners", "sort_order": 20},
                    {"name": "Glass Cleaners & Multi-Surface Sprays", "slug": "glass-cleaners-sprays", "sort_order": 30},
                ],
            },
        ],
    },
    {
        "name": "Personal Care & Hygiene",
        "slug": "personal-care-hygiene",
        "sort_order": 70,
        "children": [
            {
                "name": "Bath & Body",
                "slug": "bath-body",
                "sort_order": 10,
                "children": [
                    {"name": "Bath Soaps & Hand Washes", "slug": "bath-soaps-handwashes", "sort_order": 10},
                    {"name": "Body Washes & Shower Gels", "slug": "bodywashes-showergels", "sort_order": 20},
                ],
            },
            {
                "name": "Hair & Oral Care",
                "slug": "hair-oral-care",
                "sort_order": 20,
                "children": [
                    {"name": "Shampoos & Conditioners", "slug": "shampoos-conditioners", "sort_order": 10},
                    {"name": "Hair Oils & Serums", "slug": "hair-oils-serums", "sort_order": 20},
                    {"name": "Toothpaste, Toothbrushes & Mouthwash", "slug": "toothpaste-oral-care", "sort_order": 30},
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Idempotently seeds a 3-level grocery department hierarchy. Defaults to DRY-RUN."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Persist changes to the database. Without this flag, the command runs in DRY-RUN mode.",
        )

    def handle(self, *args, **options):
        commit = options.get("commit", False)

        if not commit:
            self.stdout.write(self.style.WARNING("=" * 70))
            self.stdout.write(self.style.WARNING("DRY-RUN MODE ACTIVE. No changes will be written to the database."))
            self.stdout.write(self.style.WARNING("Pass --commit to execute and write to the database."))
            self.stdout.write(self.style.WARNING("=" * 70))
        else:
            self.stdout.write(self.style.SUCCESS("=" * 70))
            self.stdout.write(self.style.SUCCESS("COMMIT MODE ACTIVE. Seeding grocery categories..."))
            self.stdout.write(self.style.SUCCESS("=" * 70))

        created_count = 0
        existing_count = 0
        existing_slugs = []
        conflicts = []

        def process_nodes(nodes, parent=None, level=1):
            nonlocal created_count, existing_count
            for node in nodes:
                name = node["name"]
                slug = node["slug"]
                sort_order = node.get("sort_order", 10)
                children = node.get("children", [])

                indent = "  " * (level - 1)
                existing = SellerHubCategory.objects.filter(slug=slug).first()

                if existing:
                    existing_count += 1
                    existing_slugs.append((slug, existing.id, existing.name))
                    self.stdout.write(f"{indent}[EXISTS] Level {level}: {name} (slug: {slug}, id: {existing.id})")
                    current_obj = existing

                    # Check if this existing category already has products attached
                    if children:
                        from workforce_api.models import SellerProduct
                        prod_count = SellerProduct.objects.filter(category=existing).count()
                        if prod_count > 0:
                            conflict_msg = f"Category '{existing.name}' (slug: {slug}, id: {existing.id}) has {prod_count} product(s) attached and cannot receive new subcategories."
                            conflicts.append(conflict_msg)
                            self.stdout.write(self.style.ERROR(f"{indent}  [CONFLICT / REFUSED] {conflict_msg} Skipping subcategories."))
                            continue
                else:
                    created_count += 1
                    if commit:
                        current_obj = SellerHubCategory.objects.create(
                            name=name,
                            slug=slug,
                            sort_order=sort_order,
                            parent=parent,
                            is_active=True,
                        )
                        self.stdout.write(self.style.SUCCESS(f"{indent}[CREATED] Level {level}: {name} (slug: {slug}, id: {current_obj.id})"))
                    else:
                        self.stdout.write(self.style.NOTICE(f"{indent}[WOULD CREATE] Level {level}: {name} (slug: {slug})"))
                        current_obj = SellerHubCategory(name=name, slug=slug, sort_order=sort_order, parent=parent, is_active=True)

                if children:
                    process_nodes(children, parent=current_obj if commit else None, level=level + 1)

        process_nodes(GROCERY_TAXONOMY)

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("SUMMARY OF GROCERY TAXONOMY SEED RUN")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Total existing categories in database: {len(existing_slugs)}")
        if existing_slugs:
            self.stdout.write("Existing slugs found:")
            for s_slug, s_id, s_name in existing_slugs[:10]:
                self.stdout.write(f"  - {s_slug} (id: {s_id}, name: '{s_name}')")
            if len(existing_slugs) > 10:
                self.stdout.write(f"  ... and {len(existing_slugs) - 10} more existing slugs.")

        if conflicts:
            self.stdout.write(self.style.ERROR(f"\nConflicts Detected ({len(conflicts)}):"))
            for c_err in conflicts:
                self.stdout.write(self.style.ERROR(f"  - {c_err}"))

        if commit:
            self.stdout.write(self.style.SUCCESS(f"\nSeeding completed. Created: {created_count}, Already existed: {existing_count}"))
        else:
            self.stdout.write(self.style.WARNING(f"\nDry-run finished. Would create: {created_count}, Already existed: {existing_count}"))
            self.stdout.write(self.style.NOTICE("Run with --commit to apply changes."))
        self.stdout.write("=" * 70)
