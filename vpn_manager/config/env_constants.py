import os

from dotenv import load_dotenv


load_dotenv()

SSH_HOST = os.getenv('SSH_HOST', '')
SSH_USER = os.getenv('SSH_USER', '')
SSH_KEY_PATH = os.getenv('SSH_KEY_PATH', '')

WG_PRESHARED_KEY = os.getenv('WG_PRESHARED_KEY', '')

XRAY_CONTAINER = os.getenv('XRAY_CONTAINER', 'amnezia-xray')
WG_CONTAINER = os.getenv('WG_CONTAINER', 'amnezia-awg')

CONFIG_PATH_XRAY = os.getenv('CONFIG_PATH_XRAY', '/opt/amnezia/xray/')
CONFIG_PATH_WG = os.getenv('CONFIG_PATH_WG', '/opt/amnezia/awg/')

MAIN_ADMIN_ID = os.getenv('MAIN_ADMIN_ID', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
