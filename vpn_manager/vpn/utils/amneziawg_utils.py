from config.env_constants import WG_PRESHARED_KEY

from vpn.managers.amneziawg_manager import WGManager
from vpn.models.servers import VPNServer


def generate_wg_config(client_name, server: VPNServer):
    with WGManager(server) as mgr:
        priv, pub, psk = mgr.generate_wg_keys()
        ip = mgr.get_next_ip()
        mgr.add_peer(pub, psk, ip, pub, client_name)
        conf_file = mgr.generate_client_conf_file(client_name, priv, psk, ip)

    return pub, priv, psk, ip, conf_file


def remove_wg_config(client_id, server: VPNServer):
    with WGManager(server) as mgr:
        mgr.remove_peer(client_id)


def enable_client(client_id, server: VPNServer):
    with WGManager(server) as mgr:
        mgr.enable_client(client_id, None)


def disable_client(client_id, server: VPNServer):
    with WGManager(server) as mgr:
        mgr.disable_client(client_id)


def get_existing_wg_config(public_key, private_key, client_name, server: VPNServer, allowed_ip=None):
    with WGManager(server) as mgr:
        if not allowed_ip:
            allowed_ip = mgr.get_allowed_ip_from_client_id(public_key)
        path = mgr.generate_client_conf_file(client_name, private_key, WG_PRESHARED_KEY, allowed_ip)
    return path
