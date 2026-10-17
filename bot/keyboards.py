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
    # Row 1: preset amounts
    kb.row(*[Btn(text=f"{a} $", callback_data=f"top:{a}") for a in (5, 10, 25, 50)])
    kb.row(Btn(text=t(lang, "btn_custom"), callback_data="top:custom"))
    # Row 2: CARD
    kb.row(Btn(text="💳  CARD (Visa · Mastercard)", callback_data="top:card"))
    # Row 3: Binance Pay
    kb.row(Btn(text="🔶  Binance Pay (USDT/USDC/BTC)", callback_data="top:binance"))
    # Row 4: BEP-20 pair
    kb.row(
        Btn(text="🟢  USDT (BEP20 · BSC)",  callback_data="top:bsc"),
        Btn(text="🔵  USDC (BEP20 · BSC)",  callback_data="top:usdc_bsc"),
    )
    # Row 5: Polygon + TON
    kb.row(
        Btn(text="🟣  USDT (Polygon)",       callback_data="top:polygon"),
        Btn(text="💎  USDT TON",              callback_data="top:ton"),
    )
    kb.row(Btn(text=t(lang, "btn_orders"), callback_data="orders"),
           Btn(text=t(lang, "btn_back"), callback_data="menu"))
    return kb.as_markup()


def lang_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, name in LANGS.items():
        kb.row(Btn(text=name, callback_data=f"setlang:{code}"))
    return kb.as_markup()
