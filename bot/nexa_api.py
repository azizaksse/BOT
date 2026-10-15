"""Client for the Nexa Store supplier API."""
import asyncio
import logging
import time

import httpx

log = logging.getLogger(__name__)


class NexaError(Exception):
    def __init__(self, status: int, code: str, message: str, retry_after: float | None = None):
        super().__init__(f"[{status}] {code}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after

    @property
    def retryable(self) -> bool:
        return self.status == 429 or self.status >= 500


class NexaClient:
    _cache: list[dict] | None = None   # shared between requests while the instance is warm
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

    async def _request(self, method: str, path: str, *, json=None, headers=None):
        r = await self._http.request(method, path, json=json, headers=headers)
        try:
            data = r.json()
        except ValueError:
            data = {}
        failed = r.status_code >= 400 or (isinstance(data, dict) and data.get("success") is False)
        if failed:
            code, message = "ERROR", r.text[:300]
            if isinstance(data, dict):
                err = data.get("error")
                if isinstance(err, dict):
                    code = err.get("code", code)
                    message = err.get("message", message)
                else:
                    code = data.get("code") or (err if isinstance(err, str) else code)
                    message = data.get("message") or message
            retry_after = None
            reset = r.headers.get("X-RateLimit-Reset")
            if r.status_code == 429 and reset and reset.isdigit():
                retry_after = max(1.0, int(reset) - time.time())
            status = r.status_code if r.status_code >= 400 else 400
            raise NexaError(status, str(code), str(message), retry_after)
        return data

    # ---------- endpoints ----------
    async def balance(self) -> dict:
        return await self._request("GET", "/balance")

    async def products(self, force: bool = False) -> list[dict]:
        async with self._lock:
            fresh = time.monotonic() - self._cache_at < self._ttl
            if self._cache is not None and fresh and not force:
                return self._cache
            data = await self._request("GET", "/products")
            items = data.get("products", []) if isinstance(data, dict) else data
            items.sort(key=lambda p: (not (p.get("in_stock") and p.get("stock", 0) > 0), p.get("name", "")))
            NexaClient._cache, NexaClient._cache_at = items, time.monotonic()
            return items

    async def get_product(self, product_id: str, force: bool = False) -> dict | None:
        for p in await self.products(force=force):
            if p.get("id") == product_id:
                return p
        return None

    async def purchase(self, product_id: str, quantity: int, idem_key: str) -> dict:
        """Buys codes. Retries network/5xx/429 errors with the SAME Idempotency-Key,
        so a retry can never charge twice."""
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                return await self._request(
                    "POST", "/purchase",
                    json={"product_id": product_id, "quantity": quantity},
                    headers={"Idempotency-Key": idem_key},
                )
            except NexaError as e:
                if not e.retryable:
                    raise
                last_exc, delay = e, e.retry_after or 2 ** attempt
            except httpx.TransportError as e:
                last_exc, delay = e, 2 ** attempt
            log.warning("Nexa purchase attempt %s failed: %s", attempt + 1, last_exc)
            await asyncio.sleep(min(delay, 8))
        raise last_exc
