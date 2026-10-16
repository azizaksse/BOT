import json
import logging
import math

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db
from config import ADMIN_IDS, MAX_TOPUP, MIN_TOPUP, SUPPORT_USERNAME
from cryptopay import CryptoPay
from i18n import LANGS, t
from keyboards import back_kb, lang_kb, main_menu_kb, topup_kb
from money import fmt, to_cents
from nexa_api import NexaClient
from pricing import get_pricing, price_for
from services import payments, purchase
from utils import esc, fmt_date, notify_admins, safe_edit

log = logging.getLogger(__name__)
router = Router()
PAGE_SIZE = 8


class TopUp(StatesGroup):
    amount = State()


class FindOrder(StatesGroup):
    order_id = State()


class WarrantyForm(StatesGroup):
    order_id = State()
    issue = State()


class SupportMsg(StatesGroup):
    message = State()


# ======================= MENU =======================
async def _menu_text(uid: int, lang: str) -> str:
    user = await db.get_user(uid)
    return t(lang, "menu_title", balance=fmt(user["balance"]))


@router.message(CommandStart())
async def cmd_start(m: Message, lang: str, state: FSMContext):
    await state.clear()
    user = await db.get_user(m.from_user.id)
    await m.answer(t(lang, "welcome", name=esc(m.from_user.first_name), balance=fmt(user["balance"])),
                   reply_markup=main_menu_kb(lang))


@router.message(Command("menu"))
async def cmd_menu(m: Message, lang: str, state: FSMContext):
    await state.clear()
    await m.answer(await _menu_text(m.from_user.id, lang), reply_markup=main_menu_kb(lang))


@router.message(Command("cancel"))
async def cmd_cancel(m: Message, lang: str, state: FSMContext):
    await state.clear()
    await m.answer(t(lang, "cancelled"), reply_markup=main_menu_kb(lang))


@router.callback_query(F.data == "menu")
async def cb_menu(c: CallbackQuery, lang: str, state: FSMContext):
    await state.clear()
    await safe_edit(c, await _menu_text(c.from_user.id, lang), main_menu_kb(lang))
    await c.answer()


# ======================= LANGUAGE =======================
@router.message(Command("lang"))
async def cmd_lang(m: Message, lang: str):
    await m.answer(t(lang, "choose_lang"), reply_markup=lang_kb())


@router.callback_query(F.data == "lang")
async def cb_lang(c: CallbackQuery, lang: str):
    await safe_edit(c, t(lang, "choose_lang"), lang_kb())
    await c.answer()


@router.callback_query(F.data.startswith("setlang:"))
async def cb_setlang(c: CallbackQuery):
    new = c.data.split(":")[1]
    if new not in LANGS:
        return await c.answer()
    await db.set_lang(c.from_user.id, new)
    await c.answer(t(new, "lang_set"))
    await safe_edit(c, await _menu_text(c.from_user.id, new), main_menu_kb(new))


