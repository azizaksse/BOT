"""Database layer: calls the Convex functions in convex/bot.ts over HTTPS.
Function names and return shapes match what the rest of the bot expects."""
import contextvars
import json
import time

import httpx

from config import CONVEX_SECRET, CONVEX_URL

_http: contextvars.ContextVar[httpx.AsyncClient] = contextvars.ContextVar("convex_http")


class ConvexError(Exception):
    pass


def now() -> int:
    return int(time.time())


def _norm(x):
    """Convex returns every number as a float; turn whole numbers back into ints."""
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, dict):
        return {k: _norm(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_norm(v) for v in x]
    return x


async def connect() -> None:
    _http.set(httpx.AsyncClient(base_url=CONVEX_URL.rstrip("/"), timeout=20))


async def close() -> None:
    client = _http.get(None)
    if client is not None:
        await client.aclose()


async def _call(_kind: str, _name: str, **args):
    r = await _http.get().post(
        f"/api/{_kind}",
        json={"path": f"bot:{_name}", "args": {"secret": CONVEX_SECRET, **args}, "format": "json"},
    )
    try:
        data = r.json()
    except ValueError:
        raise ConvexError(f"HTTP {r.status_code}: {r.text[:300]}")
    if data.get("status") != "success":
        raise ConvexError(data.get("errorMessage") or str(data)[:300])
    return _norm(data.get("value"))


async def _q(_name: str, **args):
    return await _call("query", _name, **args)


async def _m(_name: str, **args):
    return await _call("mutation", _name, **args)


async def init_schema() -> None:
    pass  # the schema is deployed with `npx convex deploy`


async def cleanup() -> None:
    await _m("cleanup", before=now() - 3 * 86400)


# ---------------- dedupe ----------------
async def claim(key: str) -> bool:
    return await _m("claim", k=key)


# ---------------- FSM ----------------
async def fsm_get(k: str):
    return await _q("fsmGet", k=k)


async def fsm_set_state(k: str, state: str | None) -> None:
    await _m("fsmSetState", k=k, state=state)


async def fsm_set_data(k: str, data: dict) -> None:
    await _m("fsmSetData", k=k, data=json.dumps(data, ensure_ascii=False))


# ---------------- users ----------------
async def get_or_create_user(uid: int, username: str | None, lang_code: str | None):
    lang = lang_code[:2] if lang_code and lang_code[:2] in ("fr", "ar") else "en"
    return await _m("getOrCreateUser", id=uid, username=username, lang=lang)


async def get_user(uid: int):
    return await _q("getUser", id=uid)


async def get_lang(uid: int) -> str:
    row = await get_user(uid)
    return row["lang"] if row else "en"


async def set_lang(uid: int, lang: str) -> None:
    await _m("setLang", id=uid, lang=lang)


async def set_banned(uid: int, banned: bool) -> bool:
    return await _m("setBanned", id=uid, banned=banned)


async def all_user_ids() -> list[int]:
    return await _q("allUserIds")


async def credit(uid: int, cents: int, kind: str, ref: str | None = None) -> bool:
    return await _m("credit", id=uid, cents=cents, kind=kind, ref=ref)


async def debit(uid: int, cents: int, kind: str, ref: str | None = None) -> bool:
    """Atomic in Convex: only succeeds if the balance is high enough."""
    return await _m("debit", id=uid, cents=cents, kind=kind, ref=ref)


# ---------------- orders ----------------
async def create_order(order_id, uid, product_id, product_name, qty, total, cost, idem_key):
    await _m("createOrder", id=order_id, user_id=uid, product_id=product_id, product_name=product_name,
             quantity=qty, total=total, cost=cost, idem_key=idem_key)


async def get_order(order_id: str):
    return await _q("getOrder", id=order_id)


async def user_orders(uid: int, limit: int = 10):
    return await _q("userOrders", user_id=uid, limit=limit)


async def set_order_status(order_id: str, status: str) -> None:
    await _m("setOrderStatus", id=order_id, status=status)


async def complete_order(order_id: str, codes: list, nexa_order_id: str | None) -> None:
    await _m("completeOrder", id=order_id, codes=json.dumps(codes, ensure_ascii=False),
             nexa_order_id=nexa_order_id)


async def refund_order(order_id: str) -> bool:
    return await _m("refundOrder", id=order_id)


# ---------------- invoices ----------------
async def add_invoice(invoice_id: int, uid: int, amount: int, pay_url: str) -> None:
    await _m("addInvoice", invoice_id=invoice_id, user_id=uid, amount=amount, pay_url=pay_url)


async def get_invoice(invoice_id: int):
    return await _q("getInvoice", invoice_id=invoice_id)


async def set_invoice_status(invoice_id: int, status: str) -> None:
    await _m("setInvoiceStatus", invoice_id=invoice_id, status=status)


async def mark_invoice_paid(invoice_id: int):
    """Returns the invoice only the FIRST time it is marked paid (no double credit)."""
    return await _m("markInvoicePaid", invoice_id=invoice_id)


# ---------------- settings / pricing ----------------
async def get_setting(key: str, default: str) -> str:
    value = await _q("getSetting", key=key)
    return value if value is not None else default


async def set_setting(key: str, value: str) -> None:
    await _m("setSetting", key=key, value=value)


async def get_overrides() -> dict[str, int]:
    return {r["product_id"]: r["price"] for r in await _q("getOverrides")}


async def set_override(product_id: str, cents: int) -> None:
    await _m("setOverride", product_id=product_id, price=cents)


async def del_override(product_id: str) -> bool:
    return await _m("delOverride", product_id=product_id)


# ---------------- warranties ----------------
async def create_warranty(uid: int, order_id: str, issue: str) -> int:
    return await _m("createWarranty", user_id=uid, order_id=order_id, issue=issue)


async def get_warranty(wid: int):
    return await _q("getWarranty", id=wid)


async def user_warranties(uid: int, limit: int = 10):
    return await _q("userWarranties", user_id=uid, limit=limit)


async def open_warranty_for_order(order_id: str):
    return await _q("openWarrantyForOrder", order_id=order_id)


async def update_warranty(wid: int, status: str, reply: str | None = None) -> None:
    args = {"id": wid, "status": status}
    if reply is not None:
        args["reply"] = reply
    await _m("updateWarranty", **args)


# ---------------- stats ----------------
async def stats() -> dict:
    return await _q("stats")
