from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
import json
import os
from components.logs.commons import LOG_LOCATION, LOG_LIMIT

class LogLevel(Enum):
   """مستويات التسجيل"""
   DEBUG = "DEBUG"
   INFO = "INFO"
   WARNING = "WARNING"
   ERROR = "ERROR"
   CRITICAL = "CRITICAL"

class LogCategory(Enum):
   """فئات السجلات"""
   SYSTEM = "SYSTEM"
   SECURITY = "SECURITY"
   TRADING = "TRADING"
   EVENT = "EVENT"
   ACTION = "ACTION"
   API = "API"

class LogEvent:
   """فئة تمثل حدث السجل"""
   
   def __init__(self, 
                parent: str = None,
                level: LogLevel = LogLevel.INFO,
                category: LogCategory = LogCategory.SYSTEM,
                event_type: str = None,
                event_time: datetime = None,
                event_data: Any = None,
                metadata: Dict = None):
       
       self.parent = parent
       self.level = level if isinstance(level, LogLevel) else LogLevel.INFO
       self.category = category if isinstance(category, LogCategory) else LogCategory.SYSTEM
       self.event_type = event_type
       self.event_time = event_time or datetime.now()
       self.event_data = self._format_data(event_data)
       self.metadata = metadata or {}

   def _format_data(self, data: Any) -> str:
       """تنسيق البيانات للتخزين"""
       if data is None:
           return ""
       if isinstance(data, (dict, list)):
           return json.dumps(data, ensure_ascii=False)
       return str(data).replace(',', ' ')

   def __str__(self) -> str:
       """تمثيل نصي للحدث"""
       return (f"[{self.event_time.strftime('%Y-%m-%d %H:%M:%S')}] "
               f"{self.level.value} - {self.category.value}: {self.event_data}")

   def to_dict(self) -> Dict[str, Any]:
       """تحويل الحدث إلى قاموس"""
       return {
           "parent": self.parent,
           "level": self.level.value,
           "category": self.category.value,
           "event_type": self.event_type,
           "event_time": self.event_time.strftime("%Y-%m-%d %H:%M:%S"),
           "event_data": self.event_data,
           "metadata": self.metadata
       }

   def to_line(self) -> str:
       """تحويل الحدث إلى سطر نصي للتخزين"""
       data = self.to_dict()
       return (f"{data['parent']},{data['level']},{data['category']},"
               f"{data['event_type']},{data['event_time']},{data['event_data']}")

   def from_line(self, line: str) -> 'LogEvent':
       """إنشاء حدث من سطر نصي"""
       try:
           parts = line.strip().split(',', 5)
           if len(parts) >= 6:
               self.parent, level, category, self.event_type, time_str, self.event_data = parts
               self.level = LogLevel(level)
               self.category = LogCategory(category)
               self.event_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
           return self
       except Exception as e:
           raise ValueError(f"Invalid log line format: {e}")

   def write(self) -> bool:
       """كتابة الحدث إلى ملف السجل"""
       try:
           self._ensure_log_file()
           
           # قراءة السجلات الحالية
           with open(LOG_LOCATION, 'r') as f:
               logs = f.readlines()

           # إدارة حجم ملف السجل
           if len(logs) >= LOG_LIMIT:
               logs = logs[1:]  # حذف أقدم سجل

           # إضافة السجل الجديد
           logs.append(self.to_line() + '\n')

           # كتابة جميع السجلات
           with open(LOG_LOCATION, 'w') as f:
               f.writelines(logs)

           return True
       except Exception as e:
           print(f"Error writing log: {e}")  # استخدام print لتجنب التكرار المتداخل
           return False

   def _ensure_log_file(self) -> None:
       """التأكد من وجود ملف السجل"""
       os.makedirs(os.path.dirname(LOG_LOCATION), exist_ok=True)
       if not os.path.exists(LOG_LOCATION):
           with open(LOG_LOCATION, 'w') as f:
               f.write("")

class LogManager:
   """فئة لإدارة السجلات"""
   
   def __init__(self):
       self._ensure_log_file()

   def _ensure_log_file(self) -> None:
       """التأكد من وجود ملف السجل"""
       os.makedirs(os.path.dirname(LOG_LOCATION), exist_ok=True)
       if not os.path.exists(LOG_LOCATION):
           with open(LOG_LOCATION, 'w') as f:
               f.write("")

   def get_logs(self, 
                filters: Dict = None,
                limit: int = 100,
                offset: int = 0) -> List[LogEvent]:
       """جلب السجلات مع إمكانية التصفية"""
       try:
           filters = filters or {}
           logs = []
           
           with open(LOG_LOCATION, 'r') as f:
               for line in f:
                   try:
                       log = LogEvent().from_line(line)
                       if self._matches_filters(log, filters):
                           logs.append(log)
                   except ValueError:
                       continue

           # ترتيب وتقسيم النتائج
           logs.sort(key=lambda x: x.event_time, reverse=True)
           return logs[offset:offset + limit]

       except Exception as e:
           print(f"Error reading logs: {e}")
           return []

   def _matches_filters(self, log: LogEvent, filters: Dict) -> bool:
       """التحقق من تطابق السجل مع المرشحات"""
       for key, value in filters.items():
           if key == 'start_time' and log.event_time < value:
               return False
           if key == 'end_time' and log.event_time > value:
               return False
           if key == 'level' and log.level != value:
               return False
           if key == 'category' and log.category != value:
               return False
           if key == 'parent' and log.parent != value:
               return False
       return True

   def clear_logs(self) -> bool:
       """مسح جميع السجلات"""
       try:
           with open(LOG_LOCATION, 'w') as f:
               f.write("")
           return True
       except Exception as e:
           print(f"Error clearing logs: {e}")
           return False

   def export_logs(self, 
                  format: str = 'json',
                  filters: Dict = None) -> Optional[str]:
       """تصدير السجلات بتنسيق محدد"""
       try:
           logs = self.get_logs(filters=filters, limit=None)
           
           if format.lower() == 'json':
               return json.dumps([log.to_dict() for log in logs], 
                               ensure_ascii=False, 
                               indent=2)
           elif format.lower() == 'csv':
               header = "parent,level,category,event_type,event_time,event_data\n"
               return header + ''.join(log.to_line() + '\n' for log in logs)
           else:
               raise ValueError(f"Unsupported export format: {format}")
               
       except Exception as e:
           print(f"Error exporting logs: {e}")
           return None