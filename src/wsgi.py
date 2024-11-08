# استيراد المكتبات المطلوبة
import os
from pathlib import Path
import logging
from typing import Dict, Any

from main import app
from utils.log import get_logger
from werkzeug.middleware.proxy_fix import ProxyFix

logger = get_logger(__name__)

class WSGIConfig:
    """تكوين WSGI"""
    def __init__(self):
        self.environment = self._get_environment()
        self.debug = self.environment == 'development'
        self.root_path = Path(__file__).parent
        self.static_folder = self.root_path / 'static'
        self.template_folder = self.root_path / 'templates'
        
    def _get_environment(self) -> str:
        """تحديد بيئة التشغيل"""
        return os.getenv('FLASK_ENV', 'production')

    def get_wsgi_config(self) -> Dict[str, Any]:
        """جلب إعدادات WSGI"""
        return {
            'bind': f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '5000')}",
            'workers': int(os.getenv('WORKERS', '4')),
            'worker_class': 'sync',
            'threads': int(os.getenv('THREADS', '2')),
            'timeout': int(os.getenv('TIMEOUT', '30')),
            'keepalive': int(os.getenv('KEEPALIVE', '2')),
            'max_requests': int(os.getenv('MAX_REQUESTS', '0')),
            'max_requests_jitter': int(os.getenv('MAX_REQUESTS_JITTER', '0')),
            'graceful_timeout': int(os.getenv('GRACEFUL_TIMEOUT', '30')),
            'log_level': os.getenv('LOG_LEVEL', 'info'),
        }

def create_app():
    """إنشاء وإعداد التطبيق"""
    config = WSGIConfig()
    
    # إضافة middleware باستخدام ProxyFix فقط
    app.wsgi_app = ProxyFix(app.wsgi_app)

    # إعداد التطبيق
    app.debug = True
    app.static_folder = str(config.static_folder)
    app.template_folder = str(config.template_folder)
    
    # إعداد معالجة الأخطاء
    @app.errorhandler(404)
    def not_found_error(error):
        return {'error': 'Not Found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal Server Error: {str(error)}")
        return {'error': 'Internal Server Error'}, 500

    return app

# التطبيق الرئيسي
application = create_app()

if __name__ == '__main__':
    config = WSGIConfig()
    wsgi_config = config.get_wsgi_config()
    
    try:
        # تشغيل مباشر مع وضع التطوير
        application.run(
            host='127.0.0.1',  # تغيير هنا
            port=5000,
            debug=True  # تغيير هنا
        )
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
