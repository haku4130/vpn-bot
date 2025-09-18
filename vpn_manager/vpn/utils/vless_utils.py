from vpn.managers.vless_manager import XRayManager


def generate_vless_config(client_name: str, server_ip_address: str) -> tuple[str, str]:
    with XRayManager(server_ip_address) as mgr:
        client_id = mgr.add_client(client_name)
        public_key = mgr.get_server_public_key()
        vless_url = mgr.get_vless_url_template().format(
            client_id=client_id,
            server_ip_address=server_ip_address,
            public_key=public_key,
            client_name=client_name,
        )
    return client_id, vless_url


def remove_vless_config(client_id: str, server_ip_address: str):
    with XRayManager(server_ip_address) as mgr:
        mgr.remove_client(client_id)


def get_vless_url_by_id(client_id: str, client_name: str, server_ip_address: str) -> tuple[str, str]:
    with XRayManager(server_ip_address) as mgr:
        if not mgr.check_client_exists(client_id):
            raise ValueError(f'Client with ID {client_id} does not exist.')
        public_key = mgr.get_server_public_key()
        vless_url = mgr.get_vless_url_template().format(
            client_id=client_id,
            server_ip_address=server_ip_address,
            public_key=public_key,
            client_name=client_name,
        )
    return client_id, vless_url
