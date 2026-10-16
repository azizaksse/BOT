"""Product filtering — blocks products whose names contain any of the keywords below.
   Add/remove keywords to control what your store sells.
"""

# Products containing ANY of these words (case-insensitive) will be HIDDEN from customers.
BLOCKED_KEYWORDS = [
    "netflix",
    "spotify",
    "snapchat",
    "snap",
    "apple music",
    "apple tv",
    "scribd",
    "amazon",
    "disney",
    "hulu",
    "tidal",
    "deezer",
    "youtube music",
    "youtube premium",
    "crunchyroll",
    "hbo",
    "paramount",
    "peacock",
    "itunes",
]

# Optionally block specific product IDs (use the Nexa product ID number as string)
BLOCKED_IDS: set[str] = set()


def is_visible(product: dict) -> bool:
    """Returns True if the product should be shown in the store."""
    pid = str(product.get("id", ""))
    if pid in BLOCKED_IDS:
        return False
    name = product.get("name", "").lower()
    return not any(kw.lower() in name for kw in BLOCKED_KEYWORDS)


def filter_products(products: list[dict]) -> list[dict]:
    """Filter a list of Nexa products, removing blocked ones."""
    return [p for p in products if is_visible(p)]
