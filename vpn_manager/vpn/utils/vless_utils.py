from vpn.managers.vless_manager import XRayManager
from vpn.models.servers import VPNServer


def generate_vless_config(username: str, server: VPNServer) -> tuple[str, str, str]:
    with XRayManager(server) as mgr:
        client_id, client_name = mgr.add_client(username)
        vless_url = mgr.get_vless_url_template().format(
            client_id=client_id,
            server_ip_address=server.host,
            public_key=mgr.server_protocol.public_key,
            client_name=client_name,
        )
    return client_id, client_name, vless_url


def remove_vless_config(client_id: str, server: VPNServer):
    with XRayManager(server) as mgr:
        mgr.remove_client(client_id)


def get_vless_url_by_id(client_id: str, client_name: str, server: VPNServer) -> tuple[str, str]:
    with XRayManager(server) as mgr:
        vless_url = mgr.get_vless_url_template().format(
            client_id=client_id,
            server_ip_address=server.host,
            public_key=mgr.server_protocol.public_key,
            client_name=client_name,
        )
    return client_id, vless_url
