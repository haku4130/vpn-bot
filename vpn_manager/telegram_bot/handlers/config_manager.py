import logging
import os
from datetime import datetime

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from vpn.models.configs import MODEL_MAP, AmneziaWGConfig, VLESSConfig, VPNUser

from telegram_bot import bot
from telegram_bot.helpers.config_generator import generate_vless_config, generate_wg_config


router = Router()
logger = logging.getLogger(__name__)


@router.message(Command('getvless'))
async def get_vless_handler(message: types.Message, user: VPNUser, expires: datetime | None = None):
    """Обработчик команды /getvless для получения VLESS-конфига."""

    progress_message = await message.answer('🔄 Генерируем VLESS-конфиг...')

    try:
        text, _ = await generate_vless_config(user, expires)
        await progress_message.edit_text(text, parse_mode='Markdown')
    except ValueError as e:
        await progress_message.edit_text(str(e))


# XXX Отказываемся от поддержки AmneziaWG,
# так как протокол теперь полностью блокируется
# @router.message(Command('getwg'))
async def get_wg_handler(message: types.Message, user: VPNUser, expires: datetime | None = None):
    """Обработчик команды /getwg для получения AmneziaWG-конфига."""

    progress_message = await message.answer('🔄 Генерируем AmneziaWG-конфиг...')

    try:
        text, wg_config = await generate_wg_config(user, expires)
        await progress_message.delete()
        await bot.send_document(
            chat_id=message.from_user.id,
            document=FSInputFile(wg_config.tmp_filepath),
            caption=text,
        )
        try:
            os.remove(wg_config.tmp_filepath)
        except OSError:
            logger.exception('Не удалось удалить временный файл %s', wg_config.tmp_filepath)
    except ValueError as e:
        await progress_message.edit_text(str(e))


@router.message(Command('configs'))
async def list_configs(message: types.Message, user: VPNUser):
    configs = await sync_to_async(lambda: user.configs)()
    if not configs:
        return await message.answer('У вас пока нет конфигов.')

    # Для каждого конфига выводим отдельное сообщение с кнопкой
    for cfg in configs:
        kb = InlineKeyboardBuilder()
        if isinstance(cfg, AmneziaWGConfig):
            kb.button(text='🔄 Сменить протокол', callback_data=f'change_proto:{cfg.__class__.__name__}:{cfg.id}')
        else:
            kb.button(text='⏱ Продлить', callback_data=f'extend_config:{cfg.id}')
        # XXX Отключено до реализации отдельной модели для покупки,
        # чтобы при удалении и создании дата истечения не менялась
        # kb.button(text='❌ Удалить', callback_data=f'delete_config:{cfg.__class__.__name__}:{cfg.id}')  # noqa: ERA001
        kb.button(text='📋 Получить конфиг', callback_data=f'get_config:{cfg.__class__.__name__}:{cfg.id}')
        kb.adjust(1, 2)

        # кратко описываем конфиг
        if isinstance(cfg, AmneziaWGConfig):
            text = (
                f'🔐 *AmneziaWG*\n'
                f'ID: `{cfg.client_id}`\n'
                f'Истекает: {cfg.expires_at:%d-%m-%Y}\n'
                f'Статус: {"✅ Активен" if cfg.is_active else "❌ Неактивен"}'
                f'**\n\n*Важно!*\nAmneziaWG блокируется в России, измените '
                f'свои AmneziaWG протоколы на VLESS, нажав кнопку под конфигом.'
            )
        elif isinstance(cfg, VLESSConfig):
            text = (
                f'🔑 *VLESS*\n'
                f'ID: `{cfg.client_id}`\n'
                f'Истекает: {cfg.expires_at:%d-%m-%Y}\n'
                f'Статус: {"✅ Активен" if cfg.is_active else "❌ Неактивен"}'
            )

        await message.answer(text, parse_mode='Markdown', reply_markup=kb.as_markup())

    return None


@router.callback_query(lambda c: c.data and c.data.startswith('change_proto:'))
async def change_protocol_cb(cq: types.CallbackQuery, user: VPNUser):
    _, model_name, config_id = cq.data.split(':')

    # Создаем клавиатуру для подтверждения
    kb = InlineKeyboardBuilder()
    kb.button(text='✅ Да, поменять', callback_data=f'confirm_change:{model_name}:{config_id}')
    kb.button(text='❌ Нет, оставить', callback_data='cancel_change')
    kb.adjust(2)

    await cq.message.edit_text(
        '⚠️ *Внимание!*\n\n'
        'При смене протокола текущий конфиг будет удалён и создан новый.\n'
        'Старый конфиг перестанет работать.\n\n'
        'Вы уверены, что хотите продолжить?',
        parse_mode='Markdown',
        reply_markup=kb.as_markup(),
    )