# ======================= PRODUCTS =======================
async def _products_view(lang: str, nexa: NexaClient, page: int, force: bool = False):
    try:
        products = await nexa.products(force=force)
    except Exception as e:
        log.error("products error: %s", e)
        return t(lang, "service_unavailable"), back_kb(lang)
    if not products:
        return t(lang, "no_products"), back_kb(lang)
    pricing = await get_pricing()
    pages = max(1, math.ceil(len(products) / PAGE_SIZE))
    page = max(0, min(page, pages - 1))
    kb = InlineKeyboardBuilder()
    for p in products[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        icon = "🟢" if p.get("in_stock") and p.get("stock", 0) > 0 else "🔴"
        kb.row(Btn(text=f"{icon} {p['name']} • {fmt(price_for(p, pricing))}$", callback_data=f"prod:{p['id']}"))
    nav = []
    if page > 0:
        nav.append(Btn(text="◀️", callback_data=f"plist:{page - 1}"))
    if page < pages - 1:
        nav.append(Btn(text="▶️", callback_data=f"plist:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(Btn(text=t(lang, "btn_refresh"), callback_data=f"plist:{page}:r"),
           Btn(text=t(lang, "btn_back"), callback_data="menu"))
    return t(lang, "products_title", page=page + 1, pages=pages), kb.as_markup()


@router.message(Command("products"))
async def cmd_products(m: Message, lang: str, nexa: NexaClient, state: FSMContext):
    await state.clear()
    text, kb = await _products_view(lang, nexa, 0)
    await m.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("plist:"))
async def cb_products(c: CallbackQuery, lang: str, nexa: NexaClient):
    parts = c.data.split(":")
    text, kb = await _products_view(lang, nexa, int(parts[1]), force=len(parts) > 2)
    await safe_edit(c, text, kb)
    await c.answer()


@router.callback_query(F.data.startswith("prod:"))
async def cb_product(c: CallbackQuery, lang: str, nexa: NexaClient):
    pid = c.data[5:]
    try:
        p = await nexa.get_product(pid)
    except Exception:
        return await c.answer(t(lang, "service_unavailable"), show_alert=True)
    if not p:
        return await c.answer(t(lang, "product_not_found"), show_alert=True)
    price = price_for(p, await get_pricing())
    stock = int(p.get("stock", 0)) if p.get("in_stock") else 0
    text = t(lang, "product_card", name=esc(p["name"]), price=fmt(price), stock=stock)
    # Show description if available
    desc = (p.get("description") or "").strip()
    if desc:
        # Trim to keep message short
        desc_short = desc[:600] + ("…" if len(desc) > 600 else "")
        text += f"\n\n📝 <i>{esc(desc_short)}</i>"
    kb = InlineKeyboardBuilder()
    if stock > 0:
        text += "\n\n" + t(lang, "choose_qty")
        kb.row(*[Btn(text=str(n), callback_data=f"qty:{pid}:{n}") for n in (1, 2, 3, 5, 10) if n <= stock])
    else:
        text += "\n\n" + t(lang, "out_of_stock")
    kb.row(Btn(text=t(lang, "btn_back"), callback_data="plist:0"))
    await safe_edit(c, text, kb.as_markup())
    await c.answer()


@router.callback_query(F.data.startswith("qty:"))
async def cb_qty(c: CallbackQuery, lang: str, nexa: NexaClient):
    _, pid, n = c.data.split(":")
    qty = int(n)
    p = await nexa.get_product(pid)
    if not p:
        return await c.answer(t(lang, "product_not_found"), show_alert=True)
    total = price_for(p, await get_pricing()) * qty
    user = await db.get_user(c.from_user.id)
    kb = InlineKeyboardBuilder()
    if user["balance"] >= total:
        kb.row(Btn(text=t(lang, "btn_confirm"), callback_data=f"buy:{pid}:{qty}"))
    else:
        kb.row(Btn(text=t(lang, "btn_topup"), callback_data="wallet"))
    kb.row(Btn(text=t(lang, "btn_cancel"), callback_data=f"prod:{pid}"))
    await safe_edit(c, t(lang, "confirm_purchase", name=esc(p["name"]), qty=qty, total=fmt(total),
                         balance=fmt(user["balance"])), kb.as_markup())
    await c.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(c: CallbackQuery, lang: str, nexa: NexaClient, bot: Bot):
    _, pid, n = c.data.split(":")
    qty = max(1, min(int(n), 10))
    # one purchase per confirmation message (stops double taps & Telegram retries)
    if not await db.claim(f"buy:{c.message.chat.id}:{c.message.message_id}"):
        return await c.answer(t(lang, "please_wait"), show_alert=True)
    await c.answer()
    await safe_edit(c, t(lang, "processing"))
    result = await purchase.start_purchase(bot, nexa, c.from_user.id, lang, pid, qty)
    if result is None:  # success / delayed: user already got a new message
        try:
            await c.message.delete()
        except Exception:
            pass
    else:
        text, kb = result
        await safe_edit(c, text, kb or back_kb(lang, "plist:0"))


# ======================= WALLET / TOP-UP =======================
async def _wallet_text(uid: int, lang: str) -> str:
    user = await db.get_user(uid)
    return t(lang, "wallet", balance=fmt(user["balance"]))


@router.message(Command("wallet"))
async def cmd_wallet(m: Message, lang: str, state: FSMContext):
    await state.clear()
    await m.answer(await _wallet_text(m.from_user.id, lang), reply_markup=topup_kb(lang))


@router.callback_query(F.data == "wallet")
async def cb_wallet(c: CallbackQuery, lang: str, state: FSMContext):
    await state.clear()
    await safe_edit(c, await _wallet_text(c.from_user.id, lang), topup_kb(lang))
    await c.answer()


async def _create_topup(msg: Message, uid: int, lang: str, cp: CryptoPay, amount: float):
    try:
        inv = await cp.create_invoice(amount, payload=str(uid), description=f"Wallet top-up {amount:.2f} USDT")
    except Exception as e:
        log.error("createInvoice failed: %s", e)
        return await msg.answer(t(lang, "invoice_error"))
    await db.add_invoice(inv["invoice_id"], uid, to_cents(amount), inv["url"])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text=t(lang, "btn_pay"), url=inv["url"])],
        [Btn(text=t(lang, "btn_check"), callback_data=f"chk:{inv['invoice_id']}")],
        [Btn(text=t(lang, "btn_menu"), callback_data="menu")],
    ])
    await msg.answer(t(lang, "invoice_created", amount=f"{amount:.2f}"), reply_markup=kb)


