from config.env_constants import WG_PRESHARED_KEY
from django.utils import timezone

from vpn.managers.amneziawg_manager import WGManager


def generate_wg_config(client_name):
    with WGManager() as mgr:
        priv, pub, psk = mgr.generate_wg_keys()
        ip = mgr.get_next_ip()
        date = timezone.now().strftime('%a %b %d %H:%M:%S %Y')
        mgr.add_peer(pub, psk, ip, pub, client_name, date)
        conf_file = mgr.generate_client_conf_file(client_name, priv, psk, ip)

    return pub, priv, psk, ip, conf_file


def remove_wg_config(client_id):
    with WGManager() as mgr:
        mgr.remove_peer(client_id)


def enable_client(client_id):
    with WGManager() as mgr:
        mgr.enable_client(client_id)


def disable_client(client_id):
    with WGManager() as mgr:
        mgr.disable_client(client_id)


def get_existing_wg_config(public_key, private_key, client_name, allowed_ip=None):
    with WGManager() as mgr:
        if not mgr.check_client_exists(public_key):
            raise ValueError(f'Client with ID {public_key} does not exist.')
        if not allowed_ip:
            allowed_ip = mgr.get_allowed_ip_from_client_id(public_key)
        path = mgr.generate_client_conf_file(client_name, private_key, WG_PRESHARED_KEY, allowed_ip)
    return path
