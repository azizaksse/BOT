"""Glue between the web endpoints and aiogram. Everything is created per request
(serverless functions don't stay running between requests)."""
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.types import BotCommand, Update

import db
from config import (BOT_TOKEN, BASTAHA_API_KEY, BASTAHA_BASE_URL,
                    NEXA_API_KEY, NEXA_BASE_URL,
                    TELEGRAM_API_BASE, WEBHOOK_SECRET)
from bastaha_api import BastahaClient
from handlers import admin, user
from i18n import COMMANDS
from middlewares import UserMiddleware
from multi_supplier import MultiSupplier
from nexa_api import NexaClient
from storage import PgStorage

log = logging.getLogger(__name__)

dp = Dispatcher(storage=PgStorage())
dp.message.outer_middleware(UserMiddleware())
dp.callback_query.outer_middleware(UserMiddleware())
dp.include_routers(admin.router, user.router)


def _make_bot() -> Bot:
    session = AiohttpSession(api=TelegramAPIServer.from_base(TELEGRAM_API_BASE)) if TELEGRAM_API_BASE else None
    return Bot(BOT_TOKEN, session=session,
               default=DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True))


@asynccontextmanager
async def request_context():
    await db.connect()
    bot = _make_bot()
    nexa = NexaClient(NEXA_BASE_URL, NEXA_API_KEY)
    bastaha = BastahaClient(BASTAHA_BASE_URL, BASTAHA_API_KEY) if BASTAHA_API_KEY else None
    supplier = MultiSupplier(nexa, bastaha)
    try:
        yield bot, supplier
    finally:
        await supplier.close()
        await bot.session.close()
        await db.close()


async def handle_telegram(payload: dict) -> None:
    async with request_context() as (bot, nexa):
        update = Update.model_validate(payload, context={"bot": bot})
        if not await db.claim(f"u:{update.update_id}"):
            return  # Telegram re-sent an update we already handled
        await dp.feed_update(bot, update, nexa=nexa)


async def setup(base_url: str) -> dict:
    async with request_context() as (bot, _nexa):
        await db.init_schema()
        await db.cleanup()
        hook = f"{base_url}/api/telegram"
        await bot.set_webhook(hook, secret_token=WEBHOOK_SECRET, drop_pending_updates=True,
                              allowed_updates=["message", "callback_query"])
        for lang, cmds in COMMANDS.items():
            await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in cmds],
                                      language_code=None if lang == "en" else lang)
        me = await bot.get_me()
        return {
            "ok": True,
            "bot": f"@{me.username}",
            "telegram_webhook": hook,
        }
