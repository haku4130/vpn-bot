import logging
from datetime import datetime

from django.forms import ValidationError
from vpn.models.configs import AmneziaWGConfig, VLESSConfig, VPNUser


logger = logging.getLogger(__name__)


async def generate_vless_config(user: VPNUser, expires: datetime | None = None) -> tuple[str, VLESSConfig]:
    """Создает VLESS конфиг для пользователя."""
    try:
        vless_config = await VLESSConfig.objects.acreate(user=user, expires_at=expires)
    except ValidationError as e:
        raise ValueError(f'🛑 Лимит конфигов ({user.available_configs_count}) исчерпан.') from e
    except Exception as e:
        logger.exception('Ошибка при создании VLESS-конфига')
        raise ValueError('❌ Не удалось создать VLESS-конфиг. Попробуйте позже.') from e
    else:
        return f'✅ Ваш новый VLESS-конфиг:\n```\n{vless_config.generated_url}\n```', vless_config


async def generate_wg_config(user: VPNUser, expires: datetime | None = None) -> tuple[str, AmneziaWGConfig]:
    """Создает WireGuard конфиг для пользователя."""
    try:
        wg_config = await AmneziaWGConfig.objects.acreate(user=user, expires_at=expires)
    except ValidationError as e:
        raise ValueError(f'🛑 Лимит конфигов ({user.available_configs_count}) исчерпан.') from e
    except Exception as e:
        logger.exception('Ошибка при создании AmneziaWG-конфига')
        raise ValueError('❌ Не удалось создать AmneziaWG-конфиг. Попробуйте позже.') from e
    else:
        return '✅ Ваш новый AmneziaWG-конфиг', wg_config