@router.callback_query(F.data.startswith("top:"))
async def cb_topup(c: CallbackQuery, lang: str, cp: CryptoPay, state: FSMContext):
    val = c.data.split(":")[1]
    await c.answer()
    if val == "custom":
        await state.set_state(TopUp.amount)
        return await c.message.answer(t(lang, "enter_amount", min=MIN_TOPUP, max=MAX_TOPUP))
    await _create_topup(c.message, c.from_user.id, lang, cp, float(val))


@router.callback_query(F.data.startswith("chk:"))
async def cb_check(c: CallbackQuery, lang: str, cp: CryptoPay, bot: Bot):
    invoice_id = int(c.data.split(":")[1])
    inv = await db.get_invoice(invoice_id)
    if not inv or inv["user_id"] != c.from_user.id:
        return await c.answer()
    try:
        status = await payments.check_invoice(bot, cp, invoice_id)
    except Exception:
        return await c.answer(t(lang, "service_unavailable"), show_alert=True)
    if status == "paid":
        await c.answer("✅")
        try:
            await c.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    elif status == "already":
        await c.answer(t(lang, "payment_already"), show_alert=True)
    elif status == "expired":
        await c.answer(t(lang, "payment_expired"), show_alert=True)
    else:
        await c.answer(t(lang, "payment_pending"), show_alert=True)


# ======================= ORDERS / FIND =======================
def _status(lang: str, status: str) -> str:
    return t(lang, f"st_{status}")


async def _orders_view(uid: int, lang: str):
    orders = await db.user_orders(uid, 10)
    kb = InlineKeyboardBuilder()
    for o in orders:
        icon = _status(lang, o["status"]).split()[0]
        kb.row(Btn(text=f"{icon} {o['id']} · {o['product_name'][:28]}", callback_data=f"ord:{o['id']}"))
    kb.row(Btn(text=t(lang, "btn_back"), callback_data="menu"))
    text = t(lang, "orders_title") if orders else t(lang, "no_orders")
    return text, kb.as_markup()


async def _order_details(order_id: str, uid: int, lang: str) -> tuple[str, bool]:
    o = await db.get_order(order_id)
    if not o or (o["user_id"] != uid and uid not in ADMIN_IDS):
        return t(lang, "order_not_found"), False
    text = t(lang, "order_details", id=o["id"], name=esc(o["product_name"]), qty=o["quantity"],
             total=fmt(o["total"]), status=_status(lang, o["status"]), date=fmt_date(o["created_at"]))
    if o["status"] == "completed" and o["codes"]:
        codes = json.loads(o["codes"])
        body = "\n\n".join(f"<code>{esc(x)}</code>" for x in codes)
        if len(text) + len(body) < 3900:
            text += "\n\n🔑\n" + body
    if uid in ADMIN_IDS and o["user_id"] != uid:
        text += f"\n\n👤 user <code>{o['user_id']}</code> · cost {fmt(o['cost'])}"
    return text, True


