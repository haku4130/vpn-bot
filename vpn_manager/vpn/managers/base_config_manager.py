import json
import logging
import os

from vpn.models.servers import VPNServer
from vpn.utils.ssh_utils import execute_ssh_command, get_file_from_container, get_ssh_client, put_file_to_container


logger = logging.getLogger(__name__)


class BaseConfigManager:
    config_filename: str
    clients_table_filename: str = 'clientsTable'
    container_name: str
    config_path: str
    local_key: str = '/tmp/server_pub.key'
    server_public_key: str

    def __init__(self, server: VPNServer, ssh=None):
        self.server = server
        self.ssh = ssh or get_ssh_client(self.server.host)
        self.ssh.sftp_client = self.ssh.open_sftp()
        self.local_conf = f'/tmp/{self.config_filename}'
        self.local_table = f'/tmp/{self.clients_table_filename}.json'
        self._load_files()

    def _load_files(self):
        get_file_from_container(
            self.ssh,
            self.container_name,
            self.config_path + self.config_filename,
            self.local_conf,
        )
        get_file_from_container(
            self.ssh,
            self.container_name,
            self.config_path + self.clients_table_filename,
            self.local_table,
        )

    def _save_conf(self):
        put_file_to_container(
            self.ssh,
            self.container_name,
            self.local_conf,
            self.config_path + self.config_filename,
        )

    def _save_table(self):
        put_file_to_container(
            self.ssh,
            self.container_name,
            self.local_table,
            self.config_path + self.clients_table_filename,
        )

    def _append_to_table(self, entry: dict):
        with open(self.local_table) as f:
            table = json.load(f)
        table.append(entry)
        with open(self.local_table, 'w') as f:
            json.dump(table, f, indent=4)
        self._save_table()

    def get_server_public_key(self):
        get_file_from_container(
            self.ssh,
            self.container_name,
            self.config_path + self.server_public_key,
            self.local_key,
        )
        with open(self.local_key) as f:
            key = f.read().strip()
        os.remove(self.local_key)
        return key

    def check_client_exists(self, client_id):
        with open(self.local_table) as f:
            table = json.load(f)
        return any(c['clientId'] == str(client_id) for c in table)

    def close(self):
        self.ssh.sftp_client.close()
        self.ssh.close()
        try:
            os.remove(self.local_conf)
            os.remove(self.local_table)
        except OSError:
            logger.exception('Не удалось удалить временные файлы %s или %s', self.local_conf, self.local_table)

    def restart(self):
        execute_ssh_command(self.ssh, f'sudo docker restart {self.container_name}')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.restart()
        self.close()
