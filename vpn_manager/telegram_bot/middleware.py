from aiogram import BaseMiddleware
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from vpn.models.users import VPNUser


class UserCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        tg_id = event.from_user.id

        try:
            user = await sync_to_async(VPNUser.objects.get)(telegram_id=tg_id, is_active=True)
            data['user'] = user
            return await handler(event, data)
        except VPNUser.DoesNotExist:
            # Показываем кнопку пользователю
            kb = InlineKeyboardBuilder()
            kb.button(text='🔓 Запросить доступ', callback_data='request_access')
            await event.answer(
                '❌ Вы не зарегистрированы или доступ закрыт.\n\n'
                'Нажмите кнопку ниже, чтобы отправить запрос на доступ.',
                reply_markup=kb.as_markup(),
            )