@router.message(Command("find"))
async def cmd_find(m: Message, lang: str, command: CommandObject, state: FSMContext):
    await state.clear()
    if command.args:
        text, _ = await _order_details(command.args.strip(), m.from_user.id, lang)
        return await m.answer(text, reply_markup=back_kb(lang, "orders"))
    text, kb = await _orders_view(m.from_user.id, lang)
    await m.answer(text + "\n\n" + t(lang, "find_prompt"), reply_markup=kb)
    await state.set_state(FindOrder.order_id)


@router.callback_query(F.data == "orders")
async def cb_orders(c: CallbackQuery, lang: str, state: FSMContext):
    text, kb = await _orders_view(c.from_user.id, lang)
    await safe_edit(c, text, kb)
    await state.set_state(FindOrder.order_id)
    await c.answer()


@router.callback_query(F.data.startswith("ord:"))
async def cb_order(c: CallbackQuery, lang: str):
    text, _ = await _order_details(c.data[4:], c.from_user.id, lang)
    await safe_edit(c, text, back_kb(lang, "orders"))
    await c.answer()


# ======================= WARRANTY =======================
async def _warranty_view(uid: int, lang: str):
    rows = await db.user_warranties(uid)
    lines = [t(lang, "warranty_title"), ""]
    if rows:
        lines += [t(lang, "warranty_item", id=w["id"], order=w["order_id"], status=t(lang, f"w_{w['status']}"))
                  for w in rows]
    else:
        lines.append(t(lang, "no_warranties"))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text=t(lang, "btn_new_warranty"), callback_data="wnew")],
        [Btn(text=t(lang, "btn_back"), callback_data="menu")],
    ])
    return "\n".join(lines), kb


@router.message(Command("warranty"))
async def cmd_warranty(m: Message, lang: str, state: FSMContext):
    await state.clear()
    text, kb = await _warranty_view(m.from_user.id, lang)
    await m.answer(text, reply_markup=kb)


@router.callback_query(F.data == "warranty")
async def cb_warranty(c: CallbackQuery, lang: str, state: FSMContext):
    await state.clear()
    text, kb = await _warranty_view(c.from_user.id, lang)
    await safe_edit(c, text, kb)
    await c.answer()


@router.callback_query(F.data == "wnew")
async def cb_wnew(c: CallbackQuery, lang: str, state: FSMContext):
    orders = [o for o in await db.user_orders(c.from_user.id, 10) if o["status"] == "completed"]
    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.row(Btn(text=f"{o['id']} · {o['product_name'][:28]}", callback_data=f"word:{o['id']}"))
    kb.row(Btn(text=t(lang, "btn_cancel"), callback_data="warranty"))
    await state.set_state(WarrantyForm.order_id)
    await safe_edit(c, t(lang, "warranty_ask_order"), kb.as_markup())
    await c.answer()


async def _warranty_pick_order(target: Message, uid: int, lang: str, order_id: str, state: FSMContext):
    o = await db.get_order(order_id.strip())
    if not o or o["user_id"] != uid or o["status"] != "completed":
        return await target.answer(t(lang, "warranty_bad_order"))
    existing = await db.open_warranty_for_order(o["id"])
    if existing:
        await state.clear()
        return await target.answer(t(lang, "warranty_exists", id=existing["id"]), reply_markup=back_kb(lang, "warranty"))
    await state.update_data(order_id=o["id"])
    await state.set_state(WarrantyForm.issue)
    await target.answer(t(lang, "warranty_ask_issue"))


@router.callback_query(F.data.startswith("word:"))
async def cb_word(c: CallbackQuery, lang: str, state: FSMContext):
    await c.answer()
    await _warranty_pick_order(c.message, c.from_user.id, lang, c.data[5:], state)


# ======================= SUPPORT =======================
def _support_view(lang: str):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="📨 " + t(lang, "btn_contact"), callback_data="support_msg")],
        *([
            [Btn(text="💬 " + t(lang, "btn_contact") + " (Telegram)", url=f"https://t.me/{SUPPORT_USERNAME}")]
        ] if SUPPORT_USERNAME else []),
        [Btn(text=t(lang, "btn_back"), callback_data="menu")],
    ])
    return t(lang, "support_text"), kb


