from django.db import models


class VPNServer(models.Model):
    name: models.CharField = models.CharField(max_length=100, unique=True, help_text='Удобное имя сервера')
    host: models.GenericIPAddressField = models.GenericIPAddressField(help_text='IP-адрес сервера')
    ssh_port: models.IntegerField = models.IntegerField(default=22)
    ssh_user: models.CharField = models.CharField(max_length=50, default='root')

    # Лимиты и статистика
    max_configs: models.IntegerField = models.IntegerField(
        default=100,
        help_text='Максимальное число конфигов',
    )
    issued_configs: models.IntegerField = models.IntegerField(
        default=0,
        help_text='Сколько конфигов выдано на данный момент',
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
    def available_slots(self) -> int:
        """Сколько еще можно выдать конфигов."""
        return max(0, self.max_configs - self.issued_configs)

    @property
    def is_overloaded(self) -> bool:
        return self.issued_configs >= self.max_configs


class ServerProtocol(models.Model):
    PROTOCOL_CHOICES = (
        ('vless', 'VLESS'),
        ('amneziawg', 'AmneziaWG'),
    )

    server: models.ForeignKey[VPNServer] = models.ForeignKey(  # type: ignore[type-arg]
        VPNServer,
        on_delete=models.CASCADE,
        related_name='protocols',
    )
    protocol: models.CharField = models.CharField(
        max_length=50,
        choices=PROTOCOL_CHOICES,
        help_text='Какой протокол поддерживает сервер',
    )
    config_path: models.CharField = models.CharField(
        max_length=255,
        help_text='Путь к конфигурационным файлам внутри контейнера',
    )
    container_name: models.CharField = models.CharField(
        max_length=100,
        help_text='Имя docker-контейнера',
    )

    def __str__(self):
        return f'{self.server.name} - {self.protocol}'
