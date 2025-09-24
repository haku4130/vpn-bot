import json
import uuid

from django.utils import timezone

from vpn.managers.base_config_manager import BaseConfigManager
from vpn.models.servers import ServerProtocol, VPNServer
from vpn.utils.ssh_utils import SSHClient


class XRayManager(BaseConfigManager):
    def __init__(self, server: VPNServer, ssh: SSHClient | None = None):
        self.server_protocol = server.protocols.get(protocol=ServerProtocol.VLESS)
        super().__init__(server, ssh=ssh)

    def add_client(self, username: str) -> tuple[str, str]:
        client_id = str(uuid.uuid4())
        now = timezone.now()
        creation_date = now.strftime('%a %b %d %H:%M:%S %Y')
        client_name = f'{username}_{now}'

        if self.server_protocol.is_clients_table_supported:
            # Обновляем clientsTable
            self._append_to_table(
                {
                    'clientId': client_id,
                    'userData': {
                        'clientName': client_name,
                        'creationDate': creation_date,
                    },
                },
            )

        # Обновляем основной файл конфигурации
        with open(self.local_conf) as f:
            server = json.load(f)
        server['inbounds'][0]['settings']['clients'].append(
            {
                'id': client_id,
                'email': client_name,
                'flow': 'xtls-rprx-vision',
                'level': 0,
            },
        )
        with open(self.local_conf, 'w') as f:
            json.dump(server, f, indent=4)
        self._save_conf()

        return client_id, client_name

    def remove_client(self, client_id):
        if self.server_protocol.is_clients_table_supported:
            # Обновляем clientsTable
            with open(self.local_table) as f:
                table = json.load(f)
            table = [c for c in table if c['clientId'] != client_id]
            with open(self.local_table, 'w') as f:
                json.dump(table, f, indent=4)
            self._save_table()

        # Обновляем основной файл конфигурации
        self.disable_client(client_id)

    def disable_client(self, client_id):
        with open(self.local_conf) as f:
            server = json.load(f)

        clients = server['inbounds'][0]['settings']['clients']
        server['inbounds'][0]['settings']['clients'] = [c for c in clients if c['id'] != client_id]

        with open(self.local_conf, 'w') as f:
            json.dump(server, f, indent=4)
        self._save_conf()

    def enable_client(self, client_id, client_name):
        # Проверяем, есть ли уже в основном файле конфигурации (может быть включён)
        with open(self.local_conf) as f:
            server = json.load(f)

        existing_ids = {c['id'] for c in server['inbounds'][0]['settings']['clients']}
        if client_id in existing_ids:
            return  # уже включён

        # Добавляем
        server['inbounds'][0]['settings']['clients'].append(
            {
                'id': client_id,
                'email': client_name,
                'flow': 'xtls-rprx-vision',
                'level': 0,
            },
        )

        with open(self.local_conf, 'w') as f:
            json.dump(server, f, indent=4)
        self._save_conf()

    @staticmethod
    def get_vless_url_template():
        return (
            'vless://{client_id}@{server_ip_address}:443?encryption=none&security=reality'
            '&type=tcp&flow=xtls-rprx-vision&fp=chrome&pbk={public_key}'
            '&sni=www.googletagmanager.com&sid=8a48dd5300642057#{client_name}'
        )
