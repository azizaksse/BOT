"""CryptoBot top-ups: webhook + manual check, credit balance exactly once."""
import hashlib
import hmac
import logging

from aiogram import Bot

import db
from cryptopay import CryptoPay
from i18n import t
from money import fmt
from utils import notify_admins

log = logging.getLogger(__name__)


async def credit_paid_invoice(bot: Bot, invoice_id: int) -> bool:
    row = await db.mark_invoice_paid(invoice_id)
    if not row:
        return False
    uid = row["user_id"]
    lang = await db.get_lang(uid)
    user = await db.get_user(uid)
    try:
        await bot.send_message(uid, t(lang, "payment_received", amount=fmt(row["amount"]),
                                      balance=fmt(user["balance"])))
    except Exception as e:
        log.warning("notify user %s failed: %s", uid, e)
    await notify_admins(bot, f"💵 Top-up <b>+{fmt(row['amount'])} USDT</b> from user <code>{uid}</code>")
    return True


async def check_invoice(bot: Bot, cp: CryptoPay, invoice_id: int) -> str:
    """Returns 'paid' | 'active' | 'expired' | 'already'."""
    row = await db.get_invoice(invoice_id)
    if row and row["status"] == "paid":
        return "already"
    items = await cp.get_invoices([invoice_id])
    status = items[0]["status"] if items else "expired"
    if status == "paid":
        await credit_paid_invoice(bot, invoice_id)
    elif status == "expired":
        await db.set_invoice_status(invoice_id, "expired")
    return status


def verify_webhook(token: str, body: bytes, signature: str) -> bool:
    """CryptoBot signs webhooks with HMAC-SHA256(body, key=SHA256(api_token))."""
    secret = hashlib.sha256(token.encode()).digest()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
