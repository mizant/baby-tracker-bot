import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import BOT_TOKEN
from app.db import init_db, get_session
from app.handlers import start, feeding, sleep, diaper, weight, stats, undo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Главное меню"),
    ]
    await bot.set_my_commands(commands)


async def main():
    logger.info("Starting Baby Tracker Bot...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Setup bot and dispatcher
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Set bot commands
    await set_commands(bot)

    # Register routers
    dp.include_router(start.router)
    dp.include_router(feeding.router)
    dp.include_router(sleep.router)
    dp.include_router(diaper.router)
    dp.include_router(weight.router)
    dp.include_router(stats.router)
    dp.include_router(undo.router)

    # Add database session middleware
    from aiogram.dispatcher.event.handler import HandlerObject

    async def session_middleware(handler, event, data):
        async for session in get_session():
            data["session"] = session
            return await handler(event, data)

    dp.update.outer_middleware(session_middleware)

    logger.info("Bot is running...")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
