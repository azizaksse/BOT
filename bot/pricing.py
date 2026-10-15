"""Selling price = per-product override, or Nexa cost + global markup (% and fixed)."""
import math
from dataclasses import dataclass

import db
from config import DEFAULT_MARKUP_FIXED, DEFAULT_MARKUP_PERCENT
from money import to_cents


@dataclass
class Pricing:
    percent: float
    fixed: int  # cents
    overrides: dict[str, int]


async def get_pricing() -> Pricing:
    pct = float(await db.get_setting("markup_percent", str(DEFAULT_MARKUP_PERCENT)))
    fixed = to_cents(await db.get_setting("markup_fixed", str(DEFAULT_MARKUP_FIXED)))
    return Pricing(pct, fixed, await db.get_overrides())


def price_for(product: dict, pricing: Pricing) -> int:
    cost = to_cents(product.get("price", 0))
    override = pricing.overrides.get(product.get("id"))
    # an override is ignored if the supplier cost rose above it (never sell at a loss)
    if override is not None and override >= cost:
        return override
    return max(cost, math.ceil(cost * (1 + pricing.percent / 100)) + pricing.fixed)
