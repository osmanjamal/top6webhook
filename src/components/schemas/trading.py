import json
from decimal import Decimal
from typing import Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from components.schemas.base.schema import Schema

class OrderType(Enum):
   """أنواع الأوامر"""
   MARKET = "MARKET"
   LIMIT = "LIMIT" 
   STOP_MARKET = "STOP_MARKET"
   TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
   STOP_LIMIT = "STOP_LIMIT"
   TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"

class OrderSide(Enum):
   """جوانب الأوامر"""
   BUY = "BUY"
   SELL = "SELL"

class PositionSide(Enum):
   """جوانب المراكز"""
   LONG = "LONG"
   SHORT = "SHORT"

@dataclass
class OrderValidationConfig:
   """تكوين التحقق من الأوامر"""
   min_quantity: Decimal
   max_quantity: Decimal
   price_precision: int
   quantity_precision: int
   min_notional: Decimal
   max_leverage: int

class Order(Schema):
   """نموذج الأمر"""
   
   def __init__(self):
       super().__init__()
       self.order_id: str = None
       self.order_type: OrderType = OrderType.MARKET
       self.side: OrderSide = OrderSide.BUY
       self.symbol: str = None
       self.quantity: Decimal = Decimal('0')
       self.price: Optional[Decimal] = None
       self.stop_price: Optional[Decimal] = None
       self.leverage: int = 1
       self.reduce_only: bool = False
       self.created_at: datetime = None
       self.status: str = None
       
   def validate(self, config: OrderValidationConfig) -> bool:
       """التحقق من صحة الأمر"""
       try:
           # التحقق من الرمز
           if not self.symbol or not self.symbol.endswith('USDT'):
               raise ValueError("Invalid symbol format")

           # التحقق من الكمية
           if not config.min_quantity <= self.quantity <= config.max_quantity:
               raise ValueError(f"Quantity must be between {config.min_quantity} and {config.max_quantity}")

           # التحقق من السعر للأوامر المحددة
           if self.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
               if not self.price:
                   raise ValueError("Price is required for limit orders")
               if self.price <= 0:
                   raise ValueError("Price must be positive")

           # التحقق من الرافعة المالية
           if self.leverage > config.max_leverage:
               raise ValueError(f"Leverage cannot exceed {config.max_leverage}")

           # التحقق من القيمة الإجمالية
           notional = self.quantity * (self.price or Decimal('0'))
           if notional < config.min_notional:
               raise ValueError(f"Order value must be at least {config.min_notional} USDT")

           return True
           
       except ValueError as e:
           raise
       except Exception as e:
           raise ValueError(f"Validation error: {str(e)}")

   def as_dict(self) -> Dict[str, Any]:
       """تحويل الأمر إلى قاموس"""
       return {
           'order_id': self.order_id,
           'order_type': self.order_type.value,
           'side': self.side.value,
           'symbol': self.symbol,
           'quantity': str(self.quantity),
           'price': str(self.price) if self.price else None,
           'stop_price': str(self.stop_price) if self.stop_price else None,
           'leverage': self.leverage,
           'reduce_only': self.reduce_only,
           'created_at': self.created_at.isoformat() if self.created_at else None,
           'status': self.status
       }

   def as_json(self) -> str:
       """تحويل الأمر إلى JSON"""
       return json.dumps(self.as_dict())

   @classmethod
   def from_dict(cls, data: Dict[str, Any]) -> 'Order':
       """إنشاء أمر من قاموس"""
       order = cls()
       order.order_id = data.get('order_id')
       order.order_type = OrderType(data.get('order_type', 'MARKET'))
       order.side = OrderSide(data.get('side', 'BUY'))
       order.symbol = data.get('symbol')
       order.quantity = Decimal(str(data.get('quantity', '0')))
       order.price = Decimal(str(data.get('price'))) if data.get('price') else None
       order.stop_price = Decimal(str(data.get('stop_price'))) if data.get('stop_price') else None
       order.leverage = int(data.get('leverage', 1))
       order.reduce_only = bool(data.get('reduce_only', False))
       order.created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
       order.status = data.get('status')
       return order

