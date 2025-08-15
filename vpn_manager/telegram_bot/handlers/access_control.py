from aiogram import Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from config.env_constants import MAIN_ADMIN_ID
from vpn.models.users import AccessRequest, VPNUser

from telegram_bot import bot


router = Router()


@router.callback_query(lambda cq: cq.data == 'request_access')
async def handle_access_request(cq: types.CallbackQuery):
    tg_id = cq.from_user.id
    username = cq.from_user.username or 'None'
    full_name = cq.from_user.full_name or 'None'

    user, _ = await sync_to_async(VPNUser.objects.get_or_create)(
        telegram_id=tg_id,
        defaults={'username': username, 'full_name': full_name, 'is_active': False},
    )

    _, created = await sync_to_async(AccessRequest.objects.get_or_create)(user=user)

    if created:
        # отправляем админу
        kb = InlineKeyboardBuilder()
        kb.button(text='✅ Одобрить', callback_data=f'admin_approve:{tg_id}')
        kb.button(text='❌ Отклонить', callback_data=f'admin_reject:{tg_id}')
        kb.adjust(2)
        await bot.send_message(
            MAIN_ADMIN_ID,
            f'📥 Новый запрос на доступ от {full_name} (@{username})\nTelegram ID: {tg_id}',
            reply_markup=kb.as_markup(),
        )
        await cq.message.edit_text('✅ Запрос отправлен. Ожидайте одобрения.')
    else:
        await cq.answer('⏳ Запрос уже отправлен ранее.', show_alert=True)
