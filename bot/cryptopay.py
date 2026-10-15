"""Minimal async client for @CryptoBot's Crypto Pay API."""
import httpx


class CryptoPayError(Exception):
    pass


class CryptoPay:
    def __init__(self, token: str, testnet: bool = False):
        base = "https://testnet-pay.crypt.bot/api" if testnet else "https://pay.crypt.bot/api"
        self._http = httpx.AsyncClient(
            base_url=base, headers={"Crypto-Pay-API-Token": token}, timeout=20
        )

    async def close(self):
        await self._http.aclose()

    async def _call(self, method: str, **params):
        r = await self._http.post(f"/{method}", json=params)
        data = r.json()
        if not data.get("ok"):
            raise CryptoPayError(str(data.get("error")))
        return data["result"]

    async def create_invoice(self, amount: float, payload: str, description: str) -> dict:
        res = await self._call(
            "createInvoice",
            asset="USDT",
            amount=f"{amount:.2f}",
            payload=payload,
            description=description,
            expires_in=3600,
            allow_comments=False,
        )
        res["url"] = res.get("bot_invoice_url") or res.get("pay_url")
        return res

    async def get_invoices(self, invoice_ids: list[int]) -> list[dict]:
        res = await self._call("getInvoices", invoice_ids=",".join(map(str, invoice_ids)))
        return res.get("items", [])
