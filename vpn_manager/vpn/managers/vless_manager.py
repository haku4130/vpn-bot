import json
import uuid

from config.env_constants import CONFIG_PATH_XRAY, XRAY_CONTAINER
from django.utils import timezone

from vpn.managers.base_config_manager import BaseConfigManager


class XRayManager(BaseConfigManager):
    config_filename = 'server.json'
    container_name = XRAY_CONTAINER
    config_path = CONFIG_PATH_XRAY
    server_public_key = 'xray_public.key'

    def add_client(self, client_name):
        client_id = str(uuid.uuid4())
        creation_date = timezone.now().strftime('%a %b %d %H:%M:%S %Y')

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

        # Обновляем server.json
        with open(self.local_conf) as f:
            server = json.load(f)
        server['inbounds'][0]['settings']['clients'].append({'flow': 'xtls-rprx-vision', 'id': client_id})
        with open(self.local_conf, 'w') as f:
            json.dump(server, f, indent=4)
        self._save_conf()

        return client_id

    def remove_client(self, client_id):
        # Обновляем clientsTable
        with open(self.local_table) as f:
            table = json.load(f)
        table = [c for c in table if c['clientId'] != client_id]
        with open(self.local_table, 'w') as f:
            json.dump(table, f, indent=4)
        self._save_table()

        # Обновляем server.json
        self.disable_client(client_id)

    def disable_client(self, client_id):
        with open(self.local_conf) as f:
            server = json.load(f)

        clients = server['inbounds'][0]['settings']['clients']
        server['inbounds'][0]['settings']['clients'] = [c for c in clients if c['id'] != client_id]

        with open(self.local_conf, 'w') as f:
            json.dump(server, f, indent=4)
        self._save_conf()

    def enable_client(self, client_id, *, should_check_client_exists=True):
        # Проверяем, что client_id есть в clientsTable
        if should_check_client_exists and not self.check_client_exists(client_id):
            raise ValueError(f'Client ID {client_id} не найден в clientsTable')

        # Проверяем, есть ли уже в server.json (может быть включён)
        with open(self.local_conf) as f:
            server = json.load(f)

        existing_ids = {c['id'] for c in server['inbounds'][0]['settings']['clients']}
        if client_id in existing_ids:
            return  # уже включён

        # Добавляем
        server['inbounds'][0]['settings']['clients'].append({'flow': 'xtls-rprx-vision', 'id': client_id})

        with open(self.local_conf, 'w') as f:
            json.dump(server, f, indent=4)
        self._save_conf()

    @staticmethod
    def get_vless_url_template():
        return (
            'vless://{{client_id}}@{{server_ip_address}}:443?encryption=none&security=reality'
            '&type=tcp&flow=xtls-rprx-vision&fp=chrome&pbk={{public_key}}'
            '&sni=www.googletagmanager.com&sid=8a48dd5300642057#{{client_name}}'
        )
