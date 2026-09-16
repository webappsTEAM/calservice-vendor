"""
vendor/backend/inventory/utils/unit_conversion.py

Direct copy of Customer/backend/inventory/utils/unit_conversion.py -- pure
functions, no model dependencies, so both projects can carry their own copy
without needing to share Python code across the two separate Django
projects. Keep these two files identical if either changes.
"""
from decimal import Decimal
import math


def parse_pack_size_grams(duration_or_unit_str: str, default_grams: int = 500) -> int:
    """
    Parse strings representing pack sizes/units like '200 g', '250 g', '1 kg', '1.5 kg', '50 g', '1 pc'
    into exact integer grams. Returns default_grams if not parseable or piecewise.
    """
    import re
    if not duration_or_unit_str:
        return default_grams

    s = str(duration_or_unit_str).strip()
    m = re.search(r'(\d+(?:\.\d+)?)\s*(kg|kilogram|kilograms|g|gram|grams)\b', s, re.IGNORECASE)
    if m:
        try:
            val = float(m.group(1))
            unit = m.group(2).lower()
            return to_grams(val, unit, allow_zero=False)
        except Exception:
            pass

    return default_grams


def to_grams(quantity, unit: str = "g", allow_zero: bool = False) -> int:
    """
    Convert and round to nearest whole integer gram immediately.
    Reject negative or non-numeric input. Reject zero unless allow_zero=True.
    Valid units: 'kg', 'g' (case-insensitive).
    """
    if quantity is None:
        raise ValueError("Quantity cannot be None")

    try:
        if isinstance(quantity, str):
            quantity_clean = quantity.strip().lower().replace("kg", "").replace("g", "")
            val = float(quantity_clean)
        else:
            val = float(quantity)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid numeric quantity: {quantity}")

    if math.isnan(val) or math.isinf(val):
        raise ValueError(f"Invalid numeric quantity: {quantity}")

    if allow_zero:
        if val < 0:
            raise ValueError(f"Quantity must be greater than or equal to zero, got: {quantity}")
    else:
        if val <= 0:
            raise ValueError(f"Quantity must be a positive number greater than zero, got: {quantity}")

    unit_clean = str(unit or "g").strip().lower()
    if unit_clean in ["kg", "kilogram", "kilograms"]:
        grams = round(val * 1000.0)
    elif unit_clean in ["g", "gram", "grams"]:
        grams = round(val)
    else:
        raise ValueError(f"Unsupported unit: '{unit}'. Allowed units are 'kg' or 'g'.")

    if not allow_zero and grams <= 0:
        raise ValueError("Converted quantity in grams must be at least 1 gram.")

    return int(max(0, grams))


def format_grams_for_display(grams: int) -> str:
    """
    Format integer grams into a clean human-readable string for admin displays.
    e.g., 18000 -> "18 kg", 18500 -> "18.5 kg", 500 -> "500 g".
    """
    if grams is None:
        return "0 g"

    try:
        g = int(grams)
    except (ValueError, TypeError):
        return "0 g"

    if g >= 1000:
        kg = g / 1000.0
        if kg.is_integer():
            return f"{int(kg)} kg"
        return f"{kg:.2f}".rstrip("0").rstrip(".") + " kg"
    return f"{g} g"
