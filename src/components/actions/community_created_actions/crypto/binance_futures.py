from components.actions.base.action import Action
from components.config.security import SecurityConfig
from components.logs.log_event import LogEvent
import ccxt
import datetime
import hmac
import hashlib
import time
from flask import request
from components.config.binance_ips import BinanceIPs


class BinanceFutures(Action):
    def __init__(self):
        super().__init__()
        self.config = SecurityConfig.load_credentials()['binance_futures']
        self.setup_exchange()
        
    def verify_ip(self):
        """التحقق من عنوان IP"""
        client_ip = request.remote_addr
        if not BinanceIPs.is_ip_allowed(client_ip):
            error_msg = f"Unauthorized IP address: {client_ip}"
            self.log_error(error_msg)
            raise ValueError(error_msg)


    

    def setup_exchange(self):
        """تهيئة اتصال Binance Futures"""
        self.exchange = ccxt.binance({
            'apiKey': self.config['api_key'],
            'secret': self.config['api_secret'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True
            }
        })

        # تعيين وضع testnet إذا كان مطلوباً
        if self.config['testnet']:
            self.exchange.set_sandbox_mode(True)

    def verify_ip(self):
        """التحقق من عنوان IP"""
        client_ip = request.remote_addr
        if not SecurityConfig.validate_ip(client_ip, self.config['allowed_ips']):
            error_msg = f"Unauthorized IP address: {client_ip}"
            self.log_error(error_msg)
            raise ValueError(error_msg)

    def verify_request_signature(self, request_data):
        """التحقق من توقيع الطلب"""
        if 'signature' not in request_data:
            raise ValueError("Missing signature in request")

        # إنشاء التوقيع للتحقق
        timestamp = str(int(time.time() * 1000))
        message = timestamp + self.config['api_key']
        signature = hmac.new(
            self.config['api_secret'].encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if signature != request_data['signature']:
            raise ValueError("Invalid request signature")

    def log_error(self, error_message):
        """تسجيل الأخطاء"""
        log_event = LogEvent(
            self.name,
            'error',
            datetime.datetime.now(),
            error_message
        )
        log_event.write()

    def log_trade(self, trade_data, order_response):
        """تسجيل تفاصيل الصفقة"""
        log_event = LogEvent(
            self.name,
            'trade',
            datetime.datetime.now(),
            f"Trade executed - Symbol: {trade_data['symbol']}, "
            f"Side: {trade_data['side']}, "
            f"Order ID: {order_response['id']}"
        )
        log_event.write()

    def validate_trading_params(self, data):
        """التحقق من معلمات التداول"""
        required_fields = ['symbol', 'side', 'amount']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # تنسيق رمز العملة
        data['symbol'] = data['symbol'].upper()
        if not data['symbol'].endswith('USDT'):
            data['symbol'] = f"{data['symbol']}USDT"

        # التحقق من حدود التداول
        market = self.exchange.market(data['symbol'])
        if float(data['amount']) < market['limits']['amount']['min']:
            raise ValueError(f"Amount {data['amount']} below minimum {market['limits']['amount']['min']}")

        return data

    def prepare_order_params(self, trade_data):
        """تحضير معلمات الأمر"""
        params = {
            'symbol': trade_data['symbol'],
            'type': 'MARKET',
            'side': trade_data['side'].upper(),
            'amount': float(trade_data['amount'])
        }

        # إضافة Stop Loss وTake Profit إذا كانت موجودة
        if 'stopLoss' in trade_data:
            params['stopLoss'] = {
                'type': 'STOP_MARKET',
                'price': float(trade_data['stopLoss'])
            }

        if 'takeProfit' in trade_data:
            params['takeProfit'] = {
                'type': 'TAKE_PROFIT_MARKET',
                'price': float(trade_data['takeProfit'])
            }

        return params

    def execute_trade(self, trade_data):
        """تنفيذ الصفقة"""
        try:
            order_params = self.prepare_order_params(trade_data)
            order = self.exchange.create_order(**order_params)
            
            # إضافة أوامر Stop Loss وTake Profit
            if 'stopLoss' in trade_data:
                self.exchange.create_order(
                    symbol=trade_data['symbol'],
                    type='STOP_MARKET',
                    side='sell' if trade_data['side'].lower() == 'buy' else 'buy',
                    amount=float(trade_data['amount']),
                    price=float(trade_data['stopLoss'])
                )

            if 'takeProfit' in trade_data:
                self.exchange.create_order(
                    symbol=trade_data['symbol'],
                    type='TAKE_PROFIT_MARKET',
                    side='sell' if trade_data['side'].lower() == 'buy' else 'buy',
                    amount=float(trade_data['amount']),
                    price=float(trade_data['takeProfit'])
                )

            return order

        except ccxt.NetworkError as e:
            self.log_error(f"Network error: {str(e)}")
            raise
        except ccxt.ExchangeError as e:
            self.log_error(f"Exchange error: {str(e)}")
            raise
        except Exception as e:
            self.log_error(f"Unexpected error: {str(e)}")
            raise

    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)

        try:
            # التحقق من IP
            self.verify_ip()

            # الحصول على البيانات وتحقق من صحتها
            data = self.validate_data()
            self.verify_request_signature(data)
            
            # تحضير وتنفيذ الصفقة
            trade_data = self.validate_trading_params(data)
            order = self.execute_trade(trade_data)
            
            # تسجيل الصفقة
            self.log_trade(trade_data, order)
            
            return order

        except ValueError as e:
            self.log_error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            self.log_error(f"Error in BinanceFutures action: {str(e)}")
            raise


def test_api_connection(self):
    """
    اختبار اتصال API مع Binance Futures
    يقوم بالتحقق من:
    1. صحة API credentials
    2. الوصول إلى معلومات الحساب
    3. تحديد ما إذا كان الحساب في وضع testnet أم لا
    """
    try:
        # التحقق من الاتصال والتوازن
        balance = self.exchange.fetch_balance()
        
        # التحقق من معلومات الحساب
        account_info = self.exchange.fapiPrivateGetAccount()
        
        # طباعة معلومات مهمة للتحقق
        connection_info = {
            "status": "متصل بنجاح",
            "account_type": "testnet" if self.config['testnet'] else "حساب حقيقي",
            "total_balance_usdt": balance['USDT']['total'] if 'USDT' in balance else 0,
            "available_balance_usdt": balance['USDT']['free'] if 'USDT' in balance else 0,
            "position_initial_margin": account_info.get('totalInitialMargin', 0),
            "unrealized_pnl": account_info.get('totalUnrealizedProfit', 0),
            "api_permissions": {
                "spot": self.exchange.has['createOrder'],
                "futures": self.exchange.has['createOrder'],
                "margin": self.exchange.has['createMarginOrder']
            }
        }
        
        # تسجيل نجاح الاتصال
        self.log_action_event('info', f"API Connection Test: {connection_info}")
        
        return connection_info

    except ccxt.AuthenticationError as e:
        error_msg = "فشل المصادقة: API credentials غير صحيحة"
        self.log_error(error_msg)
        return {"status": "فشل", "error": error_msg}
        
    except ccxt.NetworkError as e:
        error_msg = f"خطأ في الشبكة: {str(e)}"
        self.log_error(error_msg)
        return {"status": "فشل", "error": error_msg}
        
    except Exception as e:
        error_msg = f"خطأ غير متوقع: {str(e)}"
        self.log_error(error_msg)
        return {"status": "فشل", "error": error_msg}        