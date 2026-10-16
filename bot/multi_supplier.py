"""Multi-supplier wrapper — merges Nexa + Bastaha into a single unified interface.

Drop-in replacement for NexaClient everywhere in the codebase.
Purchase calls are automatically routed to the right back-end by product ID prefix:
  - IDs starting with 'bst_' → Bastaha
  - Everything else           → Nexa
"""
import asyncio
import logging
import time

from bastaha_api import BastahaClient
from nexa_api import NexaClient
from product_filter import filter_products

log = logging.getLogger(__name__)

_merged_cache: list[dict] | None = None
_merged_cache_at = 0.0
_CACHE_TTL = 30


class MultiSupplier:
    """Same public interface as NexaClient so all handlers work unchanged."""

    def __init__(self, nexa: NexaClient, bastaha: BastahaClient | None):
        self._nexa = nexa
        self._bastaha = bastaha
        self._lock = asyncio.Lock()

    async def close(self):
        await self._nexa.close()
        if self._bastaha:
            await self._bastaha.close()

    # ── products ──────────────────────────────────────────────────────────────

    async def products(self, force: bool = False) -> list[dict]:
        global _merged_cache, _merged_cache_at
        async with self._lock:
            fresh = time.monotonic() - _merged_cache_at < _CACHE_TTL
            if _merged_cache is not None and fresh and not force:
                return _merged_cache

            tasks = [self._nexa.products(force=force)]
            if self._bastaha:
                tasks.append(self._bastaha.products(force=force))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            merged = []
            for r in results:
                if isinstance(r, Exception):
                    log.warning("Supplier fetch error: %s", r)
                else:
                    merged.extend(r)

            # Apply keyword/ID filter (removes music, netflix, spotify, etc.)
            merged = filter_products(merged)
            merged.sort(key=lambda p: (not (p.get("in_stock") and p.get("stock", 0) > 0), p.get("name", "")))

            _merged_cache = merged
            _merged_cache_at = time.monotonic()
            return merged

    async def get_product(self, product_id: str, force: bool = False) -> dict | None:
        for p in await self.products(force=force):
            if p["id"] == product_id:
                return p
        return None

    # ── purchase ──────────────────────────────────────────────────────────────

    async def purchase(self, product_id: str, quantity: int, idem_key: str) -> dict:
        if product_id.startswith("bst_") and self._bastaha:
            return await self._bastaha.purchase(product_id, quantity, idem_key)
        return await self._nexa.purchase(product_id, quantity, idem_key)

    # ── extra helpers (admin commands) ────────────────────────────────────────

    async def balance(self) -> dict:
        """Returns Nexa balance (for /nexabal admin command)."""
        return await self._nexa.balance()

    async def bastaha_balance(self) -> dict | None:
        if not self._bastaha:
            return None
        return await self._bastaha.balance()
