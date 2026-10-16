"""Admin commands (only for ADMIN_IDS). Replies are in English."""
import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import db
from config import ADMIN_IDS
from i18n import t
from money import fmt, to_cents
from nexa_api import NexaClient
from pricing import get_pricing, price_for
from services import purchase
from utils import esc

log = logging.getLogger(__name__)
router = Router()
router.message.filter(F.from_user.id.in_(ADMIN_IDS))

HELP = """⚡ <b>Admin panel</b>

<b>Stats</b>
/stats — sales, profit, users
/nexabal — Nexa supplier balance

<b>Pricing</b>
/markup — show markup
/markup 30 0.10 — set +30% and +$0.10 on every product
/aproducts — products with cost / sell price / short ID
/setprice &lt;id&gt; &lt;price&gt; — custom price for one product
/delprice &lt;id&gt; — remove custom price

<b>Users &amp; money</b>
/user &lt;user_id&gt; — user info
/addbal &lt;user_id&gt; &lt;amount&gt; — add (or remove with -) balance
/ban &lt;user_id&gt; · /unban &lt;user_id&gt;
/dm &lt;user_id&gt; &lt;text&gt; — reply to a support message

<b>Orders</b>
/find &lt;order_id&gt; — view any order
/retry &lt;order_id&gt; — retry a delayed order (no double charge)
/refund &lt;order_id&gt; — refund an order to the user's wallet

<b>Warranty</b>
/wreply &lt;id&gt; &lt;text&gt; — reply to customer
/wclose &lt;id&gt; — close request

<b>Broadcasts</b>
/broadcast &lt;text&gt; — send plain message to all users
/announce &lt;text&gt; — send a rich announcement to all users
/deal &lt;product_id&gt; &lt;your_price&gt; &lt;note&gt; — announce a limited deal
/newstock — broadcast all products that are currently in stock"""


def _args(command: CommandObject, n: int) -> list[str] | None:
    parts = (command.args or "").split(maxsplit=n - 1)
    return parts if len(parts) == n else None


async def _find_product(nexa: NexaClient, prefix: str):
    products = await nexa.products(force=True)
    matches = [p for p in products if p["id"].lower().startswith(prefix.lower())]
    return matches[0] if len(matches) == 1 else None


@router.message(Command("admin"))
async def cmd_admin(m: Message):
    await m.answer(HELP)


@router.message(Command("stats"))
async def cmd_stats(m: Message, nexa: NexaClient):
    s = await db.stats()
    try:
        nb = await nexa.balance()
        nexa_bal = f"{nb.get('balance')} {nb.get('currency', 'USDT')}"
    except Exception as e:
        nexa_bal = f"error: {esc(e)}"
    await m.answer(
        "📊 <b>Statistics</b>\n\n"
        f"👥 Users: <b>{s['users']}</b>\n"
        f"💰 Customer balances (liability): <b>{fmt(s['balances'])}$</b>\n"
        f"💵 Total top-ups: <b>{fmt(s['topups'])}$</b>\n\n"
        f"🛒 Orders: <b>{s['orders']}</b> · revenue <b>{fmt(s['revenue'])}$</b> · "
        f"profit <b>{fmt(s['revenue'] - s['cost'])}$</b>\n"
        f"🕐 Last 24h: <b>{s['orders_24h']}</b> · revenue <b>{fmt(s['revenue_24h'])}$</b> · "
        f"profit <b>{fmt(s['revenue_24h'] - s['cost_24h'])}$</b>\n\n"
        f"⚠️ Delayed orders: <b>{s['pending_orders']}</b>\n"
        f"🛠 Open warranties: <b>{s['open_warranties']}</b>\n\n"
        f"🏦 Nexa balance: <b>{nexa_bal}</b>"
    )


@router.message(Command("nexabal"))
async def cmd_nexabal(m: Message, nexa: NexaClient):
    try:
        nb = await nexa.balance()
        await m.answer(f"🏦 Nexa balance: <b>{nb.get('balance')} {nb.get('currency', 'USDT')}</b>")
    except Exception as e:
        await m.answer(f"❌ {esc(e)}")


