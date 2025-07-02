import asyncio
import vless_config_generator
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
import os


load_dotenv()
TELEGRAM_BOT_TOKEN = str(os.getenv('TELEGRAM_BOT_TOKEN'))

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command('start'))
async def get_config_handler(message: types.Message):
    try:
        client_name = f"user-{message.from_user.username if message.from_user else 'unknown'}"
        # Вызываем синхронную функцию get_config в отдельном потоке
        loop = asyncio.get_running_loop()
        vless_url = await loop.run_in_executor(None, vless_config_generator.get_config, client_name)
        await message.reply(f'Ваш конфиг:\n{vless_url}')
    except Exception as e:
        await message.reply(f'Ошибка: {str(e)}')


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
