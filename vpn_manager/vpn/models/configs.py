from collections.abc import Callable
from functools import wraps

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from vpn.managers.amneziawg_manager import WGManager
from vpn.managers.vless_manager import XRayManager
from vpn.models.servers import VPNServer
from vpn.models.users import VPNUser
from vpn.utils.amneziawg_utils import generate_wg_config, get_existing_wg_config, remove_wg_config
from vpn.utils.vless_utils import generate_vless_config, get_vless_url_by_id, remove_vless_config


def handle_config_generation(func):
    @wraps(func)
    def wrapper(self: 'VLESSConfig | AmneziaWGConfig', *args, **kwargs):
        is_new = self._state.adding  # type: ignore
        old_active = None

        if not is_new:
            old = type(self).objects.get(pk=self.pk)
            old_active = old.is_active

        # если создаётся — вызываем специфичный для класса генератор
        if is_new:
            self._handle_config_generation()

        self.full_clean()
        func(self, *args, **kwargs)

        # если объект уже был, и поменяли is_active — синхронизируем сервер
        if not is_new and old_active != self.is_active:
            with type(self)._config_manager() as mgr:  # noqa: SLF001
                if self.is_active:
                    mgr.enable_client(str(self.client_id))
                else:
                    mgr.disable_client(str(self.client_id))

    return wrapper


class BaseVPNConfig(models.Model):
    user: models.ForeignKey[VPNUser] = models.ForeignKey('VPNUser', on_delete=models.CASCADE, related_name='%(class)ss')  # type: ignore[type-arg]
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    expires_at: models.DateTimeField = models.DateTimeField(
        blank=True,
        help_text='Дата окончания действия конфигурации',
    )
    is_active: models.BooleanField = models.BooleanField(default=True)
    server: models.ForeignKey[VPNServer] = models.ForeignKey(  # type: ignore[type-arg]
        VPNServer,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
    )

    _remove_config: Callable
    _config_manager: type[XRayManager | WGManager]

    class Meta:
        abstract = True

    def clean(self):
        if not self.user_id:  # type: ignore
            raise ValidationError({'user': 'Поле "user" обязательно.'})

        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=365)

        # при создании нового конфига убеждаемся, что не превысим лимит
        if not self.pk:
            current = self.user.all_configs_count
            if current >= self.user.available_configs_count and not self.user.is_admin:
                raise ValidationError(
                    f'У пользователя уже {current} конфигов, '
                    f'что достигло его лимита {self.user.available_configs_count}.',
                )

    def _handle_config_generation(self):
        """Шаблонный метод для генерации конфигурации."""
        raise NotImplementedError

    @handle_config_generation
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        type(self)._remove_config(str(self.client_id))  # type: ignore  # noqa: SLF001
        super().delete(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def renew(self):
        self.expires_at = timezone.now() + timezone.timedelta(days=365)
        self.is_active = True
        self.save()


class VLESSConfig(BaseVPNConfig):
    client_id: models.UUIDField = models.UUIDField(blank=True, help_text='Добавляется автоматически')  # UUID для VLESS
    _vless_url: str

    _remove_config = remove_vless_config
    _config_manager = XRayManager

    def _handle_config_generation(self):
        client_id, url = generate_vless_config(f'{self.user.username}_{timezone.now():%d-%m-%Y}')
        self.client_id = client_id
        self._vless_url = url

    @property
    def generated_url(self):
        return self._vless_url

    def get_vless_url(self):
        return get_vless_url_by_id(self.client_id, self.user.username)

    def __str__(self):
        return f'VLESS config for {self.user.username} (Expires: {self.expires_at})'


class AmneziaWGConfig(BaseVPNConfig):
    client_id: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text='Добавляется автоматически',
    )  # PublicKey для AmneziaWG
    private_key: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text='Приватный ключ AmneziaWG, необходимый для восстановления конфигурации',
    )
    allowed_ip: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text='IP-адрес, разрешенный для этого клиента',
    )
    _tmp_filepath: str

    _remove_config = remove_wg_config
    _config_manager = WGManager

    def _handle_config_generation(self):
        pub, priv, _, ip, filepath = generate_wg_config(f'{self.user.username}_{timezone.now():%d-%m-%Y}')
        self.client_id = pub
        self.private_key = priv
        self.allowed_ip = ip
        self._tmp_filepath = filepath

    @property
    def tmp_filepath(self):
        return self._tmp_filepath

    def get_existing_config(self):
        return get_existing_wg_config(
            public_key=self.client_id,
            private_key=self.private_key,
            client_name=self.user.username,
            allowed_ip=self.allowed_ip,
        )

    def __str__(self):
        return f'AmneziaWG config for {self.user.username} (Expires: {self.expires_at})'


MODEL_MAP = {
    'VLESSConfig': VLESSConfig,
    'AmneziaWGConfig': AmneziaWGConfig,
}
