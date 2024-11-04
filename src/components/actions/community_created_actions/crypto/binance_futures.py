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

    def setup_exchange(self):
        """Initialize Binance Futures connection"""
        self.exchange = ccxt.binance({
            'apiKey': self.config['api_key'],
            'secret': self.config['api_secret'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True
            }
        })

        if self.config['testnet']:
            self.exchange.set_sandbox_mode(True)

    def verify_ip(self):
        """Verify IP address"""
        client_ip = request.remote_addr
        if not SecurityConfig.validate_ip(client_ip, self.config['allowed_ips']):
            error_msg = f"Unauthorized IP address: {client_ip}"
            self.log_error(error_msg)
            raise ValueError(error_msg)

    def verify_request_signature(self, request_data):
        """Verify request signature"""
        if 'signature' not in request_data:
            raise ValueError("Missing signature in request")

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
        """Log errors"""
        log_event = LogEvent(
            self.name,
            'error',
            datetime.datetime.now(),
            error_message
        )
        log_event.write()

    def log_trade(self, trade_data, order_response):
        """Log trade details"""
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
        """Validate trading parameters"""
        required_fields = ['symbol', 'side', 'amount']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        data['symbol'] = data['symbol'].upper()
        if not data['symbol'].endswith('USDT'):
            data['symbol'] = f"{data['symbol']}USDT"

        market = self.exchange.market(data['symbol'])
        if float(data['amount']) < market['limits']['amount']['min']:
            raise ValueError(f"Amount {data['amount']} below minimum {market['limits']['amount']['min']}")

        return data

    def prepare_order_params(self, trade_data):
        """Prepare order parameters"""
        params = {
            'symbol': trade_data['symbol'],
            'type': 'MARKET',
            'side': trade_data['side'].upper(),
            'amount': float(trade_data['amount'])
        }

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

    def test_api_connection(self):
        """Test API Connection"""
        try:
            balance = self.exchange.fetch_balance()
            account_info = self.exchange.fapiPrivateGetAccount()
            
            connection_info = {
                "status": "success",
                "account_type": "testnet" if self.config['testnet'] else "live",
                "total_balance_usdt": balance['USDT']['total'] if 'USDT' in balance else 0,
                "available_balance_usdt": balance['USDT']['free'] if 'USDT' in balance else 0,
                "position_initial_margin": account_info.get('totalInitialMargin', 0),
                "unrealized_pnl": account_info.get('totalUnrealizedProfit', 0)
            }
            
            return connection_info

        except Exception as e:
            error_msg = f"Connection Error: {str(e)}"
            self.log_error(error_msg)
            return {"status": "failed", "error": error_msg}

    def execute_trade(self, trade_data):
        """Execute trade"""
        try:
            order_params = self.prepare_order_params(trade_data)
            order = self.exchange.create_order(**order_params)
            
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
            self.verify_ip()
            data = self.validate_data()
            self.verify_request_signature(data)
            trade_data = self.validate_trading_params(data)
            order = self.execute_trade(trade_data)
            self.log_trade(trade_data, order)
            return order

        except ValueError as e:
            self.log_error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            self.log_error(f"Error in BinanceFutures action: {str(e)}")
            raise