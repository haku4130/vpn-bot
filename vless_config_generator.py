import json
import os
import uuid
from datetime import datetime

import paramiko


SSH_HOST = str(os.getenv('SSH_HOST'))
SSH_USER = str(os.getenv('SSH_USER'))
SSH_KEY_PATH = str(os.getenv('SSH_KEY_PATH'))
DOCKER_CONTAINER = str(os.getenv('DOCKER_CONTAINER'))
CONFIG_PATH = str(os.getenv('CONFIG_PATH'))


def get_ssh_client():
    """Создание SSH-клиента и подключение к серверу"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, username=SSH_USER, key_filename=SSH_KEY_PATH)
    return ssh


def execute_ssh_command(ssh_client, command):
    """Выполнение SSH-команды и возврат результата"""
    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode()
    error = stderr.read().decode()
    if error:
        raise Exception(f'Ошибка выполнения команды {command}: {error}')
    return output


def get_file_from_container(ssh_client, container_path, local_path):
    """Извлечение файла из контейнера на локальную машину"""
    # Копируем файл из контейнера во временную директорию на сервере
    temp_server_path = f"/tmp/{local_path.split('/')[-1]}"
    command = f'sudo docker cp {DOCKER_CONTAINER}:{container_path} {temp_server_path}'
    execute_ssh_command(ssh_client, command)

    # Скачиваем файл с сервера на локальную машину
    sftp = ssh_client.open_sftp()
    sftp.get(temp_server_path, local_path)
    sftp.close()

    # Удаляем временный файл на сервере
    execute_ssh_command(ssh_client, f'sudo shred -u {temp_server_path}')


def put_file_to_container(ssh_client, local_path, container_path):
    """Загрузка файла с локальной машины в контейнер"""
    # Загружаем файл на сервер во временную директорию
    temp_server_path = f"/tmp/{local_path.split('/')[-1]}"
    sftp = ssh_client.open_sftp()
    sftp.put(local_path, temp_server_path)
    sftp.close()

    # Копируем файл из временной директории сервера в контейнер
    command = f'sudo docker cp {temp_server_path} {DOCKER_CONTAINER}:{container_path}'
    execute_ssh_command(ssh_client, command)

    # Удаляем временный файл на сервере
    execute_ssh_command(ssh_client, f'sudo shred -u {temp_server_path}')


def update_clients_table(ssh_client, client_id, client_name, creation_date):
    """Обновление clientsTable в контейнере с новым клиентом"""
    local_clients_table = '/tmp/clientsTable.json'
    get_file_from_container(ssh_client, f'{CONFIG_PATH}clientsTable', local_clients_table)

    with open(local_clients_table, 'r') as f:
        clients_table = json.load(f)
    new_client = {
        'clientId': client_id,
        'userData': {
            'clientName': client_name,
            'creationDate': creation_date,
        },
    }
    clients_table.append(new_client)
    with open(local_clients_table, 'w') as f:
        json.dump(clients_table, f, indent=4)

    put_file_to_container(ssh_client, local_clients_table, f'{CONFIG_PATH}clientsTable')
    os.remove(local_clients_table)


def update_server_json(ssh_client, client_id):
    """Обновление server.json с новым клиентом"""
    local_server_json = '/tmp/server.json'
    get_file_from_container(ssh_client, f'{CONFIG_PATH}server.json', local_server_json)

    with open(local_server_json, 'r') as f:
        server_config = json.load(f)

    new_client_entry = {
        'flow': 'xtls-rprx-vision',
        'id': client_id,
    }

    server_config['inbounds'][0]['settings']['clients'].append(new_client_entry)
    with open(local_server_json, 'w') as f:
        json.dump(server_config, f, indent=4)

    put_file_to_container(ssh_client, local_server_json, f'{CONFIG_PATH}server.json')
    os.remove(local_server_json)


def get_public_key(ssh_client):
    """Получение публичного ключа из контейнера"""
    local_pbkey = '/tmp/xray_public.key'
    get_file_from_container(ssh_client, f'{CONFIG_PATH}xray_public.key', local_pbkey)

    with open(local_pbkey, 'r') as f:
        public_key = f.read().strip()

    os.remove(local_pbkey)
    return public_key


def build_vless_url(client_id, public_key, client_name):
    """Построение VLESS URL для клиента"""
    return (
        f'vless://{client_id}@{SSH_HOST}:443?encryption=none&security=reality'
        f'&type=tcp&flow=xtls-rprx-vision&fp=chrome&pbk={public_key}'
        f'&sni=www.googletagmanager.com&sid=8a48dd5300642057#{client_name}'
    )


def get_config(client_name):
    """Генерация нового VLESS URL для клиента с заданным именем"""
    # Генерация UUID и данных пользователя
    client_id = str(uuid.uuid4())
    creation_date = datetime.now().strftime('%a %b %d %H:%M:%S %Y')

    # Подключение к SSH
    ssh = get_ssh_client()

    # Обновление clientsTable и server.json
    update_clients_table(ssh, client_id, client_name, creation_date)
    update_server_json(ssh, client_id)

    # Перезапуск контейнера
    execute_ssh_command(ssh, f'sudo docker restart {DOCKER_CONTAINER}')

    public_key = get_public_key(ssh)

    # Формирование VLESS URL
    vless_url = build_vless_url(client_id, public_key, client_name)

    ssh.close()

    return vless_url
