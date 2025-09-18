import asyncio
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot
from aiogram.types import BotCommand


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django  # noqa: E402, I001

django.setup()


from telegram_bot import bot, dp  # noqa: E402
from telegram_bot.handlers import access_control, admin, config_manager, help, start  # noqa: E402
from telegram_bot.middleware import UserCheckMiddleware  # noqa: E402


dp.message.middleware(UserCheckMiddleware())
dp.callback_query.middleware(UserCheckMiddleware())


async def set_main_menu(bot: Bot):
    commands = [
        BotCommand(command='getvless', description='Получить VLESS-конфиг'),
        BotCommand(command='configs', description='Мои конфиги'),
        BotCommand(command='help', description='Помощь/Инструкция/Справка'),
    ]
    await bot.set_my_commands(commands)


async def main():
    await set_main_menu(bot)
    dp.include_routers(access_control.router, config_manager.router, admin.router, help.router, start.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
