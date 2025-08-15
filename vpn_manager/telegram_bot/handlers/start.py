from aiogram import Router, types
from aiogram.filters import Command


router = Router()


@router.message(Command('start'))
async def start_handler(message: types.Message):
    await message.answer(
        '🤖 *Добро пожаловать в бота для управления VPN-конфигами!*\n\n'
        'Используйте кнопку меню, чтобы получить список доступных команд.',
        parse_mode='Markdown',
    )