@router.message(Command("support"))
async def cmd_support(m: Message, lang: str, state: FSMContext):
    await state.clear()
    text, kb = _support_view(lang)
    await m.answer(text, reply_markup=kb)


@router.callback_query(F.data == "support")
async def cb_support(c: CallbackQuery, lang: str, state: FSMContext):
    await state.clear()
    text, kb = _support_view(lang)
    await safe_edit(c, text, kb)
    await c.answer()


@router.callback_query(F.data == "support_msg")
async def cb_support_msg(c: CallbackQuery, lang: str, state: FSMContext):
    await state.set_state(SupportMsg.message)
    await c.answer()
    await safe_edit(c, "📨 <b>Send us a message</b>\n\nType your question or issue below — we'll get back to you soon!",
                    InlineKeyboardMarkup(inline_keyboard=[[Btn(text=t(lang, "btn_cancel"), callback_data="support")]]))


@router.message(SupportMsg.message, F.text | F.photo)
async def st_support_msg(m: Message, lang: str, state: FSMContext, bot: Bot):
    await state.clear()
    text = (m.text or m.caption or "(media)").strip()[:2000]
    who = f"@{esc(m.from_user.username)}" if m.from_user.username else esc(m.from_user.full_name)
    await notify_admins(
        bot,
        f"🎧 <b>Support message</b> from {who} (<code>{m.from_user.id}</code>)\n\n"
        f"{esc(text)}\n\n"
        f"Reply: <code>/dm {m.from_user.id} your reply here</code>"
    )
    if m.photo:
        for admin_id in ADMIN_IDS:
            try:
                await m.copy_to(admin_id)
            except Exception:
                pass
    await m.answer("✅ <b>Message sent!</b>\n\nOur team will reply to you here soon.",
                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[Btn(text=t(lang, "btn_menu"), callback_data="menu")]]))


# ======================= TEXT INPUT STATES (keep last) =======================
@router.message(TopUp.amount, F.text)
async def st_topup_amount(m: Message, lang: str, cp: CryptoPay, state: FSMContext):
    try:
        amount = round(float(m.text.replace(",", ".").replace("$", "").strip()), 2)
    except ValueError:
        amount = -1
    if not (MIN_TOPUP <= amount <= MAX_TOPUP):
        return await m.answer(t(lang, "invalid_amount", min=MIN_TOPUP, max=MAX_TOPUP))
    await state.clear()
    await _create_topup(m, m.from_user.id, lang, cp, amount)


@router.message(FindOrder.order_id, F.text)
async def st_find(m: Message, lang: str, state: FSMContext):
    text, found = await _order_details(m.text.strip(), m.from_user.id, lang)
    if found:
        await state.clear()
    await m.answer(text, reply_markup=back_kb(lang, "orders"))


@router.message(WarrantyForm.order_id, F.text)
async def st_warranty_order(m: Message, lang: str, state: FSMContext):
    await _warranty_pick_order(m, m.from_user.id, lang, m.text, state)


@router.message(WarrantyForm.issue, F.text | F.photo)
async def st_warranty_issue(m: Message, lang: str, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data.get("order_id")
    issue = (m.text or m.caption or "(screenshot)").strip()[:1500]
    await state.clear()
    wid = await db.create_warranty(m.from_user.id, order_id, issue)
    await m.answer(t(lang, "warranty_created", id=wid), reply_markup=main_menu_kb(lang))
    o = await db.get_order(order_id)
    who = f"@{esc(m.from_user.username)}" if m.from_user.username else esc(m.from_user.full_name)
    await notify_admins(
        bot,
        f"🛠 <b>Warranty #{wid}</b> from {who} (<code>{m.from_user.id}</code>)\n"
        f"Order: <code>{order_id}</code> · {esc(o['product_name'])} × {o['quantity']}\n\n"
        f"{esc(issue)}\n\n"
        f"Reply: <code>/wreply {wid} your message</code>\nClose: <code>/wclose {wid}</code>\n"
        f"Refund: <code>/refund {order_id}</code>",
    )
    if m.photo:
        for admin_id in ADMIN_IDS:
            try:
                await m.copy_to(admin_id)
            except Exception:
                pass
