# api/binance_helpers.py
"""Utility helpers for Binance Spot, Binance Pay, and BEP‑20 (BSC) payments.

All credentials are loaded from ``config.py`` which reads the .env file.
The functions are deliberately lightweight so they can be called from the
existing Starlette routes (async where appropriate).
"""

import time
import hmac
import hashlib
import json
from urllib.parse import urlencode

from python_binance.client import Client  # pip install python-binance
from web3 import Web3

from config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    BINANCE_PAY_PARTNER_ID,
    BINANCE_PAY_PARTNER_KEY,
    BSC_RPC_URL,
)

# ----------------------------------------------------------------------
# 1️⃣ Spot client – used for balance queries, order status, etc.
# ----------------------------------------------------------------------
spot_client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)


def get_spot_balance(asset: str = "USDT") -> float:
    """Return the free balance for a given Spot asset (default USDT)."""
    info = spot_client.get_account()
    for bal in info["balances"]:
        if bal["asset"] == asset:
            return float(bal["free"])
    return 0.0

# ----------------------------------------------------------------------
# 2️⃣ Binance Pay – create a payment order
# ----------------------------------------------------------------------
PAY_BASE_URL = "https://bpay.binanceapi.com"


def _sign_pay_payload(payload: dict) -> str:
    """Generate the HMAC‑SHA256 signature required by Binance Pay.
    The signature is the hex digest of the JSON payload signed with the
    partner secret key.
    """
    message = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    signature = hmac.new(
        BINANCE_PAY_PARTNER_KEY.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return signature


async def create_binance_pay_order(
    order_id: str,
    amount: float,
    currency: str = "USDT",
    description: str = "Nexa order",
) -> dict:
    """Create a Binance Pay transaction.
    Returns the JSON response; the field ``checkoutUrl`` can be sent to the user.
    """
    payload = {
        "merchantTradeNo": order_id,
        "currency": currency,
        "amount": f"{amount:.8f}",
        "goods": [
            {
                "goodsType": "1",
                "goodsName": description,
                "goodsCategory": "1",
                "quantity": "1",
                "price": f"{amount:.8f}",
            }
        ],
        "tradeTime": int(time.time() * 1000),
        "nonce": str(int(time.time() * 1000)),
    }

    signature = _sign_pay_payload(payload)

    headers = {
        "Content-Type": "application/json",
        "BinancePay-PartnerId": BINANCE_PAY_PARTNER_ID,
        "BinancePay-NonceStr": payload["nonce"],
        "BinancePay-Signature": signature,
    }

    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAY_BASE_URL}/v1/pay/transactions/create",
            json=payload,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

# ----------------------------------------------------------------------
# 3️⃣ BEP‑20 on‑chain payment monitoring (Web3)
# ----------------------------------------------------------------------
w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))


def get_bep20_balance(address: str, token_contract: str) -> float:
    """Return the token balance (in whole units) of a BEP‑20 token.
    ``address`` – the wallet that should receive the payment.
    ``token_contract`` – the contract address of the BEP‑20 token (e.g. USDT‑BEP20).
    """
    erc20_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function",
        },
    ]
    contract = w3.eth.contract(address=Web3.toChecksumAddress(token_contract), abi=erc20_abi)
    raw_balance = contract.functions.balanceOf(Web3.toChecksumAddress(address)).call()
    decimals = contract.functions.decimals().call()
    return raw_balance / (10 ** decimals)


def watch_address_for_payment(
    watch_address: str,
    token_contract: str,
    expected_amount: float,
    poll_interval: int = 12,
) -> bool:
    """Simple blocking poller – returns ``True`` once the address holds at least
    ``expected_amount`` tokens. Use this inside an async task or a scheduler.
    """
    while True:
        cur = get_bep20_balance(watch_address, token_contract)
        if cur >= expected_amount:
            return True
        time.sleep(poll_interval)
