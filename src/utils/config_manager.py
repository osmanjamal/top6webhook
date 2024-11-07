import os
import json
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self.config_dir = 'config'
        self.config_file = os.path.join(self.config_dir, 'app_config.json')
        self.credentials_file = os.path.join(self.config_dir, 'credentials.json')
        self._ensure_config_exists()
    
    def _ensure_config_exists(self):
        """إنشاء ملفات التكوين إذا لم تكن موجودة"""
        os.makedirs(self.config_dir, exist_ok=True)
        
        # إعدادات التطبيق الافتراضية
        if not os.path.exists(self.config_file):
            default_config = {
                "server": {
                    "host": "0.0.0.0",
                    "port": 5000,
                    "debug": False,
                    "ssl_enabled": False
                },
                "security": {
                    "allowed_ips": [],
                    "require_auth": True,
                    "auth_key": ""
                },
                "binance": {
                    "default_leverage": 10,
                    "max_position_size": 1000,
                    "risk_per_trade": 1.0,
                    "default_market": "USDT",
                    "trade_mode": "FUTURES"
                },
                "trade_settings": {
                    "max_open_positions": 5,
                    "default_stop_loss_percent": 2.0,
                    "default_take_profit_percent": 3.0,
                    "enable_trailing_stop": False,
                    "trailing_stop_percent": 1.0
                },
                "notifications": {
                    "telegram_enabled": False,
                    "telegram_bot_token": "",
                    "telegram_chat_id": "",
                    "email_enabled": False,
                    "email_address": ""
                },
                "logging": {
                    "level": "INFO",
                    "file_path": "logs/app.log",
                    "max_file_size": 10485760,
                    "backup_count": 5,
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "webhook": {
                    "base_url": "http://localhost:5000",
                    "secret_key": "",
                    "max_retries": 3,
                    "retry_delay": 5
                }
            }
            self.save_config(default_config)
        
        # إعدادات API الافتراضية
        if not os.path.exists(self.credentials_file):
            default_creds = {
                "binance_futures": {
                    "api_key": "",
                    "api_secret": "",
                    "testnet": True,
                    "allowed_ips": []
                }
            }
            self.save_credentials(default_creds)
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """حفظ إعدادات التطبيق"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
            return False
    
    def load_config(self) -> Dict[str, Any]:
        """تحميل إعدادات التطبيق"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {}
    
    def save_credentials(self, creds: Dict[str, Any]) -> bool:
        """حفظ بيانات اعتماد API"""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(creds, f, indent=4)
            logger.info("Credentials saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving credentials: {str(e)}")
            return False
    
    def load_credentials(self) -> Dict[str, Any]:
        """تحميل بيانات اعتماد API"""
        try:
            with open(self.credentials_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            return {}

    def get_trading_config(self) -> dict:
        """الحصول على إعدادات التداول"""
        config = self.load_config()
        return config.get('trade_settings', {})

    def get_server_config(self) -> dict:
        """الحصول على إعدادات الخادم"""
        config = self.load_config()
        return config.get('server', {})

    def get_binance_config(self) -> dict:
        """الحصول على إعدادات Binance"""
        config = self.load_config()
        return config.get('binance', {})

    def update_trading_config(self, new_settings: dict) -> bool:
        """تحديث إعدادات التداول"""
        try:
            config = self.load_config()
            if 'trade_settings' not in config:
                config['trade_settings'] = {}
            config['trade_settings'].update(new_settings)
            logger.info(f"Trading settings updated: {new_settings}")
            return self.save_config(config)
        except Exception as e:
            logger.error(f"Error updating trading config: {str(e)}")
            return False

    def update_binance_config(self, new_settings: dict) -> bool:
        """تحديث إعدادات Binance"""
        try:
            config = self.load_config()
            if 'binance' not in config:
                config['binance'] = {}
            config['binance'].update(new_settings)
            logger.info(f"Binance settings updated: {new_settings}")
            return self.save_config(config)
        except Exception as e:
            logger.error(f"Error updating Binance config: {str(e)}")
            return False

    def update_security_config(self, new_settings: dict) -> bool:
        """تحديث إعدادات الأمان"""
        try:
            config = self.load_config()
            if 'security' not in config:
                config['security'] = {}
            config['security'].update(new_settings)
            logger.info(f"Security settings updated: {new_settings}")
            return self.save_config(config)
        except Exception as e:
            logger.error(f"Error updating security config: {str(e)}")
            return False

    def is_ip_allowed(self, ip: str) -> bool:
        """التحقق من أن عنوان IP مسموح به"""
        try:
            config = self.load_config()
            allowed_ips = config.get('security', {}).get('allowed_ips', [])
            return ip in allowed_ips or not allowed_ips  # إذا كانت القائمة فارغة، اسمح بكل العناوين
        except Exception as e:
            logger.error(f"Error checking IP: {str(e)}")
            return False

    def get_notification_config(self) -> dict:
        """الحصول على إعدادات الإشعارات"""
        config = self.load_config()
        return config.get('notifications', {})

    def get_webhook_config(self) -> dict:
        """الحصول على إعدادات Webhook"""
        config = self.load_config()
        return config.get('webhook', {})