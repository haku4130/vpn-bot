import json
import logging
import os

from vpn.models.servers import ServerProtocol, VPNServer
from vpn.utils.ssh_utils import (
    SSHClient,
    execute_ssh_command,
    get_file_from_container,
    get_ssh_client,
    put_file_to_container,
)


logger = logging.getLogger(__name__)


class BaseConfigManager:
    clients_table_filename: str = 'clientsTable'

    def __init__(self, server: VPNServer, ssh: SSHClient | None = None, *, should_restart: bool = True):
        self.server = server
        self.server_protocol: ServerProtocol
        self.ssh = ssh or get_ssh_client(self.server)
        self.ssh.sftp_client = self.ssh.open_sftp()
        self.local_conf = f'/tmp/{self.server_protocol.config_filename}'
        self.local_table = f'/tmp/{self.clients_table_filename}.json'
        self._load_files()
        self.should_restart = should_restart

    def _load_files(self):
        if self.server_protocol.volumes_supported:
            self.ssh.sftp_client.get(
                self.server_protocol.config_path + self.server_protocol.config_filename,
                self.local_conf,
            )
            if self.server_protocol.is_clients_table_supported:
                self.ssh.sftp_client.get(
                    self.server_protocol.config_path + self.clients_table_filename,
                    self.local_table,
                )
        else:
            get_file_from_container(
                self.ssh,
                self.server_protocol.container_name,
                self.local_conf,
                self.server_protocol.config_path + self.server_protocol.config_filename,
            )
            if self.server_protocol.is_clients_table_supported:
                get_file_from_container(
                    self.ssh,
                    self.server_protocol.container_name,
                    self.local_table,
                    self.server_protocol.config_path + self.clients_table_filename,
                )

    def _save_conf(self):
        if self.server_protocol.volumes_supported:
            self.ssh.sftp_client.put(
                self.local_conf,
                self.server_protocol.config_path + self.server_protocol.config_filename,
            )
        else:
            put_file_to_container(
                self.ssh,
                self.server_protocol.container_name,
                self.local_conf,
                self.server_protocol.config_path + self.server_protocol.config_filename,
            )

    def _save_table(self):
        if self.server_protocol.volumes_supported:
            self.ssh.sftp_client.put(
                self.local_table,
                self.server_protocol.config_path + self.clients_table_filename,
            )
        else:
            put_file_to_container(
                self.ssh,
                self.server_protocol.container_name,
                self.local_table,
                self.server_protocol.config_path + self.clients_table_filename,
            )

    def _append_to_table(self, entry: dict):
        with open(self.local_table) as f:
            table = json.load(f)
        table.append(entry)
        with open(self.local_table, 'w') as f:
            json.dump(table, f, indent=4)
        self._save_table()

    def close(self):
        self.ssh.sftp_client.close()
        self.ssh.close()
        try:
            os.remove(self.local_conf)
            if self.server_protocol.is_clients_table_supported:
                os.remove(self.local_table)
        except OSError:
            logger.exception('Не удалось удалить временные файлы %s или %s', self.local_conf, self.local_table)

    def restart(self):
        execute_ssh_command(self.ssh, f'sudo docker restart {self.server_protocol.container_name}')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.should_restart:
            self.restart()
        self.close()