@router.callback_query(lambda c: c.data and c.data.startswith('confirm_change:'))
async def confirm_change_protocol_cb(cq: types.CallbackQuery, user: VPNUser):
    _, model_name, config_id = cq.data.split(':')
    Model = MODEL_MAP[model_name]  # noqa: N806
    config = await sync_to_async(Model.objects.get)(pk=config_id, user=user)

    expires = config.expires_at

    try:
        await cq.message.edit_text('🔄 Удаляем старый конфиг...')
        await config.adelete()
    except Model.DoesNotExist:
        await cq.answer('❌ Конфиг не найден', show_alert=True)
        return
    except Exception:
        logger.exception('Ошибка при удалении конфига')
        await cq.answer('❌ Ошибка при удалении конфига', show_alert=True)
        return

    await cq.message.edit_text('🔄 Генерируем новый конфиг...')

    try:
        if model_name == 'AmneziaWGConfig':
            text, _ = await generate_vless_config(user, expires)
            await cq.message.edit_text(text, parse_mode='Markdown')
        else:
            text, wg_config = await generate_wg_config(user, expires)
            await cq.message.edit_text('✅ Конфиг успешно создан')
            await bot.send_document(
                chat_id=cq.from_user.id,
                document=FSInputFile(wg_config.tmp_filepath),
                caption=text,
            )
            try:
                os.remove(wg_config.tmp_filepath)
            except OSError:
                logger.exception('Не удалось удалить временный файл %s', wg_config.tmp_filepath)
    except ValueError as e:
        await cq.message.edit_text(str(e))


@router.callback_query(lambda c: c.data == 'cancel_change')
async def cancel_change_protocol_cb(cq: types.CallbackQuery):
    await cq.message.edit_text('❌ Смена протокола отменена')


# XXX Отключено до реализации отдельной модели для покупки,
# чтобы при удалении и создании дата истечения не менялась
# @router.callback_query(lambda c: c.data and c.data.startswith('delete_config:'))
async def delete_config_cb(cq: types.CallbackQuery, user: VPNUser):
    _, model_name, config_id = cq.data.split(':')
    Model = MODEL_MAP[model_name]  # noqa: N806
    config = await sync_to_async(Model.objects.get)(pk=config_id, user=user)

    try:
        await cq.message.edit_text('🔄 Удаляем старый конфиг...')
        await config.adelete()
        await cq.message.edit_text('✅ Конфиг успешно удален')
    except Model.DoesNotExist:
        await cq.answer('❌ Конфиг не найден', show_alert=True)
    except Exception:
        logger.exception('Ошибка при удалении конфига')
        await cq.answer('❌ Ошибка при удалении конфига', show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith('get_config:'))
async def get_config_cb(cq: types.CallbackQuery, user: VPNUser):
    _, model_name, config_id = cq.data.split(':')
    Model = MODEL_MAP[model_name]  # noqa: N806
    config = await sync_to_async(Model.objects.get)(pk=config_id, user=user)

    try:
        await cq.message.edit_text('🔄 Получаем информацию о конфиге...')
        if isinstance(config, VLESSConfig):
            _, vless_url = await sync_to_async(config.get_vless_url)()
            await cq.message.answer(f'✅ Ваш VLESS-конфиг:\n```\n{vless_url}\n```', parse_mode='Markdown')
        elif isinstance(config, AmneziaWGConfig):
            tmp_filepath = await sync_to_async(config.get_existing_config)()
            await cq.message.delete()
            await bot.send_document(
                chat_id=cq.from_user.id,
                document=FSInputFile(tmp_filepath),
                caption='✅ Ваш AmneziaWG-конфиг',
            )
            try:
                os.remove(tmp_filepath)
            except OSError:
                logger.exception('Не удалось удалить временный файл %s', tmp_filepath)

        await cq.answer()
    except Exception:
        logger.exception('Ошибка при получении конфига')
        await cq.answer('❌ Ошибка при получении конфига', show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith('extend_config:'))
async def extend_config_cb(cq: types.CallbackQuery):
    await cq.answer('🔄 Эта функция пока в разработке', show_alert=True)
