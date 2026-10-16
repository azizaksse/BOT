"""Client for the Bastaha reseller API.
Products are normalized to the same shape as Nexa products.
All product IDs are prefixed with 'bst_' so the multi-supplier can route
purchase calls to the right back-end.
"""
import asyncio
import logging
import time

import httpx

log = logging.getLogger(__name__)

BST_PREFIX = "bst_"


def _normalize(p: dict) -> dict:
    """Convert a Bastaha product dict to the Nexa-compatible shape."""
    stock = int(p.get("stock", 0))
    return {
        "id": f"{BST_PREFIX}{p['id']}",
        "_bst_id": p["id"],          # original int id for purchase calls
        "name": p.get("name", ""),
        "price": float(p.get("price", 0)),
        "stock": stock,
        "in_stock": stock > 0,
        "currency": p.get("currency", "USDT"),
        "source": "bastaha",
        "description": p.get("description") or "",
        "category": p.get("category", ""),
    }


class BastahaError(Exception):
    def __init__(self, status: int, message: str, retry_after: float | None = None):
        super().__init__(f"[{status}] {message}")
        self.status = status
        self.message = message
        self.retry_after = retry_after

    @property
    def retryable(self) -> bool:
        return self.status == 429 or self.status >= 500

    # expose same attrs as NexaError so purchase.py can handle both uniformly
    @property
    def code(self) -> str:
        return "BASTAHA_ERROR"


class BastahaClient:
    _cache: list[dict] | None = None
    _cache_at = 0.0

    def __init__(self, base_url: str, api_key: str, cache_ttl: int = 30):
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=httpx.Timeout(20, connect=8),
        )
        self._ttl = cache_ttl
        self._lock = asyncio.Lock()

    async def close(self):
        await self._http.aclose()

    async def _request(self, method: str, path: str, *, json=None):
        r = await self._http.request(method, path, json=json)
        try:
            data = r.json()
        except ValueError:
            data = {}
        if r.status_code >= 400 or (isinstance(data, dict) and data.get("success") is False):
            msg = (data.get("message") or data.get("error") or r.text)[:300]
            raise BastahaError(r.status_code if r.status_code >= 400 else 400, str(msg))
        return data

    async def balance(self) -> dict:
        return await self._request("GET", "/balance")

    async def products(self, force: bool = False) -> list[dict]:
        async with self._lock:
            fresh = time.monotonic() - self._cache_at < self._ttl
            if self._cache is not None and fresh and not force:
                return self._cache
            data = await self._request("GET", "/products")
            raw = data.get("products", []) if isinstance(data, dict) else data
            items = [_normalize(p) for p in raw]
            items.sort(key=lambda p: (not p["in_stock"], p["name"]))
            BastahaClient._cache, BastahaClient._cache_at = items, time.monotonic()
            return items

    async def get_product(self, product_id: str, force: bool = False) -> dict | None:
        for p in await self.products(force=force):
            if p["id"] == product_id:
                return p
        return None

    async def purchase(self, product_id: str, quantity: int, idem_key: str) -> dict:
        """Place an order. product_id must be a bst_ prefixed string."""
        bst_id = int(product_id.removeprefix(BST_PREFIX))
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                data = await self._request(
                    "POST", "/place-order",
                    json={"product_id": bst_id, "quantity": quantity},
                )
                # Normalize response to Nexa shape: {"codes": [...], "order_id": ...}
                codes = (
                    data.get("codes")
                    or data.get("items")
                    or data.get("keys")
                    or []
                )
                if isinstance(codes, str):
                    codes = [codes]
                return {
                    "codes": codes,
                    "order_id": str(data.get("order_id") or data.get("id") or ""),
                }
            except BastahaError as e:
                if not e.retryable:
                    raise
                last_exc, delay = e, e.retry_after or 2 ** attempt
            except httpx.TransportError as e:
                last_exc, delay = e, 2 ** attempt
            log.warning("Bastaha purchase attempt %s failed: %s", attempt + 1, last_exc)
            await asyncio.sleep(min(delay, 8))
        raise last_exc
