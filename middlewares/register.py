"""Middleware: регистрация пользователей и проверка бана."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

import database as db


class RegisterMiddleware(BaseMiddleware):
    """Автоматически регистрирует / обновляет пользователя в БД."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user

        if user and not user.is_bot:
            full_name = (user.full_name or "").strip() or str(user.id)
            db_user = await db.get_or_create_user(user.id, user.username, full_name)
            data["db_user"] = db_user

            if db_user.get("is_banned"):
                if isinstance(event, Message):
                    await event.answer("🚫 Ваш аккаунт заблокирован. Обратитесь в поддержку.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 Аккаунт заблокирован.", show_alert=True)
                return

        return await handler(event, data)
