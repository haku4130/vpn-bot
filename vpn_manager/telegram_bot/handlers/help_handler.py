from aiogram import Router, types
from aiogram.filters import Command


router = Router()


@router.message(Command('help'))
async def help_handler(message: types.Message):
    """Обработчик команды /help для получения справки по боту."""
    help_text = (
        '🤖 *Бот для управления VPN-конфигами*\n\n'
        'Основные команды:\n'
        '/getconfig - Получить VLESS-конфиг. Самый современный протокол.\n'
        '/configs - Список ваших конфигов.\n'
        '/help - Показать эту справку.\n\n'
        'ℹ️ *Как пользоваться полученными конфигами*:\n'
        '• *На IPhone*: скопируйте полученный конфиг (начинается с `vless://`) '
        'и вставьте его в приложение **v2raytun**.\n'
        'Приложение доступно в App Store.\n'
        '• *На Android и компьютерах*: скопируйте полученный конфиг (начинается с `vless://`) '
        'и вставьте его в приложение **AmneziaVPN**.\n'
        'Приложение доступно в Google Play.\n'
        'Также файлы для установки можно найти в [релизах](https://github.com/amnezia-vpn/amnezia-client/releases), '
        'выбрав нужную версию\n\n'
        '❓ *По всем вопросам и проблемам пишите:* @ww\\_speeder\\_admin'
    )
    await message.answer(help_text, parse_mode='Markdown')
