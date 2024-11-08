import datetime
from hashlib import md5
from typing import List, Dict, Any, Optional
from commons import LOG_LOCATION, UNIQUE_KEY
from components.logs.log_event import LogEvent
from utils.log import get_logger

logger = get_logger(__name__)

class EventManager:
   """مدير الأحداث - مسؤول عن إدارة وتتبع جميع الأحداث"""
   
   def __init__(self):
       self._events: List['Event'] = []
       self._event_states: Dict[str, 'EventState'] = {}

   def get_all(self) -> List['Event']:
       """جلب جميع الأحداث المسجلة"""
       return self._events

   def get(self, event_name: str) -> Optional['Event']:
       """جلب حدث محدد بالاسم"""
       try:
           return next(event for event in self._events if event.name == event_name)
       except StopIteration:
           logger.error(f'Event not found: {event_name}')
           return None

   def register_event(self, event: 'Event') -> bool:
       """تسجيل حدث جديد"""
       try:
           if not self.get(event.name):
               self._events.append(event)
               self._event_states[event.name] = EventState()
               logger.info(f'Event registered: {event.name}')
               return True
           logger.warning(f'Event already exists: {event.name}')
           return False
       except Exception as e:
           logger.error(f'Error registering event {event.name}: {str(e)}')
           return False

em = EventManager()

class EventState:
   """حالة الحدث - تتبع حالة وإحصائيات كل حدث"""
   
   def __init__(self):
       self.active = True
       self.last_triggered = None
       self.trigger_count = 0
       self.success_count = 0
       self.failed_count = 0
       self.last_error = None
       self.execution_times = []

   def record_trigger(self, success: bool, execution_time: float):
       """تسجيل تنفيذ الحدث"""
       self.trigger_count += 1
       self.last_triggered = datetime.datetime.now()
       self.execution_times.append(execution_time)
       
       if success:
           self.success_count += 1
       else:
           self.failed_count += 1
   
   def get_stats(self) -> Dict[str, Any]:
       """جلب إحصائيات الحدث"""
       return {
           'active': self.active,
           'last_triggered': self.last_triggered,
           'trigger_count': self.trigger_count,
           'success_rate': (self.success_count / self.trigger_count * 100) if self.trigger_count > 0 else 0,
           'avg_execution_time': sum(self.execution_times) / len(self.execution_times) if self.execution_times else 0,
           'last_error': str(self.last_error) if self.last_error else None
       }

class Event:
   """الفئة الأساسية للأحداث"""
   
   objects = em

   def __init__(self):
       self.name = self.get_name()
       self.active = True
       self.webhook = True
       self.key = self._generate_key()
       self._actions = []
       self.logs = self._load_logs()

   def get_name(self) -> str:
       """جلب اسم الحدث"""
       return type(self).__name__

   def _generate_key(self) -> str:
       """توليد مفتاح فريد للحدث"""
       unique_string = f"{self.name + UNIQUE_KEY}"
       return f'{self.name}:{md5(unique_string.encode()).hexdigest()[:6]}'

   def _load_logs(self) -> List[LogEvent]:
       """تحميل سجلات الحدث"""
       try:
           with open(LOG_LOCATION, 'r') as f:
               return [LogEvent().from_line(line) for line in f if line.split(',')[0] == self.name]
       except Exception as e:
           logger.error(f"Error loading logs: {str(e)}")
           return []

   def add_action(self, action) -> None:
       """إضافة إجراء للحدث"""
       if action not in self._actions:
           self._actions.append(action)
           logger.info(f'Action {action.name} added to event {self.name}')

   def remove_action(self, action) -> None:
       """إزالة إجراء من الحدث"""
       if action in self._actions:
           self._actions.remove(action)
           logger.info(f'Action {action.name} removed from event {self.name}')

   def get_actions(self) -> List[Any]:
       """جلب جميع الإجراءات المرتبطة"""
       return self._actions

   def register(self) -> None:
       """تسجيل الحدث مع المدير"""
       self.objects.register_event(self)

   def validate_trigger_data(self, data: Dict) -> bool:
       """التحقق من صحة بيانات التشغيل"""
       if not isinstance(data, dict):
           logger.error(f"Invalid trigger data type for event {self.name}")
           return False
           
       if 'key' not in data:
           logger.error(f"Missing key in trigger data for event {self.name}")
           return False
           
       if data['key'] != self.key:
           logger.error(f"Invalid key in trigger data for event {self.name}")
           return False
           
       return True

   async def trigger(self, data: Dict = None) -> bool:
       """تشغيل الحدث"""
       if not self.active:
           logger.warning(f"Event {self.name} is inactive")
           return False

       if not self._actions:
           logger.warning(f"No actions registered for event {self.name}")
           return False

       start_time = datetime.datetime.now()
       success = False

       try:
           # التحقق من صحة البيانات
           if not self.validate_trigger_data(data):
               raise ValueError("Invalid trigger data")

           # تسجيل بدء التشغيل
           self._log_event('trigger_start', f'Event {self.name} triggered with data: {data}')

           # تنفيذ الإجراءات
           for action in self._actions:
               try:
                   action.set_data(data)
                   await action.run()
               except Exception as e:
                   logger.error(f"Error in action {action.name}: {str(e)}")
                   raise

           success = True
           execution_time = (datetime.datetime.now() - start_time).total_seconds()
           self.objects._event_states[self.name].record_trigger(True, execution_time)
           self._log_event('trigger_success', f'Event completed successfully in {execution_time:.2f}s')
           return True

       except Exception as e:
           execution_time = (datetime.datetime.now() - start_time).total_seconds()
           self.objects._event_states[self.name].record_trigger(False, execution_time)
           self.objects._event_states[self.name].last_error = str(e)
           self._log_event('trigger_error', f'Event failed: {str(e)}')
           return False

   def _log_event(self, event_type: str, message: str) -> None:
       """تسجيل حدث في السجلات"""
       log_event = LogEvent(
           parent=self.name,
           event_type=event_type,
           event_time=datetime.datetime.now(),
           event_data=message
       )
       log_event.write()
       self.logs.append(log_event)

   def get_state(self) -> EventState:
       """جلب حالة الحدث"""
       return self.objects._event_states.get(self.name, EventState())

   def __str__(self) -> str:
       return f'{self.name} ({"Active" if self.active else "Inactive"})'