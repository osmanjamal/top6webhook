import os
from pathlib import Path
import uuid
from typing import Dict, Any
from dataclasses import dataclass
import logging
from enum import Enum

# نمط التصميم Singleton للإعدادات العامة
class Commons:
   _instance = None

   def __new__(cls):
       if cls._instance is None:
           cls._instance = super().__new__(cls)
           cls._instance._initialize()
       return cls._instance

   def _initialize(self):
       """تهيئة الإعدادات الأساسية"""
       # تهيئة المسارات
       self.paths = self._setup_paths()
       
       # تعريف الإصدار
       self.VERSION_NUMBER = '0.5'
       
       # تهيئة المفاتيح
       self.keys = self._setup_keys()
       
       # تهيئة الحدود
       self.limits = self._setup_limits()
       
       # تهيئة إعدادات السجلات
       self.logs = self._setup_logs()

   def _setup_paths(self) -> 'PathConfig':
       """إعداد المسارات"""
       base_dir = Path(__file__).resolve().parent
       return PathConfig(
           base=base_dir,
           components=base_dir / 'components',
           logs=base_dir / 'components' / 'logs',
           config=base_dir / 'config'
       )

   def _setup_keys(self) -> 'KeyConfig':
       """إعداد المفاتيح"""
       key_path = self.paths.base / '.key'
       return KeyConfig(
           path=key_path,
           value=self._get_or_create_key(key_path)
       )

   def _setup_limits(self) -> 'LimitConfig':
       """إعداد الحدود"""
       return LimitConfig(
           log_limit=100,
           request_limit=60,
           cache_limit=1000
       )

   def _setup_logs(self) -> 'LogConfig':
       """إعداد السجلات"""
       log_file = self.paths.logs / 'log.log'
       self._ensure_log_file(log_file)
       return LogConfig(
           file=log_file,
           level=logging.INFO,
           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
       )

   def _get_or_create_key(self, key_path: Path) -> str:
       """إنشاء أو جلب المفتاح الفريد"""
       try:
           if key_path.exists():
               return key_path.read_text().strip()
           else:
               unique_key = str(uuid.uuid4())
               key_path.write_text(unique_key)
               return unique_key
       except Exception as e:
           logging.error(f"Error handling key file: {e}")
           return str(uuid.uuid4())

   def _ensure_log_file(self, log_file: Path) -> None:
       """التأكد من وجود ملف السجلات"""
       try:
           log_file.parent.mkdir(parents=True, exist_ok=True)
           if not log_file.exists():
               log_file.touch()
       except Exception as e:
           logging.error(f"Error creating log file: {e}")

@dataclass
class PathConfig:
   """تكوين المسارات"""
   base: Path
   components: Path
   logs: Path
   config: Path

   def create_dirs(self) -> None:
       """إنشاء جميع المجلدات المطلوبة"""
       for path in [self.components, self.logs, self.config]:
           path.mkdir(parents=True, exist_ok=True)

@dataclass
class KeyConfig:
   """تكوين المفاتيح"""
   path: Path
   value: str

@dataclass
class LimitConfig:
   """تكوين الحدود"""
   log_limit: int
   request_limit: int
   cache_limit: int

@dataclass
class LogConfig:
   """تكوين السجلات"""
   file: Path
   level: int
   format: str

class Environment(Enum):
   """بيئات التشغيل"""
   DEVELOPMENT = "development"
   TESTING = "testing"
   PRODUCTION = "production"

# إنشاء نسخة عامة
commons = Commons()

# ثوابت عامة
VERSION_NUMBER = commons.VERSION_NUMBER
API_VERSION = "v1"
DEFAULT_ENCODING = "utf-8"
SUPPORTED_LANGUAGES = ["en", "ar"]

# تصدير المتغيرات المطلوبة بشكل مباشر
BASE_DIR = commons.paths.base
LOG_LOCATION = commons.logs.file
LOG_LIMIT = commons.limits.log_limit
UNIQUE_KEY = commons.keys.value

# دوال مساعدة
def get_environment() -> Environment:
   """تحديد بيئة التشغيل"""
   env = os.getenv("APP_ENV", "development").lower()
   return Environment(env)

def is_production() -> bool:
   """التحقق من بيئة الإنتاج"""
   return get_environment() == Environment.PRODUCTION

def get_log_level() -> int:
   """تحديد مستوى السجلات"""
   if is_production():
       return logging.WARNING
   return logging.DEBUG

def setup_logging():
   """إعداد نظام السجلات"""
   logging.basicConfig(
       filename=str(LOG_LOCATION),
       level=get_log_level(),
       format=commons.logs.format
   )

# تهيئة السجلات عند استيراد الملف
setup_logging()