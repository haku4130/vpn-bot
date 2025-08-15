import json

from config.env_constants import CONFIG_PATH_WG, SSH_HOST, WG_CONTAINER, WG_PRESHARED_KEY
from wgconfig import WGConfig
from wireguard_tools import WireguardKey

from vpn.managers.base_config_manager import BaseConfigManager


class WGManager(BaseConfigManager):
    config_filename = 'wg0.conf'
    container_name = WG_CONTAINER
    config_path = CONFIG_PATH_WG
    server_public_key = 'wireguard_server_public_key.key'

    def __init__(self, ssh=None):
        super().__init__(ssh)
        self.cfg = WGConfig(self.local_conf)
        self.cfg.read_file()

    def generate_wg_keys(self):
        priv = WireguardKey.generate()
        return str(priv), str(priv.public_key()), WG_PRESHARED_KEY

    def get_next_ip(self):
        used = (
            [p.get('AllowedIPs', '') for p in self.cfg.peers.values() if p.get('AllowedIPs', '').startswith('10.8.1.')]
            if self.cfg.peers
            else []
        )
        last = max(int(ip.split('/')[0].split('.')[-1]) for ip in used) + 1
        return f'10.8.1.{last}/32'

    def add_peer(self, public_key, preshared_key, allowed_ip, client_id, client_name, creation_date):  # noqa: PLR0913
        # Обновляем clientsTable
        self._append_to_table(
            {
                'clientId': client_id,
                'userData': {
                    'allowedIps': allowed_ip,
                    'clientName': client_name,
                    'creationDate': creation_date,
                    'dataReceived': '0 B',
                    'dataSent': '0 B',
                    'latestHandshake': '',
                },
            },
        )

        # Обновляем wg0.conf
        self.cfg.add_peer(public_key)
        self.cfg.add_attr(public_key, 'PresharedKey', preshared_key)
        self.cfg.add_attr(public_key, 'AllowedIPs', allowed_ip)
        self.cfg.write_file()
        self._save_conf()

    def remove_peer(self, public_key):
        # Обновляем clientsTable
        with open(self.local_table) as f:
            table = json.load(f)
        table = [c for c in table if c['clientId'] != public_key]
        with open(self.local_table, 'w') as f:
            json.dump(table, f, indent=4)
        self._save_table()

        # Обновляем wg0.conf
        self.cfg.del_peer(public_key)
        self.cfg.write_file()
        self._save_conf()

    def enable_client(self, public_key):
        self.cfg.enable_peer(public_key)
        self.cfg.write_file()
        self._save_conf()

    def disable_client(self, public_key):
        self.cfg.disable_peer(public_key)
        self.cfg.write_file()
        self._save_conf()

    def generate_client_conf_file(self, client_name, private_key, preshared_key, allowed_ip):
        path = f'/tmp/wg_{client_name}.conf'
        new_conf = WGConfig(path)
        server_cfg = self.cfg.get_interface()

        # 'None' означает добавление в секцию [Interface]
        new_conf.add_attr(None, 'Address', allowed_ip)
        new_conf.add_attr(None, 'DNS', '1.1.1.1, 1.0.0.1')
        new_conf.add_attr(None, 'PrivateKey', private_key)
        for k in ('Jc', 'Jmin', 'Jmax', 'S1', 'S2', 'H1', 'H2', 'H3', 'H4'):
            new_conf.add_attr(None, k, server_cfg.get(k, ''))

        server_public_key = self.get_server_public_key()
        new_conf.add_peer(server_public_key)
        new_conf.add_attr(server_public_key, 'PresharedKey', preshared_key)
        new_conf.add_attr(server_public_key, 'AllowedIPs', '0.0.0.0/0,::/0')
        new_conf.add_attr(server_public_key, 'Endpoint', f'{SSH_HOST}:46446')
        new_conf.add_attr(server_public_key, 'PersistentKeepalive', '25')

        new_conf.write_file()
        return path

    def get_allowed_ip_from_client_id(self, client_id):
        with open(self.local_table) as f:
            table = json.load(f)
        for entry in table:
            if entry['clientId'] == client_id:
                return entry['userData']['allowedIps']
        raise ValueError(f'Client with ID {client_id} does not exist.')
