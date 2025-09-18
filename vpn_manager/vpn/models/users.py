from itertools import chain

from django.db import models
from django.utils import timezone


class VPNUser(models.Model):
    telegram_id: models.BigIntegerField = models.BigIntegerField(unique=True, help_text='Числовой Telegram user ID')
    username: models.CharField = models.CharField(max_length=255, help_text='Telegram-ник с @', null=True, blank=True)
    full_name: models.CharField = models.CharField(max_length=255, help_text='Человекочитаемое имя пользователя')
    is_active: models.BooleanField = models.BooleanField(default=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    available_configs_count: models.PositiveIntegerField = models.PositiveIntegerField(default=0)
    is_admin: models.BooleanField = models.BooleanField(
        default=False,
        help_text='Для админа нет ограничения на количество конфигов',
    )

    def clean(self):
        if self.username:
            self.username = self.username.lstrip('@')

    def save(self, *args, **kwargs):
        if self.pk:  # если это существующий пользователь
            old_instance = type(self).objects.get(pk=self.pk)
            is_active_changed = old_instance.is_active != self.is_active

            # сначала сохраняем самого пользователя
            super().save(*args, **kwargs)

            # если пользователь деактивирован, то деактивируем все его конфиги
            if is_active_changed and not self.is_active:
                for config in self.configs:
                    config.is_active = False
                    config.save()
        else:
            # для нового пользователя просто сохраняем
            super().save(*args, **kwargs)

    @property
    def configs(self):
        """Возвращает все конфиги пользователя (VLESS + AmneziaWG)."""
        return list(
            chain(
                self.vlessconfigs.all(),  # type: ignore
                self.amneziawgconfigs.all(),  # type: ignore
            ),
        )

    def total_configs(self, *, include_inactive: bool = False) -> int:
        """Возвращает общее число configs (VLESS + AmneziaWG) для пользователя.

        Если include_inactive=False — считает только is_active=True.
        """

        kwargs = {} if include_inactive else {'is_active': True}
        vless_count = self.vlessconfigs.filter(**kwargs).count()  # type: ignore
        wg_count = self.amneziawgconfigs.filter(**kwargs).count()  # type: ignore
        return vless_count + wg_count

    @property
    def active_configs_count(self) -> int:
        """Короткий доступ к числу активных конфигов."""
        return self.total_configs(include_inactive=False)

    @property
    def all_configs_count(self) -> int:
        """Короткий доступ к числу всех (даже неактивных)."""
        return self.total_configs(include_inactive=True)

    def __str__(self):
        username_part = f'@{self.username}' if self.username else ''
        return f'{self.full_name} {username_part} ({self.telegram_id})'


class AccessRequest(models.Model):
    user: models.OneToOneField[VPNUser] = models.OneToOneField('VPNUser', on_delete=models.DO_NOTHING)  # type: ignore[type-arg]
    requested_at: models.DateTimeField = models.DateTimeField(default=timezone.now)
    is_approved: models.BooleanField = models.BooleanField(default=False)
    processed_at: models.DateTimeField = models.DateTimeField(blank=True, null=True)
    comment: models.TextField = models.TextField(blank=True, help_text='Комментарий администратора')

    def __str__(self):
        status = '✅' if self.is_approved else '⏳'
        return f'{status} {self.user.full_name or self.user.username or self.user.telegram_id}'
