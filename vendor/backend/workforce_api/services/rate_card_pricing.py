"""
Rate-card pricing that a single rate column cannot express.

Most items are a rate per square foot. Several are not, and pretending they are
is how a quote ends up billing a 10,000-litre tank at a per-litre rate meant for
a 2,000-litre one:

  TIERED         epoxy flooring: 1 mm Rs.60, 2 mm Rs.90, 3 mm Rs.110 per sq.ft
  CAPACITY_BAND  water tank: <=1000 L flat Rs.1700, 1000-5000 L Rs.1.50/L,
                 >=10000 L flat Rs.17000
  SIZE_BAND      bathroom tiling: up to 80 sq.ft Rs.10000 flat, above Rs.20000
  FLAT           one price regardless of quantity
  QUOTE_ONLY     no standard rate; the technician prices it on site
  PER_UNIT       the ordinary case

pricing_config shapes:
  TIERED         {"tiers": {"1mm": 60, "2mm": 90, "3mm": 110}}
  CAPACITY_BAND  {"bands": [{"max": 1000, "flat": 1700},
                            {"max": 5000, "rate": 1.5},
                            {"max": null, "flat": 17000}]}
  SIZE_BAND      {"bands": [{"max": 80, "flat": 10000},
                            {"max": null, "flat": 20000}]}

Bands are evaluated in order and the FIRST whose `max` covers the quantity wins;
`max: null` is the catch-all and must come last.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def _d(value):
    return Decimal(str(value if value is not None else 0))


def price_line(rate_card, quantity, tier=None):
    """
    Price one quote line against a rate card.

    Returns (line_total, unit_price, note). unit_price is what the technician
    and the customer see per unit; for flat-priced bands it is the flat amount
    with quantity treated as 1, so the arithmetic on the quote still adds up.
    """
    quantity = _d(quantity)
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")

    minimum = _d(getattr(rate_card, "minimum_quantity", 0))
    if minimum > 0 and quantity < minimum:
        raise ValidationError(
            f"{rate_card.item_name} has a minimum of {minimum:g} {rate_card.unit}. "
            f"{quantity:g} {rate_card.unit} is below the viable threshold for "
            "mobilising labour and materials."
        )

    model = getattr(rate_card, "pricing_model", "PER_UNIT")
    config = getattr(rate_card, "pricing_config", None) or {}

    if model == "QUOTE_ONLY":
        raise ValidationError(
            f"{rate_card.item_name} has no standard rate and must be priced on site. "
            "Enter the unit price manually on the quote line."
        )

    if model == "FLAT":
        total = _d(rate_card.default_rate).quantize(CENT)
        return total, total, f"Flat price for {rate_card.item_name}."

    if model == "PER_UNIT":
        unit = _d(rate_card.default_rate).quantize(CENT)
        return (unit * quantity).quantize(CENT), unit, ""

    if model == "TIERED":
        tiers = config.get("tiers") or {}
        if not tier:
            raise ValidationError(
                f"{rate_card.item_name} needs a specification: "
                f"{', '.join(sorted(tiers)) or 'none configured'}."
            )
        if tier not in tiers:
            raise ValidationError(
                f"'{tier}' is not a valid specification for {rate_card.item_name}. "
                f"Choose from: {', '.join(sorted(tiers))}."
            )
        unit = _d(tiers[tier]).quantize(CENT)
        return (unit * quantity).quantize(CENT), unit, f"{rate_card.item_name} ({tier})."

    if model in ("CAPACITY_BAND", "SIZE_BAND"):
        band = _select_band(config.get("bands") or [], quantity, rate_card.item_name)
        if "flat" in band and band["flat"] is not None:
            total = _d(band["flat"]).quantize(CENT)
            return total, total, band.get("label") or f"{rate_card.item_name} (flat band)."
        unit = _d(band.get("rate")).quantize(CENT)
        return (unit * quantity).quantize(CENT), unit, band.get("label") or ""

    raise ValidationError(f"Unknown pricing model '{model}' on {rate_card.item_name}.")


def _select_band(bands, quantity, item_name):
    if not bands:
        raise ValidationError(f"{item_name} has no pricing bands configured.")
    for band in bands:
        ceiling = band.get("max")
        if ceiling is None or quantity <= _d(ceiling):
            return band
    # Reached only if the last band has a finite max and quantity exceeds it.
    raise ValidationError(
        f"{quantity:g} is above every configured band for {item_name}. "
        "Add a catch-all band (\"max\": null) or price this line manually."
    )