@router.message(Command("markup"))
async def cmd_markup(m: Message, command: CommandObject):
    if command.args:
        parts = command.args.replace(",", ".").split()
        try:
            pct = float(parts[0])
            fixed = float(parts[1]) if len(parts) > 1 else 0.0
        except ValueError:
            return await m.answer("Usage: /markup 30 0.10")
        await db.set_setting("markup_percent", str(pct))
        await db.set_setting("markup_fixed", str(fixed))
    p = await get_pricing()
    await m.answer(f"📈 Markup: <b>+{p.percent}%</b> and <b>+{fmt(p.fixed)}$</b> per item\n"
                   f"Custom prices: <b>{len(p.overrides)}</b>")


@router.message(Command("aproducts"))
async def cmd_aproducts(m: Message, nexa: NexaClient):
    products = await nexa.products(force=True)
    pricing = await get_pricing()
    lines = []
    for p in products:
        star = "⭐" if p["id"] in pricing.overrides else ""
        lines.append(f"<code>{p['id'][:8]}</code> {esc(p['name'])}\n"
                     f"   cost {fmt(to_cents(p['price']))} → sell <b>{fmt(price_for(p, pricing))}</b>{star} · stock {p.get('stock', 0)}")
    if not lines:
        return await m.answer("No products.")
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) > 3800:
            await m.answer(chunk)
            chunk = ""
        chunk += line + "\n"
    await m.answer(chunk + "\n⭐ = custom price. Use the 8-char ID with /setprice")


@router.message(Command("setprice"))
async def cmd_setprice(m: Message, command: CommandObject, nexa: NexaClient):
    a = _args(command, 2)
    if not a:
        return await m.answer("Usage: /setprice &lt;id&gt; &lt;price&gt;")
    p = await _find_product(nexa, a[0])
    if not p:
        return await m.answer("❌ Product not found (or ID prefix not unique).")
    cents = to_cents(a[1].replace(",", "."))
    cost = to_cents(p["price"])
    await db.set_override(p["id"], cents)
    warn = "\n⚠️ Below cost — markup price will be used instead!" if cents < cost else ""
    await m.answer(f"✅ {esc(p['name'])}: <b>{fmt(cents)}$</b> (cost {fmt(cost)}$){warn}")


@router.message(Command("delprice"))
async def cmd_delprice(m: Message, command: CommandObject, nexa: NexaClient):
    p = await _find_product(nexa, (command.args or "").strip()) if command.args else None
    if not p:
        return await m.answer("Usage: /delprice &lt;id&gt;")
    ok = await db.del_override(p["id"])
    await m.answer("✅ Custom price removed." if ok else "No custom price for this product.")


@router.message(Command("user"))
async def cmd_user(m: Message, command: CommandObject):
    if not (command.args or "").strip().isdigit():
        return await m.answer("Usage: /user &lt;user_id&gt;")
    u = await db.get_user(int(command.args))
    if not u:
        return await m.answer("User not found.")
    orders = await db.user_orders(u["id"], 5)
    lines = [f"• <code>{o['id']}</code> {esc(o['product_name'])} × {o['quantity']} · {fmt(o['total'])}$ · {o['status']}"
             for o in orders]
    await m.answer(
        f"👤 <code>{u['id']}</code> @{esc(u['username'] or '-')}\n"
        f"Lang: {u['lang']} · Banned: {'yes' if u['banned'] else 'no'}\n"
        f"Balance: <b>{fmt(u['balance'])}$</b>\n\nLast orders:\n" + ("\n".join(lines) or "—")
    )


@router.message(Command("addbal"))
async def cmd_addbal(m: Message, command: CommandObject, bot: Bot):
    a = _args(command, 2)
    if not a or not a[0].isdigit():
        return await m.answer("Usage: /addbal &lt;user_id&gt; &lt;amount&gt;")
    uid, cents = int(a[0]), to_cents(a[1].replace(",", "."))
    if cents >= 0:
        ok = await db.credit(uid, cents, "admin", str(m.from_user.id))
    else:
        ok = await db.debit(uid, -cents, "admin", str(m.from_user.id))
    if not ok:
        return await m.answer("❌ Failed (unknown user or not enough balance).")
    u = await db.get_user(uid)
    await m.answer(f"✅ New balance of <code>{uid}</code>: <b>{fmt(u['balance'])}$</b>")
    try:
        await bot.send_message(uid, t(u["lang"], "balance_adjusted", amount=fmt(cents), balance=fmt(u["balance"])))
    except Exception:
        pass


