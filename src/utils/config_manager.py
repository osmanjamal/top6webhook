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

    # 1. وظائف إدارة الملفات
    def _ensure_config_exists(self):
        """إنشاء ملفات التكوين إذا لم تكن موجودة"""
        os.makedirs(self.config_dir, exist_ok=True)
        
        if not os.path.exists(self.config_file):
            self.save_config(self._get_default_config())
        
        if not os.path.exists(self.credentials_file):
            self.save_credentials(self._get_default_credentials())

    def _get_default_config(self) -> Dict[str, Any]:
        """إرجاع الإعدادات الافتراضية"""
        return {
            "server": self._get_default_server_config(),
            "security": self._get_default_security_config(),
            "binance": self._get_default_binance_config(),
            "trade_settings": self._get_default_trade_config(),
            "notifications": self._get_default_notification_config(),
            "logging": self._get_default_logging_config(),
            "webhook": self._get_default_webhook_config()
        }

    def _get_default_credentials(self) -> Dict[str, Any]:
        """إرجاع بيانات الاعتماد الافتراضية"""
        return {
            "binance_futures": {
                "api_key": "",
                "api_secret": "",
                "testnet": True,
                "allowed_ips": []
            }
        }

    # 2. وظائف القراءة والكتابة الأساسية
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

    # 3. وظائف الحصول على الإعدادات المحددة
    def get_trading_config(self) -> dict:
        """الحصول على إعدادات التداول"""
        return self.load_config().get('trade_settings', {})

    def get_server_config(self) -> dict:
        """الحصول على إعدادات الخادم"""
        return self.load_config().get('server', {})

    def get_binance_config(self) -> dict:
        """الحصول على إعدادات Binance"""
        return self.load_config().get('binance', {})

    def get_notification_config(self) -> dict:
        """الحصول على إعدادات الإشعارات"""
        return self.load_config().get('notifications', {})

    def get_webhook_config(self) -> dict:
        """الحصول على إعدادات Webhook"""
        return self.load_config().get('webhook', {})

    # 4. وظائف تحديث الإعدادات
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

    def update_security_config(self, new_settings: dict) -> bool:
        """تحديث إعدادات الأمان"""
        try:
            config = self.load_config()
            if 'security' not in config:
                config['security'] = {}
            config['security'].update(new_settings)
            return self.save_config(config)
        except Exception as e:
            logger.error(f"Error updating security config: {str(e)}")
            return False

    # 5. وظائف الأمان
    def is_ip_allowed(self, ip: str) -> bool:
        """التحقق من أن عنوان IP مسموح به"""
        try:
            config = self.load_config()
            allowed_ips = config.get('security', {}).get('allowed_ips', [])
            return ip in allowed_ips or not allowed_ips
        except Exception as e:
            logger.error(f"Error checking IP: {str(e)}")
            return False

    def clear_credentials(self) -> None:
        """مسح بيانات الاعتماد"""
        try:
            if os.path.exists(self.credentials_file):
                os.remove(self.credentials_file)
                self._ensure_config_exists()
                logger.info("Credentials cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing credentials: {str(e)}")

    # 6. الإعدادات الافتراضية
    def _get_default_server_config(self) -> dict:
        return {
            "host": "0.0.0.0",
            "port": 5000,
            "debug": False,
            "ssl_enabled": False
        }

    def _get_default_security_config(self) -> dict:
        return {
            "allowed_ips": [],
            "require_auth": True,
            "auth_key": ""
        }

    def _get_default_binance_config(self) -> dict:
        return {
            "default_leverage": 10,
            "max_position_size": 1000,
            "risk_per_trade": 1.0,
            "default_market": "USDT",
            "trade_mode": "FUTURES"
        }

    def _get_default_trade_config(self) -> dict:
        return {
            "max_open_positions": 5,
            "default_stop_loss_percent": 2.0,
            "default_take_profit_percent": 3.0,
            "enable_trailing_stop": False,
            "trailing_stop_percent": 1.0
        }

    def _get_default_notification_config(self) -> dict:
        return {
            "telegram_enabled": False,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "email_enabled": False,
            "email_address": ""
        }

    def _get_default_logging_config(self) -> dict:
        return {
            "level": "INFO",
            "file_path": "logs/app.log",
            "max_file_size": 10485760,
            "backup_count": 5,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }

    def _get_default_webhook_config(self) -> dict:
        return {
            "base_url": "http://localhost:5000",
            "secret_key": "",
            "max_retries": 3,
            "retry_delay": 5
        }