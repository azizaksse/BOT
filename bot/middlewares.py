from aiogram import BaseMiddleware

import db


class UserMiddleware(BaseMiddleware):
    """Registers the user, blocks banned users, and injects `lang` into handlers."""

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is None or user.is_bot:
            return await handler(event, data)
        row = await db.get_or_create_user(user.id, user.username, user.language_code)
        if row["banned"]:
            return None
        data["lang"] = row["lang"]
        return await handler(event, data)
