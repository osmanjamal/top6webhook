import os
import json
from pathlib import Path

class SecurityConfig:
    CONFIG_FILE = 'config/credentials.json'    
    @staticmethod
    def get_config_path():
        base_dir = Path(__file__).parent.parent.parent
        return os.path.join(base_dir, SecurityConfig.CONFIG_FILE)

    @staticmethod
    def create_config_if_not_exists():
        config_path = SecurityConfig.get_config_path()
        if not os.path.exists(os.path.dirname(config_path)):
            os.makedirs(os.path.dirname(config_path))
            if not os.path.exists(config_path):
               default_config = {
                    "binance_futures": {
                    "api_key": "",
                    "api_secret": "",
                    "allowed_ips": [],
                    "testnet": False
                }
            }
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)

    @staticmethod
    def load_credentials():
        config_path = SecurityConfig.get_config_path()
        SecurityConfig.create_config_if_not_exists()
        
        with open(config_path, 'r') as f:
            return json.load(f)

    @staticmethod
    def save_credentials(config):
        config_path = SecurityConfig.get_config_path()
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)

    @staticmethod
    def validate_ip(ip_address, allowed_ips):
        if not allowed_ips:
            return False
        return ip_address in allowed_ips