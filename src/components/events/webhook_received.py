from components.events.base.event import Event
from components.logs.log_event import LogEvent
import datetime

class WebhookReceived(Event):
    def __init__(self):
        super().__init__()
        self.webhook = True  # This is important!
        
    def trigger(self, data=None):
        """تشغيل الحدث مع تسجيل النشاط"""
        if self.active and len(self._actions) > 0:
            log_event = LogEvent(
                self.name,
                'trigger',
                datetime.datetime.now(),
                f'Webhook received with data for symbol: {data.get("symbol", "unknown")}'
            )
            log_event.write()
            
            # تنفيذ جميع الإجراءات المرتبطة
            for action in self._actions:
                try:
                    action.set_data(data)
                    action.run()
                except Exception as e:
                    error_event = LogEvent(
                        self.name,
                        'error',
                        datetime.datetime.now(),
                        f'Error in action {action.name}: {str(e)}'
                    )
                    error_event.write()
        else:
            if not self.active:
                print(f"Event {self.name} is not active")
            if len(self._actions) == 0:
                print(f"No actions linked to event {self.name}")
            
    @property
    def webhook_url(self):
        """Return the webhook URL for this event"""
        return f"http://localhost:5000/webhook"
        
    def get_webhook_data(self):
        """Example webhook data format"""
        return {
            "key": self.key,
            "symbol": "BTCUSDT",
            "side": "buy",
            "amount": 0.001
        }