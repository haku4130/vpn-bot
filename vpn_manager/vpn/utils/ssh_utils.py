import paramiko
from config.env_constants import SSH_HOST, SSH_KEY_PATH, SSH_USER
from paramiko.ssh_exception import SSHException


class SSHClient(paramiko.SSHClient):
    sftp_client: paramiko.SFTPClient


def get_ssh_client():
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, username=SSH_USER, key_filename=SSH_KEY_PATH)
    return ssh


def execute_ssh_command(ssh_client, command):
    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode()
    error = stderr.read().decode()
    if error:
        raise SSHException(f'Ошибка выполнения команды {command}: {error}')
    return output


def get_file_from_container(ssh_client, container, container_path, local_path):
    temp_server_path = f"/tmp/{local_path.split('/')[-1]}"
    command = f'sudo docker cp {container}:{container_path} {temp_server_path}'
    execute_ssh_command(ssh_client, command)
    ssh_client.sftp_client.get(temp_server_path, local_path)
    execute_ssh_command(ssh_client, f'sudo shred -u {temp_server_path}')


def put_file_to_container(ssh_client, container, local_path, container_path):
    temp_server_path = f"/tmp/{local_path.split('/')[-1]}"
    ssh_client.sftp_client.put(local_path, temp_server_path)
    command = f'sudo docker cp {temp_server_path} {container}:{container_path}'
    execute_ssh_command(ssh_client, command)
    execute_ssh_command(ssh_client, f'sudo shred -u {temp_server_path}')
