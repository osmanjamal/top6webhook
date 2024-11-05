from components.events.base.event import Event

class WebhookReceived(Event):

    def __init__(self):
        super().__init__()
        # Get webhook key from self.key
        # Format: WebhookReceived:xxxxx

    @property
    def webhook_url(self):
        return f"http://149.28.119.62:5000/webhook"
        
    def get_webhook_data(self):
        """Example of webhook data format for TradingView"""
        return {
            "key": self.key,   # سيتم إنشاؤه تلقائياً
            "symbol": "BTCUSDT",    
            "side": "buy",          # or sell
            "amount": 0.001,        # كمية العقد
            
        }