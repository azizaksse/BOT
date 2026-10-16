"""Product filtering — blocks products whose names contain any of the keywords below.
   Add/remove keywords to control what your store sells.
"""

# Products containing ANY of these words (case-insensitive) will be HIDDEN from customers.
BLOCKED_KEYWORDS = [
    # Streaming / video (haram)
    "netflix",
    "prime video",
    "amazon prime",
    "disney",
    "hulu",
    "hbo",
    "paramount",
    "peacock",
    "crunchyroll",
    "apple tv",
    "apple tv+",
    "youtube premium",
    "youtube music",
    "tidal",
    "deezer",
    "itunes",
    # Music
    "spotify",
    "apple music",
    "amazon music",
    "youtube music",
    # Social media entertainment
    "snapchat",
    "snap",
    "tiktok",
    # Other entertainment/watching
    "onlyfans",
    "twitch",
    "funimation",
    "vrv",
    "mubi",
    "plex",
    "starz",
    "showtime",
    "epix",
    "shudder",
    "discovery+",
    "britbox",
    "acorn tv",
    "philo",
    "sling",
    "fubo",
    "directv",
    "scribd",
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
