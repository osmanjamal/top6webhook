import datetime
from logging import getLogger
from typing import Dict, Any, List, Optional
from components.logs.log_event import LogEvent
from utils.log import get_logger

logger = get_logger(__name__)

class ActionManager:
   """مدير الإجراءات - مسؤول عن إدارة وتتبع جميع الإجراءات"""
   
   def __init__(self):
       self._actions = []
       self._action_states = {}

   def get_all(self) -> List['Action']:
       """الحصول على جميع الإجراءات المسجلة"""
       return self._actions

   def get(self, action_name: str) -> Optional['Action']:
       """الحصول على إجراء محدد بالاسم"""
       try:
           return next(action for action in self._actions if action.name == action_name)
       except StopIteration:
           logger.error(f'Action not found: {action_name}')
           return None
           
   def register(self, action: 'Action') -> bool:
       """تسجيل إجراء جديد"""
       try:
           if not self.get(action.name):
               self._actions.append(action)
               self._action_states[action.name] = ActionState()
               logger.info(f'Action registered: {action.name}')
               return True
           logger.warning(f'Action already exists: {action.name}')
           return False
       except Exception as e:
           logger.error(f'Error registering action {action.name}: {str(e)}')
           return False
           
   def unregister(self, action_name: str) -> bool:
       """إلغاء تسجيل إجراء"""
       try:
           action = self.get(action_name)
           if action:
               self._actions.remove(action)
               del self._action_states[action_name]
               logger.info(f'Action unregistered: {action_name}')
               return True
           return False
       except Exception as e:
           logger.error(f'Error unregistering action {action_name}: {str(e)}')
           return False

am = ActionManager()

class ActionState:
   """حالة الإجراء - تتبع حالة وإحصائيات كل إجراء"""
   
   def __init__(self):
       self.is_active = True
       self.last_run = None
       self.run_count = 0
       self.success_count = 0
       self.error_count = 0
       self.last_error = None
       self.execution_times = []

   def record_execution(self, success: bool, execution_time: float):
       """تسجيل تنفيذ الإجراء"""
       self.run_count += 1
       self.last_run = datetime.datetime.now()
       self.execution_times.append(execution_time)
       
       if success:
           self.success_count += 1
       else:
           self.error_count += 1

   def get_stats(self) -> Dict[str, Any]:
       """الحصول على إحصائيات الإجراء"""
       return {
           'is_active': self.is_active,
           'last_run': self.last_run,
           'run_count': self.run_count,
           'success_rate': (self.success_count / self.run_count * 100) if self.run_count > 0 else 0,
           'avg_execution_time': sum(self.execution_times) / len(self.execution_times) if self.execution_times else 0
       }

class ActionLogEvent:
   """حدث تسجيل خاص بالإجراء"""
   
   def __init__(self, status: str, message: str):
       self.timestamp = datetime.datetime.now()
       self.status = status
       self.message = message

   def __str__(self) -> str:
       return f"[{self.timestamp}] {self.status}: {self.message}"

class Action:
   """الفئة الأساسية للإجراءات"""
   
   objects = am

   def __init__(self):
       self.name = self.get_name()
       self.logs = []
       self._raw_data = None
       self._config = {}
       self._dependencies = []
       
   def get_name(self) -> str:
       """الحصول على اسم الإجراء"""
       return type(self).__name__

   def __str__(self) -> str:
       return f'{self.name}'

   def register(self) -> None:
       """تسجيل الإجراء مع المدير"""
       self.objects.register(self)
       self._log_action('registered', 'Action registered successfully')

   def set_data(self, data: Dict[str, Any]) -> None:
       """تعيين بيانات الإجراء"""
       self._raw_data = data

   def validate_data(self) -> Dict[str, Any]:
       """التحقق من صحة البيانات"""
       if not self._raw_data:
           raise ValueError('No data provided to action')
       return self._raw_data

   def set_config(self, config: Dict[str, Any]) -> None:
       """تعيين إعدادات الإجراء"""
       self._config = config

   def add_dependency(self, action: 'Action') -> None:
       """إضافة اعتماد على إجراء آخر"""
       if action not in self._dependencies:
           self._dependencies.append(action)

   def _log_action(self, status: str, message: str) -> None:
       """تسجيل حدث الإجراء"""
       log_event = ActionLogEvent(status, message)
       self.logs.append(log_event)
       
       system_log = LogEvent(
           parent=self.name,
           event_type=status,
           event_time=datetime.datetime.now(),
           event_data=message
       )
       system_log.write()

   def get_state(self) -> ActionState:
       """الحصول على حالة الإجراء"""
       return self.objects._action_states.get(self.name, ActionState())

   async def run(self, *args, **kwargs) -> Any:
       """تنفيذ الإجراء"""
       start_time = datetime.datetime.now()
       success = False
       
       try:
           # تنفيذ الاعتمادات أولاً
           for dep in self._dependencies:
               await dep.run(*args, **kwargs)
               
           # تنفيذ الإجراء الرئيسي
           result = await self.execute(*args, **kwargs)
           success = True
           
           execution_time = (datetime.datetime.now() - start_time).total_seconds()
           self.get_state().record_execution(success, execution_time)
           
           self._log_action('success', f'Action executed successfully in {execution_time:.2f}s')
           return result
           
       except Exception as e:
           execution_time = (datetime.datetime.now() - start_time).total_seconds()
           self.get_state().record_execution(False, execution_time)
           self._log_action('error', f'Action failed: {str(e)}')
           raise

   async def execute(self, *args, **kwargs) -> Any:
       """تنفيذ منطق الإجراء الفعلي - يجب تجاوزه في الفئات الفرعية"""
       raise NotImplementedError("Action must implement execute method")