from aiogram import Bot, Dispatcher
from config.env_constants import TELEGRAM_BOT_TOKEN


dp = Dispatcher()
bot = Bot(token=TELEGRAM_BOT_TOKEN)