@router.message(Command("ban", "unban"))
async def cmd_ban(m: Message, command: CommandObject):
    if not (command.args or "").strip().isdigit():
        return await m.answer("Usage: /ban &lt;user_id&gt;")
    banned = command.command == "ban"
    ok = await db.set_banned(int(command.args), banned)
    await m.answer(("🚫 Banned" if banned else "✅ Unbanned") if ok else "User not found.")


@router.message(Command("retry"))
async def cmd_retry(m: Message, command: CommandObject, bot: Bot, nexa: NexaClient):
    o = await db.get_order((command.args or "").strip()) if command.args else None
    if not o:
        return await m.answer("Usage: /retry &lt;order_id&gt;")
    if o["status"] not in ("pending", "processing"):
        return await m.answer(f"Order status is <b>{o['status']}</b> — nothing to retry.")
    await m.answer("⏳ Retrying…")
    result = await purchase.execute_order(bot, nexa, o["id"])
    await m.answer(f"Result: <b>{result}</b>")


@router.message(Command("refund"))
async def cmd_refund(m: Message, command: CommandObject, bot: Bot):
    o = await db.get_order((command.args or "").strip()) if command.args else None
    if not o:
        return await m.answer("Usage: /refund &lt;order_id&gt;")
    if not await db.refund_order(o["id"]):
        return await m.answer("❌ Already refunded.")
    await m.answer(f"✅ Refunded {fmt(o['total'])}$ to <code>{o['user_id']}</code>")
    lang = await db.get_lang(o["user_id"])
    try:
        await bot.send_message(o["user_id"], t(lang, "refund_admin", id=o["id"], total=fmt(o["total"])))
    except Exception:
        pass


@router.message(Command("wreply"))
async def cmd_wreply(m: Message, command: CommandObject, bot: Bot):
    a = _args(command, 2)
    if not a or not a[0].isdigit():
        return await m.answer("Usage: /wreply &lt;id&gt; &lt;text&gt;")
    w = await db.get_warranty(int(a[0]))
    if not w:
        return await m.answer("Warranty not found.")
    await db.update_warranty(w["id"], "answered", a[1])
    lang = await db.get_lang(w["user_id"])
    try:
        await bot.send_message(w["user_id"], t(lang, "warranty_reply", id=w["id"], text=esc(a[1])))
        await m.answer("✅ Sent.")
    except Exception as e:
        await m.answer(f"❌ Could not deliver: {esc(e)}")


@router.message(Command("wclose"))
async def cmd_wclose(m: Message, command: CommandObject, bot: Bot):
    if not (command.args or "").strip().isdigit():
        return await m.answer("Usage: /wclose &lt;id&gt;")
    w = await db.get_warranty(int(command.args))
    if not w:
        return await m.answer("Warranty not found.")
    await db.update_warranty(w["id"], "closed")
    lang = await db.get_lang(w["user_id"])
    try:
        await bot.send_message(w["user_id"], t(lang, "warranty_closed", id=w["id"]))
    except Exception:
        pass
    await m.answer("✅ Closed.")


@router.message(Command("broadcast"))
async def cmd_broadcast(m: Message, command: CommandObject, bot: Bot):
    source = m.reply_to_message
    if not source and not command.args:
        return await m.answer("Usage: /broadcast &lt;text&gt; or reply to a message with /broadcast")
    ids = await db.all_user_ids()
    await m.answer(f"📣 Sending to {len(ids)} users…")
    sent = 0
    for uid in ids:
        try:
            if source:
                await source.copy_to(uid)
            else:
                await bot.send_message(uid, command.args)
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await m.answer(f"✅ Delivered to {sent}/{len(ids)} users.")


