"""BEP-20 / BSC payment helper.

Flow:
1. User asks to top-up via BEP-20.
2. Bot shows the deposit address and the exact amount to send.
3. A unique reference memo (uid + amount + timestamp) is stored in the DB.
4. A background poller calls `poll_bsc_payment` which reads the token
   balance via BSC RPC and credits the user once it arrives.

No private key is needed — we only *read* the chain.
"""
import asyncio
import logging
import time

import httpx

from config import BSC_DEPOSIT_ADDRESS, BSC_RPC_URL, USDT_BEP20_CONTRACT

log = logging.getLogger(__name__)

# ERC-20 / BEP-20 balanceOf selector: keccak256("balanceOf(address)")[:4]
_BALANCE_OF_SELECTOR = "0x70a08231"
_DECIMALS = 18  # USDT-BEP20 uses 18 decimals


def _to_padded(address: str) -> str:
    """Pad an address to 32 bytes (64 hex chars) for ABI encoding."""
    return address.lower().replace("0x", "").zfill(64)


async def get_bep20_balance(address: str = BSC_DEPOSIT_ADDRESS) -> float:
    """Return the USDT-BEP20 balance of *address* (float, in USDT)."""
    data = _BALANCE_OF_SELECTOR + _to_padded(address)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [{"to": USDT_BEP20_CONTRACT, "data": data}, "latest"],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(BSC_RPC_URL, json=payload)
            result = resp.json().get("result", "0x0")
            raw = int(result, 16)
            return raw / (10 ** _DECIMALS)
    except Exception as e:
        log.error("BSC RPC error: %s", e)
        return 0.0


async def wait_for_payment(
    expected_usdt: float,
    baseline: float,
    timeout: int = 1800,   # 30 minutes
    interval: int = 15,    # poll every 15 s
) -> bool:
    """
    Poll BSC until the deposit address receives *at least* expected_usdt
    more USDT than the baseline reading taken before the user was shown the
    deposit address.

    Returns True if paid in time, False on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        balance = await get_bep20_balance()
        received = balance - baseline
        log.debug("BSC poll: balance=%.4f baseline=%.4f received=%.4f", balance, baseline, received)
        if received >= expected_usdt * 0.99:   # allow 1% tolerance for rounding
            return True
        await asyncio.sleep(interval)
    return False
