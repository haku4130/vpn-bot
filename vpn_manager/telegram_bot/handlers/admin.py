from aiogram import Router, types
from asgiref.sync import sync_to_async
from vpn.models.configs import VPNUser

from telegram_bot import bot


router = Router()


@router.callback_query(lambda c: c.data and c.data.startswith('admin_'))
async def admin_approve_reject(cq: types.CallbackQuery):
    action, tg_id = cq.data.split(':')
    user = await sync_to_async(VPNUser.objects.get)(telegram_id=int(tg_id))
    if action == 'admin_approve':
        user.is_active = True
        await sync_to_async(user.save)()
        await cq.message.edit_text(f'✅ Доступ одобрен для {user.full_name} (ID={tg_id})')
        await bot.send_message(tg_id, '✅ Ваш доступ к боту одобрен.')
    else:
        await cq.message.edit_text(f'❌ Доступ отклонён для {user.full_name} (ID={tg_id})')
        await bot.send_message(tg_id, '❌ Ваш запрос на доступ отклонён.')
    await cq.answer()