@router.message(Command("dm"))
async def cmd_dm(m: Message, command: CommandObject, bot: Bot):
    """Reply to a support message: /dm <user_id> <text>"""
    a = _args(command, 2)
    if not a or not a[0].isdigit():
        return await m.answer("Usage: /dm &lt;user_id&gt; &lt;text&gt;")
    uid = int(a[0])
    try:
        await bot.send_message(uid, f"🎧 <b>Support reply:</b>\n\n{esc(a[1])}")
        await m.answer(f"✅ Message delivered to <code>{uid}</code>")
    except Exception as e:
        await m.answer(f"❌ Could not deliver: {esc(e)}")


@router.message(Command("announce"))
async def cmd_announce(m: Message, command: CommandObject, bot: Bot):
    """Send a rich announcement to all users."""
    source = m.reply_to_message
    text = command.args or ""
    if not source and not text:
        return await m.answer("Usage: /announce &lt;text&gt; or reply to a message with /announce")
    ids = await db.all_user_ids()
    await m.answer(f"📢 Sending announcement to {len(ids)} users…")
    sent = 0
    announcement = f"📢 <b>Store Update!</b>\n\n{text}" if text else None
    for uid in ids:
        try:
            if source:
                await source.copy_to(uid)
            else:
                await bot.send_message(uid, announcement)
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await m.answer(f"✅ Announcement delivered to {sent}/{len(ids)} users.")


@router.message(Command("deal"))
async def cmd_deal(m: Message, command: CommandObject, bot: Bot, nexa: NexaClient):
    """Announce a limited-time deal: /deal <product_id> <price> [note]"""
    parts = (command.args or "").split(maxsplit=2)
    if len(parts) < 2:
        return await m.answer("Usage: /deal &lt;product_id&gt; &lt;price&gt; [note]\nExample: /deal 91 1.99 Flash sale — 24h only!")
    product = await _find_product(nexa, parts[0])
    if not product:
        return await m.answer("❌ Product not found.")
    try:
        sale_price = float(parts[1].replace(",", "."))
    except ValueError:
        return await m.answer("❌ Invalid price.")
    note = parts[2] if len(parts) > 2 else "⏰ Limited time only!"
    ids = await db.all_user_ids()
    await m.answer(f"🔥 Sending deal to {len(ids)} users…")
    msg = (
        f"🔥 <b>LIMITED DEAL!</b>\n\n"
        f"🏷 <b>{esc(product['name'])}</b>\n"
        f"💵 Price: <b>${sale_price:.2f} USDT</b>\n"
        f"⚡ Instant delivery\n\n"
        f"{esc(note)}"
    )
    sent = 0
    for uid in ids:
        try:
            await bot.send_message(uid, msg)
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await m.answer(f"✅ Deal sent to {sent}/{len(ids)} users.")


@router.message(Command("newstock"))
async def cmd_newstock(m: Message, bot: Bot, nexa: NexaClient):
    """Broadcast all currently in-stock products to all users."""
    try:
        products = await nexa.products(force=True)
    except Exception as e:
        return await m.answer(f"❌ Could not fetch products: {esc(e)}")
    in_stock = [p for p in products if p.get("in_stock") and p.get("stock", 0) > 0]
    if not in_stock:
        return await m.answer("No products currently in stock.")
    pricing = await get_pricing()
    lines = []
    for p in in_stock[:20]:
        sell = price_for(p, pricing)
        lines.append(f"✅ <b>{esc(p['name'])}</b> — <b>{fmt(sell)}$</b> · Stock: {p['stock']}")
    msg = (
        f"🛒 <b>Products Available Now!</b>\n\n"
        + "\n".join(lines)
        + "\n\n⚡ Instant delivery · Open the store to order!"
    )
    ids = await db.all_user_ids()
    await m.answer(f"📦 Sending stock update to {len(ids)} users…")
    sent = 0
    for uid in ids:
        try:
            await bot.send_message(uid, msg)
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await m.answer(f"✅ Stock update sent to {sent}/{len(ids)} users.")

