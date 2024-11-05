from components.actions.base.action import Action
from components.config.security import SecurityConfig
from components.logs.log_event import LogEvent
import ccxt
import datetime
import hmac
import hashlib
import time
from flask import request

class BinanceFutures(Action):
    def __init__(self):
        super().__init__()
        self.config = SecurityConfig.load_credentials()['binance_futures']
        self.setup_exchange()

    
    def setup_exchange(self):
        """Initialize Binance Futures connection"""
        try:
            print("\nDetailed Debug Information:")
            print(f"API Key (first 5 chars): {self.config['api_key'][:5]}...")
            print(f"API Secret (first 5 chars): {self.config['api_secret'][:5]}...")
            print(f"TestNet Mode: {self.config['testnet']}")
            print(f"Allowed IPs: {self.config['allowed_ips']}")
            
            print("\nSetting up exchange connection...")
            
            # تكوين محسن للاتصال
            exchange_config = {
                'apiKey': self.config['api_key'].strip(),
                'secret': self.config['api_secret'].strip(),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000,
                    'warnOnFetchOHLCVLimitArgument': True,
                    'createMarketBuyOrderRequiresPrice': False
                }
            }

            self.exchange = ccxt.binance(exchange_config)

            if self.config['testnet']:
                print("Setting up TestNet mode...")
                self.exchange.set_sandbox_mode(True)
            else:
                print("Setting up Live mode...")

            # اختبار أساسي للوقت
            print("\n1. Testing server time...")
            serverTime = self.exchange.publicGetTime()
            print(f"Server Time Response: {serverTime}")

            # اختبار معلومات التداول العامة
            print("\n2. Testing public endpoints...")
            try:
                exchangeInfo = self.exchange.fapiPublicGetExchangeInfo()
                print("Successfully accessed public futures endpoints")
            except Exception as e:
                print(f"Error accessing public endpoints: {str(e)}")
                raise

            # اختبار الوصول للحساب
            print("\n3. Testing account access...")
            try:
                print("Attempting to fetch account balance...")
                balance = self.exchange.fapiPrivateV2GetBalance()
                print("Successfully fetched balance")
                print(f"Balance response: {balance}")
            except Exception as e:
                print(f"\nError accessing account: {str(e)}")
                print("\nPossible solutions:")
                print("1. Verify API key permissions:")
                print("   - Enable Reading")
                print("   - Enable Futures")
                print("   - Enable Spot & Margin Trading")
                print("2. Check IP restrictions:")
                print(f"   - Your current IP: 31.218.96.211")
                print("3. Ensure Futures account is activated:")
                print("   - Go to Binance Futures")
                print("   - Complete account activation if needed")
                print("   - Transfer some USDT to Futures wallet")
                raise

            # اختبار معلومات الحساب
            print("\n4. Testing futures account details...")
            try:
                futuresAccount = self.exchange.fapiPrivateV2GetAccount()
                print("Successfully fetched account details")
                
                wallet_balance = float(futuresAccount.get('totalWalletBalance', 0))
                unrealized_pnl = float(futuresAccount.get('totalUnrealizedProfit', 0))
                margin_balance = float(futuresAccount.get('totalMarginBalance', 0))
                
                print("\nAccount Summary:")
                print(f"Wallet Balance: {wallet_balance:.2f} USDT")
                print(f"Unrealized PNL: {unrealized_pnl:.2f} USDT")
                print(f"Margin Balance: {margin_balance:.2f} USDT")
                
                return {
                    "status": "success",
                    "account_type": "live",
                    "wallet_balance": wallet_balance,
                    "unrealized_pnl": unrealized_pnl,
                    "margin_balance": margin_balance
                }
                
            except Exception as e:
                print(f"\nError accessing futures account: {str(e)}")
                raise

        except Exception as e:
            print(f"\nDetailed Error in setup_exchange: {str(e)}")
            if "Invalid API-key" in str(e):
                print("\nAPI Configuration Issue:")
                print("1. Go to Binance.com -> API Management")
                print("2. Delete existing API key")
                print("3. Create new API key with these settings:")
                print("   [✓] Enable Reading")
                print("   [✓] Enable Spot & Margin Trading")
                print("   [✓] Enable Futures")
                print("4. Add IP restriction:")
                print("   - Add: 31.218.96.211")
                print("5. Update credentials using:")
                print("   python -m src.utils.manage_security set-credentials")
            raise

        except Exception as e:
            print(f"\nDetailed Error in setup_exchange: {str(e)}")
            if "Invalid API-key" in str(e):
                print("\nAPI Permissions Issue:")
                print("1. Check IP whitelist on Binance")
                print("2. Verify API permissions are enabled")
                print("3. Ensure Futures trading is activated")
            raise

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
        message = (
            f"Trade executed - Symbol: {trade_data['symbol']}, "
            f"Side: {trade_data['side']}, "
            f"Order ID: {order_response['id']}"
        )
        log_event = LogEvent(
            self.name,
            'trade',
            datetime.datetime.now(),
            message
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
        min_amount = market['limits']['amount']['min']
        if float(data['amount']) < min_amount:
            raise ValueError(
                f"Amount {data['amount']} below minimum {min_amount}"
            )
        return data

    def execute_trade(self, trade_data):
        """Execute trade"""
        try:
            order_params = {
                'symbol': trade_data['symbol'],
                'type': 'MARKET',
                'side': trade_data['side'].upper(),
                'amount': float(trade_data['amount'])
            }
            
            order = self.exchange.create_order(**order_params)

            if 'stopLoss' in trade_data:
                sl_side = 'sell' if trade_data['side'].lower() == 'buy' else 'buy'
                self.exchange.create_order(
                    symbol=trade_data['symbol'],
                    type='STOP_MARKET',
                    side=sl_side,
                    amount=float(trade_data['amount']),
                    price=float(trade_data['stopLoss'])
                )

            if 'takeProfit' in trade_data:
                tp_side = 'sell' if trade_data['side'].lower() == 'buy' else 'buy'
                self.exchange.create_order(
                    symbol=trade_data['symbol'],
                    type='TAKE_PROFIT_MARKET',
                    side=tp_side,
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

    def test_api_connection(self):
        """Test API connection and fetch account info"""
        try:
            print("\nTesting API Connection...")
            print(f"Current IP: {request.remote_addr if request else 'Not in request context'}")
            
            # Test basic connection
            print("\n1. Testing basic connectivity...")
            time = self.exchange.fetch_time()
            print(f"Server time: {datetime.datetime.fromtimestamp(time/1000)}")
            
            # Test futures account access
            print("\n2. Testing futures account access...")
            balance = self.exchange.fetch_balance()
            print(f"Raw balance response: {balance}")
            
            # Get detailed account info
            print("\n3. Getting account details...")
            account = self.exchange.fapiPrivateV2GetAccount()
            print(f"Raw account response: {account}")
            
            return {
                "status": "success",
                "account_type": "testnet" if self.config['testnet'] else "live",
                "total_balance_usdt": balance.get('USDT', {}).get('total', 0),
                "available_balance_usdt": balance.get('USDT', {}).get('free', 0),
                "position_initial_margin": account.get('totalInitialMargin', 0),
                "unrealized_pnl": account.get('totalUnrealizedProfit', 0)
            }
            
        except ccxt.NetworkError as e:
            error_msg = f"Network Error: {str(e)}"
            print(f"\nNetwork Error Details: {error_msg}")
            return {"status": "failed", "error": error_msg}
            
        except ccxt.ExchangeError as e:
            error_msg = f"Exchange Error: {str(e)}"
            print(f"\nExchange Error Details: {error_msg}")
            return {"status": "failed", "error": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            print(f"\nUnexpected Error Details: {error_msg}")
            return {"status": "failed", "error": error_msg}