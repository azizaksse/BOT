"""Utility helpers for Binance Pay payments.

Only uses httpx which is already in requirements.txt.
No extra packages needed.
"""
import hashlib
import hmac
import json
import logging
import time

import httpx

log = logging.getLogger(__name__)

PAY_BASE_URL = "https://bpay.binanceapi.com"


def _sign_pay_payload(partner_key: str, payload: dict) -> str:
    """HMAC-SHA256 signature required by Binance Pay."""
    message = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return hmac.new(partner_key.encode(), message.encode(), hashlib.sha256).hexdigest()


async def create_binance_pay_order(
    partner_id: str,
    partner_key: str,
    order_id: str,
    amount: float,
    currency: str = "USDT",
    description: str = "Wallet top-up",
) -> dict:
    """Create a Binance Pay order. Returns the API JSON response.
    The field ``data.checkoutUrl`` can be sent to the user as a payment link.
    """
    nonce = str(int(time.time() * 1000))
    payload = {
        "merchantTradeNo": order_id,
        "currency": currency,
        "amount": f"{amount:.8f}",
        "goods": [{
            "goodsType": "1",
            "goodsName": description,
            "goodsCategory": "1",
            "quantity": "1",
            "price": f"{amount:.8f}",
        }],
        "tradeTime": int(time.time() * 1000),
        "nonce": nonce,
    }
    signature = _sign_pay_payload(partner_key, payload)
    headers = {
        "Content-Type": "application/json",
        "BinancePay-PartnerId": partner_id,
        "BinancePay-NonceStr": nonce,
        "BinancePay-Signature": signature,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{PAY_BASE_URL}/v1/pay/transactions/create",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()
