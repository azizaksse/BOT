"""Order flow: charge user -> buy from Nexa (idempotent) -> deliver, or refund."""
import json
import logging
import secrets
import string
import uuid

import httpx
from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup

import db
from i18n import t
from money import fmt, to_cents
from nexa_api import NexaClient, NexaError
from pricing import get_pricing, price_for
from utils import esc, notify_admins

log = logging.getLogger(__name__)

# Errors after which Nexa definitely did NOT deliver -> safe to refund automatically.
DEFINITIVE_FAIL = {400, 401, 402, 403, 404, 409, 422}


def new_order_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "NX-" + "".join(secrets.choice(alphabet) for _ in range(8))


async def start_purchase(bot: Bot, nexa: NexaClient, uid: int, lang: str, product_id: str, qty: int):
    """Returns None on success (user notified), or (text, keyboard) describing why it failed."""
    try:
        product = await nexa.get_product(product_id, force=True)
    except Exception as e:
        log.error("Nexa products failed: %s", e)
        return t(lang, "service_unavailable"), None
    if not product:
        return t(lang, "product_not_found"), None
    stock = int(product.get("stock", 0))
    if not product.get("in_stock") or stock <= 0:
        return t(lang, "out_of_stock"), None
    if stock < qty:
        return t(lang, "not_enough_stock"), None

    unit = price_for(product, await get_pricing())
    total = unit * qty
    order_id = new_order_id()

    if not await db.debit(uid, total, "purchase", order_id):
        user = await db.get_user(uid)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text=t(lang, "btn_topup"), callback_data="wallet")],
            [Btn(text=t(lang, "btn_back"), callback_data=f"prod:{product_id}")],
        ])
        return t(lang, "insufficient", total=fmt(total), balance=fmt(user["balance"])), kb

    await db.create_order(
        order_id, uid, product_id, product["name"], qty, total,
        cost=to_cents(product.get("price", 0)) * qty, idem_key=str(uuid.uuid4()),
    )
    await execute_order(bot, nexa, order_id)
    return None


async def execute_order(bot: Bot, nexa: NexaClient, order_id: str) -> str:
    """Calls Nexa for an already-paid order. Safe to call again (admin /retry):
    the stored Idempotency-Key guarantees Nexa won't charge twice."""
    order = await db.get_order(order_id)
    if not order or order["status"] not in ("processing", "pending"):
        return "skipped"
    uid = order["user_id"]
    lang = await db.get_lang(uid)

    try:
        res = await nexa.purchase(order["product_id"], order["quantity"], order["idem_key"])
    except NexaError as e:
        if e.status in DEFINITIVE_FAIL:
            await db.refund_order(order_id)
            await _send(bot, uid, t(lang, "order_failed_refunded", id=order_id, total=fmt(order["total"])))
            if e.status in (401, 402, 403):
                await notify_admins(bot, f"🚨 <b>Nexa error {e.status} ({esc(e.code)})</b> on order "
                                         f"<code>{order_id}</code>: {esc(e.message)}\n"
                                         f"Customer was refunded. Check your Nexa wallet / API key!")
            return "refunded"
        return await _mark_pending(bot, order, lang, f"Nexa {e.status} {e.code}: {e.message}")
    except httpx.HTTPError as e:
        return await _mark_pending(bot, order, lang, f"Network error: {e!r}")

    codes = res.get("codes") or []
    await db.complete_order(order_id, codes, res.get("order_id"))
    await deliver(bot, order_id)
    return "completed"


async def _mark_pending(bot: Bot, order, lang: str, reason: str) -> str:
    # Unknown outcome: Nexa may or may not have charged us -> do NOT auto-refund.
    await db.set_order_status(order["id"], "pending")
    await _send(bot, order["user_id"], t(lang, "order_delayed", id=order["id"]))
    await notify_admins(
        bot,
        f"⚠️ <b>Order delayed</b> <code>{order['id']}</code>\n"
        f"User: <code>{order['user_id']}</code> · {esc(order['product_name'])} × {order['quantity']}\n"
        f"Reason: {esc(reason)}\n\n"
        f"Retry (safe, same idempotency key): <code>/retry {order['id']}</code>\n"
        f"Refund customer: <code>/refund {order['id']}</code>",
    )
    return "pending"


async def deliver(bot: Bot, order_id: str) -> None:
    order = await db.get_order(order_id)
    uid = order["user_id"]
    lang = await db.get_lang(uid)
    user = await db.get_user(uid)
    codes = json.loads(order["codes"] or "[]")
    header = t(lang, "order_done", id=order_id, name=esc(order["product_name"]), qty=order["quantity"],
               total=fmt(order["total"]), balance=fmt(user["balance"]))
    body = "\n\n".join(f"<code>{esc(c)}</code>" for c in codes)
    if len(header) + len(body) < 3900:
        await _send(bot, uid, f"{header}\n\n{body}")
    else:
        await _send(bot, uid, f"{header}\n\n{t(lang, 'codes_in_file')}")
        file = BufferedInputFile("\n".join(codes).encode(), filename=f"{order_id}.txt")
        await bot.send_document(uid, file)


async def _send(bot: Bot, uid: int, text: str):
    try:
        await bot.send_message(uid, text)
    except Exception as e:
        log.warning("Could not message user %s: %s", uid, e)
