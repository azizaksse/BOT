"""Vercel entry point. Routes:
  POST /api/telegram   <- Telegram updates (webhook)
  POST /api/cryptopay  <- CryptoBot "invoice_paid" notifications
  GET  /api/setup?key=SETUP_KEY  <- run once after each deploy (creates tables, sets webhook)
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bot"))

from starlette.applications import Starlette  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse, PlainTextResponse  # noqa: E402
from starlette.routing import Route  # noqa: E402

import core  # noqa: E402
from config import PUBLIC_URL, SETUP_KEY, WEBHOOK_SECRET  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")


async def telegram(request: Request):
    if request.headers.get("x-telegram-bot-api-secret-token") != WEBHOOK_SECRET:
        return JSONResponse({"ok": False}, status_code=403)
    try:
        await core.handle_telegram(await request.json())
    except Exception:
        # always answer 200, otherwise Telegram keeps re-sending the same update
        log.exception("update failed")
    return JSONResponse({"ok": True})


async def cryptopay(request: Request):
    body = await request.body()
    if not core.verify_cryptopay(body, request.headers.get("crypto-pay-api-signature", "")):
        return JSONResponse({"ok": False}, status_code=401)
    try:
        await core.handle_cryptopay(json.loads(body))
    except Exception:
        log.exception("cryptopay webhook failed")
        return JSONResponse({"ok": False}, status_code=500)  # CryptoBot will retry
    return JSONResponse({"ok": True})


async def setup(request: Request):
    if request.query_params.get("key") != SETUP_KEY:
        return JSONResponse({"ok": False, "error": "wrong key"}, status_code=403)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    try:
        return JSONResponse(await core.setup(PUBLIC_URL or f"https://{host}"))
    except Exception as e:
        log.exception("setup failed")
        return JSONResponse({"ok": False, "error": repr(e)}, status_code=500)


async def home(request: Request):
    return PlainTextResponse("✅ Bot server is running.")


app = Starlette(routes=[
    Route("/api/telegram", telegram, methods=["POST"]),
    Route("/api/cryptopay", cryptopay, methods=["POST"]),
    Route("/api/setup", setup, methods=["GET"]),
    Route("/", home),
])
