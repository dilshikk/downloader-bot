from typing import Dict, Any, Callable, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class AdminLanguageMiddleware(BaseMiddleware):
    """Forces Russian language for all admin panel handlers."""

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        data["lang"] = "ru"
        return await handler(event, data)
