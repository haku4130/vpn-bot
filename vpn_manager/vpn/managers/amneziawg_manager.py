import json

from django.utils import timezone
from wgconfig import WGConfig  # type: ignore[import-untyped]
from wireguard_tools import WireguardKey

from vpn.managers.base_config_manager import BaseConfigManager
from vpn.models.servers import ServerProtocol, VPNServer
from vpn.utils.ssh_utils import SSHClient


class WGManager(BaseConfigManager):
    def __init__(self, server: VPNServer, ssh: SSHClient | None = None):
        self.server_protocol = server.protocols.get(protocol=ServerProtocol.AMNEZIAWG)
        super().__init__(server, ssh)
        self.cfg = WGConfig(self.local_conf)
        self.cfg.read_file()

    def generate_wg_keys(self):
        priv = WireguardKey.generate()
        return str(priv), str(priv.public_key()), self.server_protocol.wg_preshared_key

    def get_next_ip(self):
        used = (
            [p.get('AllowedIPs', '') for p in self.cfg.peers.values() if p.get('AllowedIPs', '').startswith('10.8.1.')]
            if self.cfg.peers
            else []
        )
        last = max(int(ip.split('/')[0].split('.')[-1]) for ip in used) + 1
        return f'10.8.1.{last}/32'

    def add_peer(self, public_key, preshared_key, allowed_ip, client_id, client_name):
        if self.server_protocol.is_clients_table_supported:
            # Обновляем clientsTable
            self._append_to_table(
                {
                    'clientId': client_id,
                    'userData': {
                        'allowedIps': allowed_ip,
                        'clientName': client_name,
                        'creationDate': timezone.now().strftime('%a %b %d %H:%M:%S %Y'),
                        'dataReceived': '0 B',
                        'dataSent': '0 B',
                        'latestHandshake': '',
                    },
                },
            )

        # Обновляем основной файл конфигурации
        self.cfg.add_peer(public_key)
        self.cfg.add_attr(public_key, 'PresharedKey', preshared_key)
        self.cfg.add_attr(public_key, 'AllowedIPs', allowed_ip)
        self.cfg.write_file()
        self._save_conf()

    def remove_peer(self, public_key):
        if self.server_protocol.is_clients_table_supported:
            # Обновляем clientsTable
            with open(self.local_table) as f:
                table = json.load(f)
            table = [c for c in table if c['clientId'] != public_key]
            with open(self.local_table, 'w') as f:
                json.dump(table, f, indent=4)
            self._save_table()

        # Обновляем основной файл конфигурации
        self.cfg.del_peer(public_key)
        self.cfg.write_file()
        self._save_conf()

    def enable_client(self, public_key, _):
        self.cfg.enable_peer(public_key)
        self.cfg.write_file()
        self._save_conf()

    def disable_client(self, public_key):
        self.cfg.disable_peer(public_key)
        self.cfg.write_file()
        self._save_conf()

    def generate_client_conf_file(self, client_name, private_key, preshared_key, allowed_ip):
        new_conf = WGConfig(f'/tmp/wg_{client_name}.conf')
        server_cfg = self.cfg.get_interface()

        # 'None' означает добавление в секцию [Interface]
        new_conf.add_attr(None, 'Address', allowed_ip)
        new_conf.add_attr(None, 'DNS', '1.1.1.1, 1.0.0.1')
        new_conf.add_attr(None, 'PrivateKey', private_key)
        for k in ('Jc', 'Jmin', 'Jmax', 'S1', 'S2', 'H1', 'H2', 'H3', 'H4'):
            new_conf.add_attr(None, k, server_cfg.get(k, ''))

        server_public_key = self.server_protocol.public_key
        new_conf.add_peer(server_public_key)
        new_conf.add_attr(server_public_key, 'PresharedKey', preshared_key)
        new_conf.add_attr(server_public_key, 'AllowedIPs', '0.0.0.0/0,::/0')
        new_conf.add_attr(server_public_key, 'Endpoint', f'{self.server.host}:46446')
        new_conf.add_attr(server_public_key, 'PersistentKeepalive', '25')

        new_conf.write_file()
        return new_conf.filename

    def get_allowed_ip_from_client_id(self, client_id):
        with open(self.local_table) as f:
            table = json.load(f)
        for entry in table:
            if entry['clientId'] == client_id:
                return entry['userData']['allowedIps']
        raise ValueError(f'Client with ID {client_id} does not exist.')
