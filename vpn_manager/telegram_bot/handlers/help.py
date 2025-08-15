from aiogram import Router, types
from aiogram.filters import Command


router = Router()


@router.message(Command('help'))
async def help_handler(message: types.Message):
    """Обработчик команды /help для получения справки по боту."""
    help_text = (
        '🤖 *Бот для управления VPN-конфигами*\n\n'
        'Основные команды:\n'
        '/getvless - Получить VLESS-конфиг. Рекомендуемый протокол.\n'
        '/getwg - Получить AmneziaWG-конфиг. Протокол может блокироваться некоторыми провайдерами.\n'
        '/configs - Список ваших конфигов.\n'
        '/help - Показать эту справку.\n\n'
        'ℹ️ *Как пользоваться полученными конфигами*:\n'
        '• *VLESS*: скопируйте полученный URL (начинается с `vless://`) '
        'и вставьте его в приложение **v2raytun** (или любой другой клиент VLESS).\n'
        '• *AmneziaWG*: сохраните полученный `.conf`-файл и откройте его '
        'в мобильном приложении **AmneziaWG** через «Import».\n\n'
        '❓ *По всем вопросам и проблемам пишите:* @haku4130'
    )
    await message.answer(help_text, parse_mode='Markdown')
