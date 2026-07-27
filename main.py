"""Точка входа бота Selectel Market."""
import asyncio
import logging
import sys
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import database as db
from config import config
from middlewares.register import RegisterMiddleware
from webhook_server import create_webhook_app

# ─── Хендлеры ───────────────────────────────────────────────────────────────
from handlers import start, profile, support, catalog, topup, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not config.bot_token:
        logger.critical("BOT_TOKEN is not set in .env!")
        sys.exit(1)

    # Инициализация БД
    await db.init_db()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Middleware
    dp.message.middleware(RegisterMiddleware())
    dp.callback_query.middleware(RegisterMiddleware())

    # Роутеры (admin — первый, т.к. его фильтр IsAdmin ограничивает область)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(support.router)
    dp.include_router(catalog.router)
    dp.include_router(topup.router)

    # ── Запуск webhook-сервера для CryptoBot ────────────────────────────────
    runner = None
    if config.cryptobot_token:
        webhook_app = create_webhook_app(bot)
        runner = web.AppRunner(webhook_app)
        await runner.setup()
        site = web.TCPSite(runner, config.webhook_host, config.webhook_port)
        await site.start()
        logger.info(
            "Webhook server started on %s:%s%s",
            config.webhook_host, config.webhook_port, config.webhook_path
        )
    else:
        logger.warning(
            "Webhook server NOT started — set CRYPTOBOT_TOKEN in .env to enable"
        )

    logger.info("Starting Selectel Market bot (polling)...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if runner:
            await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
