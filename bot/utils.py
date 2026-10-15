import html
import logging
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from config import ADMIN_IDS

log = logging.getLogger(__name__)


def esc(text) -> str:
    return html.escape(str(text or ""))


def fmt_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


async def safe_edit(c: CallbackQuery, text: str, kb: InlineKeyboardMarkup | None = None):
    """Edit the callback's message; fall back to sending a new one."""
    try:
        await c.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        await c.message.answer(text, reply_markup=kb)


async def notify_admins(bot: Bot, text: str, **kwargs):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, **kwargs)
        except Exception as e:  # admin blocked bot etc.
            log.warning("Could not notify admin %s: %s", admin_id, e)
