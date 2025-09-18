from django.contrib import admin
from django.utils.html import format_html

from .models.configs import AmneziaWGConfig, VLESSConfig, VPNUser
from .models.servers import ServerProtocol, VPNServer


class VLESSConfigInline(admin.TabularInline):
    model = VLESSConfig
    extra = 0  # не показывать пустые формы
    fields = ('client_id', 'expires_at', 'is_active')
    readonly_fields = ('client_id',)


class AmneziaWGConfigInline(admin.TabularInline):
    model = AmneziaWGConfig
    extra = 0
    fields = ('client_id', 'expires_at', 'is_active')
    readonly_fields = ('client_id',)


class ServerProtocolInline(admin.TabularInline):
    model = ServerProtocol
    extra = 0


# == Регистрация моделей в админке ==
@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'formatted_username',
        'telegram_id',
        'is_active',
        'available_configs_count',
        'created_at',
        'is_admin',
    )
    search_fields = ('telegram_id', 'username')
    list_filter = ('is_active',)
    inlines = (VLESSConfigInline, AmneziaWGConfigInline)

    @admin.display(description='Username')
    def formatted_username(self, obj):
        if obj.username:
            return format_html(
                '<a href="https://t.me/{}" target="_blank" style="text-decoration: underline;">@{}</a>',
                obj.username,
                obj.username,
            )
        return '-'


@admin.register(VLESSConfig)
class VLESSConfigAdmin(admin.ModelAdmin):
    list_display = ('client_id', 'user', 'expires_at', 'is_active', 'server')
    readonly_fields = ('user', 'client_id', 'server')
    list_filter = ('is_active', 'expires_at')
    search_fields = ('user__username', 'user__telegram_id', 'client_id')
    creation_fields = ('user', 'expires_at', 'is_active')

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj else ()

    def get_fields(self, request, obj=None):
        if obj:
            return self.list_display
        return self.creation_fields


@admin.register(AmneziaWGConfig)
class AmneziaWGConfigAdmin(admin.ModelAdmin):
    list_display = ('short_client_id', 'user', 'expires_at', 'allowed_ip', 'is_active', 'server')
    readonly_fields = ('user', 'private_key', 'client_id', 'allowed_ip', 'server')
    list_filter = ('is_active', 'expires_at')
    search_fields = ('user__username', 'user__telegram_id', 'client_id')
    creation_fields = ('user', 'expires_at', 'is_active')

    @admin.display(description='Client ID')
    def short_client_id(self, obj):
        return obj.client_id[:12] + '…' if obj.client_id else ''

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj else ()

    def get_fields(self, request, obj=None):
        if obj:
            return ('user', 'client_id', 'private_key', 'allowed_ip', 'expires_at', 'is_active', 'server')
        return self.creation_fields


@admin.register(VPNServer)
class VPNServerAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'host',
        'ssh_port',
        'ssh_user',
        'list_protocols',
        'max_configs',
        'issued_configs',
        'is_active',
        'created_at',
    )
    inlines = (ServerProtocolInline,)

    @admin.display(description='Protocols')
    def list_protocols(self, obj):
        return ', '.join(p.protocol for p in obj.protocols.all())


# == Настройки админки ==
admin.site.site_header = 'VPN Manager Admin'
admin.site.site_title = 'VPN Manager Admin'
admin.site.index_title = 'VPN Manager Admin'