class Position(Schema):
   """نموذج المركز"""
   
   def __init__(self):
       super().__init__()
       self.symbol: str = None
       self.side: PositionSide = None
       self.quantity: Decimal = Decimal('0')
       self.entry_price: Decimal = Decimal('0')
       self.leverage: int = 1
       self.unrealized_pnl: Decimal = Decimal('0')
       self.margin_type: str = 'isolated'
       self.take_profit: Optional[Decimal] = None
       self.stop_loss: Optional[Decimal] = None
       self.liquidation_price: Optional[Decimal] = None
       self.created_at: datetime = datetime.now()
       self.updated_at: datetime = datetime.now()

   def calculate_pnl(self, current_price: Decimal) -> Decimal:
       """حساب الربح/الخسارة"""
       if self.side == PositionSide.LONG:
           return (current_price - self.entry_price) * self.quantity
       else:
           return (self.entry_price - current_price) * self.quantity

   def calculate_margin(self) -> Decimal:
       """حساب الهامش"""
       return (self.entry_price * self.quantity) / self.leverage

   def update_risk_levels(self, 
                         take_profit: Optional[Decimal] = None,
                         stop_loss: Optional[Decimal] = None) -> None:
       """تحديث مستويات المخاطرة"""
       if take_profit:
           self._validate_price_level(take_profit, 'take_profit')
           self.take_profit = take_profit
           
       if stop_loss:
           self._validate_price_level(stop_loss, 'stop_loss')
           self.stop_loss = stop_loss
           
       self.updated_at = datetime.now()

   def _validate_price_level(self, price: Decimal, level_type: str) -> None:
       """التحقق من صحة مستوى السعر"""
       if price <= 0:
           raise ValueError(f"Invalid {level_type} price")
           
       if level_type == 'take_profit':
           if self.side == PositionSide.LONG and price <= self.entry_price:
               raise ValueError("Take profit must be above entry price for long positions")
           if self.side == PositionSide.SHORT and price >= self.entry_price:
               raise ValueError("Take profit must be below entry price for short positions")
               
       if level_type == 'stop_loss':
           if self.side == PositionSide.LONG and price >= self.entry_price:
               raise ValueError("Stop loss must be below entry price for long positions")
           if self.side == PositionSide.SHORT and price <= self.entry_price:
               raise ValueError("Stop loss must be above entry price for short positions")

   def as_dict(self) -> Dict[str, Any]:
       """تحويل المركز إلى قاموس"""
       return {
           'symbol': self.symbol,
           'side': self.side.value if self.side else None,
           'quantity': str(self.quantity),
           'entry_price': str(self.entry_price),
           'leverage': self.leverage,
           'unrealized_pnl': str(self.unrealized_pnl),
           'margin_type': self.margin_type,
           'take_profit': str(self.take_profit) if self.take_profit else None,
           'stop_loss': str(self.stop_loss) if self.stop_loss else None,
           'liquidation_price': str(self.liquidation_price) if self.liquidation_price else None,
           'created_at': self.created_at.isoformat(),
           'updated_at': self.updated_at.isoformat()
       }

   def as_json(self) -> str:
       """تحويل المركز إلى JSON"""
       return json.dumps(self.as_dict())

   @classmethod
   def from_dict(cls, data: Dict[str, Any]) -> 'Position':
       """إنشاء مركز من قاموس"""
       position = cls()
       position.symbol = data.get('symbol')
       position.side = PositionSide(data['side']) if data.get('side') else None
       position.quantity = Decimal(str(data.get('quantity', '0')))
       position.entry_price = Decimal(str(data.get('entry_price', '0')))
       position.leverage = int(data.get('leverage', 1))
       position.unrealized_pnl = Decimal(str(data.get('unrealized_pnl', '0')))
       position.margin_type = data.get('margin_type', 'isolated')
       position.take_profit = Decimal(str(data['take_profit'])) if data.get('take_profit') else None
       position.stop_loss = Decimal(str(data['stop_loss'])) if data.get('stop_loss') else None
       position.liquidation_price = Decimal(str(data['liquidation_price'])) if data.get('liquidation_price') else None
       position.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
       position.updated_at = datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
       return position