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
from config import (BOT_TOKEN, CRYPTOPAY_TESTNET, CRYPTOPAY_TOKEN, NEXA_API_KEY, NEXA_BASE_URL,
                    TELEGRAM_API_BASE, WEBHOOK_SECRET)
from cryptopay import CryptoPay
from handlers import admin, user
from i18n import COMMANDS
from middlewares import UserMiddleware
from nexa_api import NexaClient
from services import payments
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
    cp = CryptoPay(CRYPTOPAY_TOKEN, testnet=CRYPTOPAY_TESTNET)
    try:
        yield bot, nexa, cp
    finally:
        await nexa.close()
        await cp.close()
        await bot.session.close()
        await db.close()


async def handle_telegram(payload: dict) -> None:
    async with request_context() as (bot, nexa, cp):
        update = Update.model_validate(payload, context={"bot": bot})
        if not await db.claim(f"u:{update.update_id}"):
            return  # Telegram re-sent an update we already handled
        await dp.feed_update(bot, update, nexa=nexa, cp=cp)


def verify_cryptopay(body: bytes, signature: str) -> bool:
    return payments.verify_webhook(CRYPTOPAY_TOKEN, body, signature)


async def handle_cryptopay(data: dict) -> None:
    if data.get("update_type") != "invoice_paid":
        return
    invoice = data.get("payload") or {}
    if invoice.get("status") != "paid" or "invoice_id" not in invoice:
        return
    async with request_context() as (bot, _nexa, _cp):
        await payments.credit_paid_invoice(bot, int(invoice["invoice_id"]))


async def setup(base_url: str) -> dict:
    async with request_context() as (bot, _nexa, _cp):
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
            "next_step": f"Paste this URL in @CryptoBot -> Crypto Pay -> My Apps -> your app -> Webhooks: "
                         f"{base_url}/api/cryptopay",
        }
