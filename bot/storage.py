"""aiogram FSM storage in Postgres (memory is wiped between Vercel requests)."""
import json
from typing import Any

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

import db


def _k(key: StorageKey) -> str:
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}"


class PgStorage(BaseStorage):
    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        value = state.state if isinstance(state, State) else state
        await db.fsm_set_state(_k(key), value)

    async def get_state(self, key: StorageKey) -> str | None:
        row = await db.fsm_get(_k(key))
        return row["state"] if row else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        await db.fsm_set_data(_k(key), data)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        row = await db.fsm_get(_k(key))
        return json.loads(row["data"]) if row and row["data"] else {}

    async def close(self) -> None:
        pass
