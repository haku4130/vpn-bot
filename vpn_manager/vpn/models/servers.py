from django.db import models


class VPNServer(models.Model):
    name: models.CharField = models.CharField(max_length=100, unique=True, help_text='Удобное имя сервера')
    host: models.GenericIPAddressField = models.GenericIPAddressField(help_text='IP-адрес сервера')
    ssh_port: models.IntegerField = models.IntegerField(default=22)
    ssh_user: models.CharField = models.CharField(max_length=50, default='root')
    protocols: models.QuerySet['ServerProtocol']  # Related field defined in ServerProtocol
    location: models.CharField = models.CharField(
        default='Netherlands',
        max_length=50,
        help_text='Географическое расположение сервера',
    )

    # Лимиты и статистика
    max_configs: models.IntegerField = models.IntegerField(
        default=100,
        help_text='Максимальное число конфигов',
    )

    # Текущее состояние
    is_active: models.BooleanField = models.BooleanField(default=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'VPN сервер'
        verbose_name_plural = 'VPN сервера'

    def __str__(self):
        return f'{self.name} ({self.host})'

    @property
    def issued_configs(self) -> int:
        """Сколько конфигов реально выдано для этого сервера."""
        vless_count = self.vlessconfigs.count()  # type: ignore
        wg_count = self.amneziawgconfigs.count()  # type: ignore
        return vless_count + wg_count

    @property
    def available_slots(self) -> int:
        """Сколько еще можно выдать конфигов."""
        return max(0, self.max_configs - self.issued_configs)

    @property
    def is_overloaded(self) -> bool:
        return self.issued_configs >= self.max_configs

    @classmethod
    def get_least_loaded(cls) -> 'VPNServer | None':
        """Вернуть сервер с наибольшим числом свободных слотов."""
        servers = cls.objects.filter(is_active=True)
        if not servers.exists():
            return None
        least_loaded_server = min(servers, key=lambda s: s.issued_configs)
        if least_loaded_server.is_overloaded:
            return None
        return least_loaded_server


class ServerProtocol(models.Model):
    VLESS = 'vless'
    AMNEZIAWG = 'amneziawg'
    PROTOCOL_CHOICES = (
        (VLESS, 'VLESS'),
        (AMNEZIAWG, 'AmneziaWG'),
    )

    server: models.ForeignKey[VPNServer] = models.ForeignKey(  # type: ignore[type-arg]
        VPNServer,
        on_delete=models.CASCADE,
        related_name='protocols',
    )
    protocol: models.CharField = models.CharField(
        max_length=50,
        choices=PROTOCOL_CHOICES,
        default=VLESS,
        help_text='Какой протокол поддерживает сервер',
    )
    config_filename: models.CharField = models.CharField(
        max_length=50,
        default='config.json',
        help_text='Имя конфигурационного файла',
    )
    config_path: models.CharField = models.CharField(
        max_length=255,
        default='/etc/xray/',
        help_text='Путь к конфигурационным файлам',
    )
    container_name: models.CharField = models.CharField(
        max_length=100,
        default='xray-server',
        help_text='Имя docker-контейнера',
    )
    public_key: models.CharField = models.CharField(
        max_length=255,
        help_text='Публичный ключ сервера для конфигураций клиентов',
    )
    wg_preshared_key: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text='(только для AmneziaWG) Общий ключ WireGuard',
    )

    is_clients_table_supported: models.BooleanField = models.BooleanField(
        default=False,
    )
    volumes_supported: models.BooleanField = models.BooleanField(
        default=True,
        help_text='Поддерживает ли сервер монтирование volumes (для AmneziaWG)',
    )

    def __str__(self):
        return f'{self.server.name} - {self.protocol}'
