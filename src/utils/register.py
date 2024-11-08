import importlib
from importlib import import_module
import traceback
from typing import Optional, Any, List, Dict
import json

from utils.formatting import snake_case
from utils.log import get_logger

logger = get_logger(__name__)

class RegistrationError(Exception):
   """خطأ في عملية التسجيل"""
   pass

class DependencyError(Exception):
   """خطأ في الاعتمادات"""
   pass

class RegisterManager:
   """مدير التسجيل المركزي"""
   
   def __init__(self):
       self.registered_actions = {}
       self.registered_events = {}
       self.dependencies = {}
       
   def register_action(self, action_name: str) -> str:
       """تسجيل إجراء جديد"""
       try:
           # التحقق من صحة الاسم
           if not self._validate_name(action_name):
               raise RegistrationError(f"Invalid action name: {action_name}")

           # تحويل الاسم إلى snake_case
           snake_name = snake_case(action_name)
           
           # استيراد وإنشاء الإجراء
           try:
               action = self._import_component(
                   component_type='actions',
                   name=snake_name,
                   class_name=action_name
               )
               
               # التحقق من الاعتمادات
               self._check_dependencies(action)
               
               # تسجيل الإجراء
               action.register()
               self.registered_actions[action_name] = action
               
               logger.info(f'Action "{action_name}" registered successfully!')
               return action_name
               
           except ImportError as e:
               logger.error(f'Action {action_name} not found: {str(e)}')
               raise RegistrationError(f"Failed to import action: {str(e)}")
               
       except Exception as e:
           logger.error(f'Failed to register action "{action_name}": {str(e)}')
           traceback.print_exc()
           raise

   def register_event(self, event_name: str) -> Any:
       """تسجيل حدث جديد"""
       try:
           # التحقق من صحة الاسم
           if not self._validate_name(event_name):
               raise RegistrationError(f"Invalid event name: {event_name}")

           # تحويل الاسم إلى snake_case
           snake_name = snake_case(event_name)
           
           # استيراد وإنشاء الحدث
           try:
               event = self._import_component(
                   component_type='events',
                   name=snake_name,
                   class_name=event_name
               )
               
               # تسجيل الحدث
               event.register()
               self.registered_events[event_name] = event
               
               logger.info(f'Event "{event_name}" registered successfully!')
               return event
               
           except ImportError as e:
               logger.error(f'Event {event_name} not found: {str(e)}')
               raise RegistrationError(f"Failed to import event: {str(e)}")
               
       except Exception as e:
           logger.error(f'Failed to register event "{event_name}": {str(e)}')
           traceback.print_exc()
           raise

   def register_link(self, link: tuple, event_manager, action_manager) -> bool:
       """ربط إجراء بحدث"""
       try:
           action_name, event_name = link
           
           # الحصول على الإجراء والحدث
           action = action_manager.get(action_name)
           event = event_manager.get(event_name)
           
           if not action or not event:
               raise RegistrationError("Action or event not found")
               
           # إضافة الإجراء للحدث
           event.add_action(action)
           logger.info(f'Link "{action_name} -> {event_name}" registered successfully!')
           
           # حفظ الاعتماد
           self._add_dependency(event_name, action_name)
           
           return True
           
       except Exception as e:
           logger.error(f'Failed to register link: {str(e)}')
           traceback.print_exc()
           return False

   def _validate_name(self, name: str) -> bool:
       """التحقق من صحة اسم المكون"""
       if not name:
           return False
       if not name[0].isupper():
           return False
       if any(c in name for c in ['_', ' ', '-']):
           return False
       return True

   def _import_component(self, component_type: str, name: str, class_name: str) -> Any:
       """استيراد مكون (إجراء أو حدث)"""
       module = import_module(f'components.{component_type}.{name}')
       component = getattr(module, class_name)()
       return component

   def _check_dependencies(self, component: Any) -> None:
       """التحقق من الاعتمادات"""
       if hasattr(component, 'dependencies'):
           for dep in component.dependencies:
               if dep not in self.registered_actions:
                   raise DependencyError(f"Missing dependency: {dep}")

   def _add_dependency(self, event_name: str, action_name: str) -> None:
       """إضافة اعتماد"""
       if event_name not in self.dependencies:
           self.dependencies[event_name] = []
       self.dependencies[event_name].append(action_name)

   def get_component_info(self, component_name: str) -> Dict:
       """الحصول على معلومات المكون"""
       try:
           # البحث في الإجراءات
           if component_name in self.registered_actions:
               component = self.registered_actions[component_name]
               deps = [name for name, deps in self.dependencies.items() if component_name in deps]
               return {
                   'type': 'action',
                   'name': component_name,
                   'dependencies': deps,
                   'registered': True,
                   'active': True if hasattr(component, 'active') else None
               }
           
           # البحث في الأحداث
           if component_name in self.registered_events:
               component = self.registered_events[component_name]
               deps = self.dependencies.get(component_name, [])
               return {
                   'type': 'event',
                   'name': component_name,
                   'actions': deps,
                   'registered': True,
                   'active': component.active if hasattr(component, 'active') else None
               }
               
           return {
               'name': component_name,
               'registered': False
           }
           
       except Exception as e:
           logger.error(f'Error getting component info: {str(e)}')
           return None

   def export_registration_state(self) -> str:
       """تصدير حالة التسجيل"""
       state = {
           'actions': list(self.registered_actions.keys()),
           'events': list(self.registered_events.keys()),
           'dependencies': self.dependencies
       }
       return json.dumps(state, indent=2)

# إنشاء نسخة واحدة من مدير التسجيل
register_manager = RegisterManager()

# تصدير الدوال الرئيسية للاستخدام المباشر
def register_action(action_name: str) -> str:
   return register_manager.register_action(action_name)

def register_event(event_name: str) -> Any:
   return register_manager.register_event(event_name)

def register_link(link: tuple, event_manager, action_manager) -> bool:
   return register_manager.register_link(link, event_manager, action_manager)