from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from i18n import LANGS, t


def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(Btn(text=t(lang, "btn_products"), callback_data="plist:0"))
    kb.row(Btn(text=t(lang, "btn_wallet"), callback_data="wallet"),
           Btn(text=t(lang, "btn_orders"), callback_data="orders"))
    kb.row(Btn(text=t(lang, "btn_warranty"), callback_data="warranty"),
           Btn(text=t(lang, "btn_support"), callback_data="support"))
    kb.row(Btn(text=t(lang, "btn_lang"), callback_data="lang"))
    return kb.as_markup()


def back_kb(lang: str, to: str = "menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[Btn(text=t(lang, "btn_back"), callback_data=to)]])


def topup_kb(lang: str) -> InlineKeyboardMarkup:
    from config import BINANCE_PAY_PARTNER_ID
    kb = InlineKeyboardBuilder()
    kb.row(*[Btn(text=f"{a} $", callback_data=f"top:{a}") for a in (5, 10, 25, 50)])
    kb.row(Btn(text=t(lang, "btn_custom"), callback_data="top:custom"))
    kb.row(Btn(text="🔗 BEP-20 / BSC (USDT)", callback_data="top:bsc"))
    if BINANCE_PAY_PARTNER_ID:
        kb.row(Btn(text="💛 Binance Pay (USDT)", callback_data="top:binance"))
    kb.row(Btn(text=t(lang, "btn_orders"), callback_data="orders"),
           Btn(text=t(lang, "btn_back"), callback_data="menu"))
    return kb.as_markup()


def lang_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, name in LANGS.items():
        kb.row(Btn(text=name, callback_data=f"setlang:{code}"))
    return kb.as_markup()
