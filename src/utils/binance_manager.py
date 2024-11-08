import ccxt
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BinanceManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.exchange = None

    # 1. وظائف الاتصال والتهيئة
def setup_connection(self) -> bool:
    """إعداد الاتصال مع Binance"""
    try:
        creds = self.config_manager.load_credentials().get('binance_futures', {})
        if not self._validate_credentials(creds):
            logger.warning("Invalid or missing credentials")
            return False

        self.exchange = self._create_exchange(creds)
        
        # اختبار الاتصال بشكل صريح
        test_result = self.test_connection()
        if test_result['status'] == 'success':
            logger.info("Binance connection established successfully")
            return True
        else:
            logger.error(f"Connection test failed: {test_result.get('message')}")
            self.exchange = None
            return False

    except Exception as e:
        logger.error(f"Binance connection failed: {str(e)}")
        self.exchange = None
        return False

def validate_credentials(self, creds: dict) -> bool:
    """التحقق من صحة بيانات الاعتماد"""
    if not creds.get('api_key') or not creds.get('api_secret'):
        logger.warning("Missing API credentials")
        return False
    return True

def create_exchange(self, creds: dict) -> Any:
    """إنشاء كائن التداول"""
    exchange_config = {
        'apiKey': creds['api_key'],
        'secret': creds['api_secret'],
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True,
            'recvWindow': 60000
        }
    }
    
    exchange = ccxt.binance(exchange_config)
    if creds.get('testnet', False):
        exchange.set_sandbox_mode(True)
        logger.info("Running in testnet mode")
    return exchange

def test_connection(self) -> Dict[str, Any]:
    """اختبار الاتصال وجلب معلومات الحساب"""
    try:
        if not self.exchange:
            return {
                "status": "error",
                "message": "Exchange not initialized"
            }

        # اختبار أساسي للاتصال
        server_time = self.exchange.fetch_time()
        balance = self.exchange.fetch_balance()

        return {
            "status": "success",
            "account_type": "testnet" if self.exchange.urls['api']['public'].endswith('testnet') else "live",
            "total_balance": balance.get('USDT', {}).get('total', 0),
            "available_balance": balance.get('USDT', {}).get('free', 0)
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Connection test failed: {error_msg}")
        return {
            "status": "error",
            "message": error_msg
        }

    def _validate_credentials(self, creds: Dict) -> bool:
        """التحقق من صحة بيانات الاعتماد"""
        if not creds.get('api_key') or not creds.get('api_secret'):
            logger.warning("Missing Binance credentials")
            return False
        return True

    def _create_exchange(self, creds: Dict) -> Any:
        """إنشاء كائن التداول"""
        exchange_config = {
            'apiKey': creds['api_key'],
            'secret': creds['api_secret'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
                'recvWindow': 60000
            }
        }
        
        exchange = ccxt.binance(exchange_config)
        if creds.get('testnet', False):
            exchange.set_sandbox_mode(True)
        return exchange

    def _test_connection(self):
        """اختبار الاتصال"""
        self.exchange.fetch_balance()
        logger.info("Binance connection successful")

    # 2. وظائف معلومات الحساب
    def get_account_info(self) -> Dict[str, Any]:
        """جلب معلومات الحساب"""
        if not self.exchange:
            return self._get_empty_account_info()
            
        try:
            balance = self.exchange.fetch_balance()
            positions = self.exchange.fetch_positions()
            
            total_unrealized_pnl = sum(float(pos['unrealizedPnl']) for pos in positions if float(pos['contracts']) > 0)
            wallet_balance = float(balance.get('USDT', {}).get('total', 0))
            used_margin = float(balance.get('USDT', {}).get('used', 0))
            
            return {
                "totalWalletBalance": wallet_balance,
                "totalUnrealizedProfit": total_unrealized_pnl,
                "totalMarginBalance": wallet_balance + total_unrealized_pnl,
                "totalInitialMargin": used_margin,
                "totalMaintMargin": used_margin * 0.4,
                "marginLevel": (wallet_balance / used_margin * 100) if used_margin > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error fetching account info: {str(e)}")
            return self._get_empty_account_info()

    def get_balance(self) -> Dict[str, Any]:
        """جلب معلومات الرصيد"""
        if not self.exchange:
            return self._get_empty_balance()
            
        try:
            balance = self.exchange.fetch_balance()
            return {
                "total": balance.get('total', {}),
                "free": balance.get('free', {}),
                "used": balance.get('used', {})
            }
        except Exception as e:
            logger.error(f"Error fetching balance: {str(e)}")
            return self._get_empty_balance()

    # 3. وظائف التداول
    def create_order(self, symbol: str, order_type: str, side: str, amount: float, 
                    price: Optional[float] = None, params: Dict = {}) -> Dict[str, Any]:
        """إنشاء أمر جديد"""
        if not self.exchange:
            raise Exception("Exchange not initialized")
            
        try:
            self._validate_order_params(symbol, order_type, side, amount)
            return self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params
            )
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            raise

    def get_open_positions(self) -> list:
        """جلب المراكز المفتوحة"""
        if not self.exchange:
            return []
            
        try:
            positions = self.exchange.fetch_positions()
            return [self._format_position(pos) for pos in positions if float(pos['contracts']) > 0]
        except Exception as e:
            logger.error(f"Error fetching positions: {str(e)}")
            raise

    # 4. وظائف مساعدة
    def _get_empty_account_info(self) -> Dict[str, Any]:
        """إرجاع معلومات حساب فارغة"""
        return {
            "totalWalletBalance": 0,
            "totalUnrealizedProfit": 0,
            "totalMarginBalance": 0,
            "totalInitialMargin": 0,
            "totalMaintMargin": 0,
            "marginLevel": 0
        }

    def _get_empty_balance(self) -> Dict[str, Any]:
        """إرجاع رصيد فارغ"""
        return {
            "total": {},
            "free": {},
            "used": {}
        }

    def _format_position(self, pos: Dict) -> Dict:
        """تنسيق بيانات المركز"""
        return {
            "symbol": pos['symbol'],
            "side": pos['side'],
            "size": pos['contracts'],
            "notional": pos['notional'],
            "leverage": pos['leverage'],
            "entryPrice": pos['entryPrice'],
            "markPrice": pos['markPrice'],
            "unrealizedPnl": pos['unrealizedPnl'],
            "percentage": pos['percentage']
        }

    def _validate_order_params(self, symbol: str, order_type: str, side: str, amount: float):
        """التحقق من صحة معاملات الأمر"""
        if not symbol or not order_type or not side:
            raise ValueError("Missing required order parameters")
        if amount <= 0:
            raise ValueError("Amount must be positive")