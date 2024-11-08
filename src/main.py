import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from functools import wraps
import time
import hmac
import hashlib
import psutil

# Flask imports
from flask import Flask, request, jsonify, render_template, Response
from flask_sqlalchemy import SQLAlchemy
from models.database import db, DashboardData, Position, Event, Action

# Project imports
from commons import VERSION_NUMBER, LOG_LOCATION
from components.actions.base.action import am
from components.events.base.event import em
from components.logs.log_event import LogEvent
from components.schemas.trading import Order, Position
from utils.log import get_logger
from utils.register import register_action, register_event, register_link, register_manager, RegisterManager
from utils.config_manager import ConfigManager
from utils.binance_manager import BinanceManager

# Settings import
from settings import REGISTERED_ACTIONS, REGISTERED_EVENTS, REGISTERED_LINKS

# Initialize Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dashboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# إنشاء قاعدة البيانات
with app.app_context():
    db.create_all()

# Initialize logging
logger = get_logger(__name__)

# Initialize managers
config_manager = ConfigManager()
binance_manager = BinanceManager(config_manager)

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
REQUIRED_PERMISSIONS = ['futures']

# Schema definitions
schema_list = {
    'order': Order().as_json(),
    'position': Position().as_json()
}

# Register components
def initialize_components():
    """تهيئة وتسجيل المكونات"""
    try:
        logger.info("Initializing components...")
        
        # تسجيل الإجراءات
        registered_actions = set()  # لتجنب التكرار
        for action in REGISTERED_ACTIONS:
            if action not in registered_actions:
                registered = register_action(action)
                if registered:
                    logger.info(f"Action registered: {action}")
                    registered_actions.add(action)

        # تسجيل الأحداث
        registered_events = set()  # لتجنب التكرار
        for event in REGISTERED_EVENTS:
            if event not in registered_events:
                registered = register_event(event)
                if registered:
                    logger.info(f"Event registered: {event}")
                    registered_events.add(event)

        # تسجيل الروابط
        for link in REGISTERED_LINKS:
            action_name, event_name = link
            if action_name in registered_actions and event_name in registered_events:
                register_link(link, em, am)

        logger.info("Components initialization completed")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing components: {str(e)}")
        return False
# Decorators
def require_api_key(f):
    """للتأكد من وجود مفاتيح API قبل تنفيذ العملية"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not binance_manager.exchange:
            return jsonify({
                "status": "error",
                "message": "API connection not configured",
                "code": "API_NOT_CONFIGURED"
            }), 403
        return f(*args, **kwargs)
    return decorated

def verify_ip(f):
    """للتحقق من عنوان IP"""
    @wraps(f)
    def decorated(*args, **kwargs):
        client_ip = request.remote_addr
        if not config_manager.is_ip_allowed(client_ip):
            logger.warning(f"Unauthorized access attempt from IP: {client_ip}")
            return jsonify({
                "status": "error",
                "message": "IP not authorized",
                "code": "IP_NOT_AUTHORIZED"
            }), 403
        return f(*args, **kwargs)
    return decorated

def rate_limit(limit: int = 10, per: int = 60):
    """للتحكم في عدد الطلبات"""
    def decorator(f):
        requests = {}
        @wraps(f)
        def decorated(*args, **kwargs):
            now = time.time()
            client_ip = request.remote_addr
            
            # تنظيف الطلبات القديمة
            requests[client_ip] = [req for req in requests.get(client_ip, []) 
                                 if now - req < per]
            
            if len(requests.get(client_ip, [])) >= limit:
                return jsonify({
                    "status": "error",
                    "message": "Rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED"
                }), 429
                
            requests.setdefault(client_ip, []).append(now)
            return f(*args, **kwargs)
        return decorated
    return decorator

# API Routes for Trading Operations

@app.route("/api/binance/order", methods=["POST"])
@require_api_key
@verify_ip
@rate_limit()
async def create_binance_order():
    """إنشاء أمر تداول جديد"""
    try:
        data = request.get_json()
        validation_result = validate_order_data(data)
        
        if not validation_result['valid']:
            return jsonify({
                "status": "error",
                "message": validation_result['message']
            }), 400

        # التحقق من المخاطر
        risk_check = check_order_risk(data)
        if not risk_check['allowed']:
            return jsonify({
                "status": "error",
                "message": risk_check['message']
            }), 400

        # تجهيز الرمز
        symbol = data['symbol'].upper()
        if not symbol.endswith('USDT'):
            symbol = f"{symbol}USDT"

        # إنشاء الأمر
        order = await create_order_with_safety({
            'symbol': symbol,
            'order_type': data.get('type', 'MARKET'),
            'side': data['side'].upper(),
            'amount': float(data['amount']),
            'leverage': data.get('leverage', 10),
            'stopLoss': data.get('stopLoss'),
            'takeProfit': data.get('takeProfit')
        })

        logger.info(f"Order created successfully: {symbol} {data['side']} {data['amount']}")
        return jsonify({
            "status": "success",
            "order": order
        })

    except Exception as e:
        error_msg = f"Error creating order: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route("/api/binance/positions", methods=["GET"])
@require_api_key
@verify_ip
def get_positions():
    """الحصول على المراكز المفتوحة"""
    try:
        positions = binance_manager.get_open_positions()
        return jsonify({
            "status": "success",
            "positions": positions,
            "count": len(positions),
            "lastUpdate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    except Exception as e:
        error_msg = f"Error fetching positions: {str(e)}"
        logger.error(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route("/webhook", methods=["POST"])
async def webhook():
    """معالجة طلبات Webhook"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                logger.error('Error getting JSON data from request')
                logger.error(f'Request data: {request.data}')
                logger.error(f'Request headers: {request.headers}')
                return jsonify({
                    "status": "error",
                    "message": "Invalid JSON data"
                }), 400

            logger.info(f'Webhook received: {data}')

            # التحقق من المفتاح
            if 'key' not in data:
                return jsonify({
                    "status": "error",
                    "message": "Missing webhook key"
                }), 400

            # معالجة الأحداث
            triggered_events = []
            for event in em.get_all():
                if event.webhook and event.key == data['key']:
                    try:
                        await event.trigger(data=data)
                        triggered_events.append(event.name)
                        logger.info(f'Event triggered successfully: {event.name}')
                    except Exception as event_error:
                        logger.error(f'Error triggering event {event.name}: {str(event_error)}')

            if not triggered_events:
                logger.warning(f'No events triggered for webhook request')
                return jsonify({
                    "status": "warning",
                    "message": "No matching events found"
                }), 200

            return jsonify({
                "status": "success",
                "triggered_events": triggered_events
            })

        except Exception as e:
            error_msg = f"Error processing webhook: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500

    return Response(status=200)

# Trading Helper Functions
async def create_order_with_safety(data: dict) -> dict:
    """إنشاء أمر مع إجراءات السلامة"""
    try:
        # التحقق من توفر الرصيد
        balance = binance_manager.get_balance()
        available_balance = float(balance.get('free', {}).get('USDT', 0))
        
        order_value = float(data['amount'])
        if order_value > available_balance:
            raise ValueError(f"Insufficient balance. Available: {available_balance} USDT")

        # إنشاء الأمر
        order = binance_manager.create_order(
            symbol=data['symbol'],
            order_type=data['order_type'],
            side=data['side'],
            amount=data['amount']
        )

        # إضافة وقف الخسارة
        if data.get('stopLoss'):
            sl_order = _create_stop_loss_order(data, order)
            logger.info(f"Stop loss order created: {sl_order['id']}")

        # إضافة هدف الربح
        if data.get('takeProfit'):
            tp_order = _create_take_profit_order(data, order)
            logger.info(f"Take profit order created: {tp_order['id']}")

        return order

    except Exception as e:
        logger.error(f"Error in create_order_with_safety: {str(e)}")
        raise

def _create_stop_loss_order(data: dict, main_order: dict) -> dict:
    """إنشاء أمر وقف الخسارة"""
    sl_side = 'sell' if data['side'].lower() == 'buy' else 'buy'
    return binance_manager.create_order(
        symbol=data['symbol'],
        order_type='STOP_MARKET',
        side=sl_side,
        amount=float(data['amount']),
        params={'stopPrice': float(data['stopLoss'])}
    )

def _create_take_profit_order(data: dict, main_order: dict) -> dict:
    """إنشاء أمر هدف الربح"""
    tp_side = 'sell' if data['side'].lower() == 'buy' else 'buy'
    return binance_manager.create_order(
        symbol=data['symbol'],
        order_type='TAKE_PROFIT_MARKET',
        side=tp_side,
        amount=float(data['amount']),
        params={'stopPrice': float(data['takeProfit'])}
    )

# Dashboard Routes

@app.route("/", methods=["GET"])
def dashboard():
    """صفحة لوحة التحكم الرئيسية"""
    if request.method == 'GET':
        try:
            with open('.gui_key', 'r') as key_file:
                gui_key = key_file.read().strip()
                if gui_key == request.args.get('guiKey', None):
                    account_info = _get_default_account_info()
                    
                    if binance_manager.exchange:
                        try:
                            account_data = binance_manager.get_account_info()
                            balance_info = binance_manager.get_balance()
                            positions = binance_manager.get_open_positions()
                            
                            account_info.update({
                                "total_balance": account_data.get("totalWalletBalance", 0),
                                "available_balance": balance_info.get("free", {}).get("USDT", 0),
                                "pnl": account_data.get("totalUnrealizedProfit", 0),
                                "margin_level": account_data.get("marginLevel", 0),
                                "positions": positions
                            })

                            # حفظ البيانات في قاعدة البيانات
                            dashboard_data = DashboardData(
                                total_balance=account_info["total_balance"],
                                available_balance=account_info["available_balance"],
                                pnl=account_info["pnl"],
                                margin_level=account_info["margin_level"],
                                api_status=True
                            )
                            db.session.add(dashboard_data)

                            # حفظ المراكز
                            for pos in positions:
                                position = Position(
                                    symbol=pos["symbol"],
                                    side=pos["side"],
                                    size=float(pos["size"]),
                                    entry_price=float(pos["entryPrice"]),
                                    current_price=float(pos["markPrice"]),
                                    pnl=float(pos["unrealizedPnl"]),
                                    dashboard_id=dashboard_data.id
                                )
                                db.session.add(position)

                            db.session.commit()

                        except Exception as e:
                            logger.error(f"Error fetching live data: {str(e)}")

                    # حفظ الأحداث والإجراءات
                    events = em.get_all()
                    for event in events:
                        event_data = Event(
                            name=event.name,
                            status="active" if event.active else "inactive",
                            key=event.key,
                            last_triggered=None  # يمكن تحديثه عند تشغيل الحدث
                        )
                        db.session.add(event_data)

                    actions = am.get_all()
                    for action in actions:
                        action_data = Action(
                            name=action.name,
                            status="active",
                            last_run=None  # يمكن تحديثه عند تنفيذ الإجراء
                        )
                        db.session.add(action_data)

                    db.session.commit()

                    return render_template(
                        'dashboard.html',
                        schema_list=schema_list,
                        action_list=actions,
                        event_list=events,
                        version=VERSION_NUMBER,
                        account_info=account_info,
                        api_status=binance_manager.exchange is not None,
                        connection_status="Connected" if binance_manager.exchange else "Disconnected"
                    )
                    
                return 'Access Denied - Invalid GUI Key', 401
                
        except FileNotFoundError:
            logger.warning('GUI key file not found. Open GUI mode detected.')
            return 'Access Denied - No GUI Key File', 401
        except Exception as e:
            logger.error(f"Error loading dashboard: {str(e)}")
            return 'Error loading dashboard', 500

@app.route("/api/dashboard/history", methods=["GET"])
def get_dashboard_history():
    """جلب سجل بيانات لوحة التحكم"""
    try:
        history = DashboardData.query.order_by(DashboardData.timestamp.desc()).limit(100).all()
        return jsonify([{
            "timestamp": item.timestamp,
            "total_balance": item.total_balance,
            "available_balance": item.available_balance,
            "pnl": item.pnl,
            "margin_level": item.margin_level,
            "api_status": item.api_status
        } for item in history])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard/positions/history", methods=["GET"])
def get_positions_history():
    """جلب سجل المراكز"""
    try:
        positions = Position.query.order_by(Position.timestamp.desc()).limit(100).all()
        return jsonify([{
            "timestamp": pos.timestamp,
            "symbol": pos.symbol,
            "side": pos.side,
            "size": pos.size,
            "entry_price": pos.entry_price,
            "current_price": pos.current_price,
            "pnl": pos.pnl
        } for pos in positions])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Dashboard API Routes

@app.route("/api/dashboard/status", methods=["GET"])
@verify_ip
def get_dashboard_status():
    """الحصول على حالة لوحة التحكم والمعلومات الحية"""
    try:
        if binance_manager.exchange:
            account_info = binance_manager.get_account_info()
            balance_info = binance_manager.get_balance()
            positions = binance_manager.get_open_positions()
            
            return jsonify({
                "status": "success",
                "data": {
                    "account": {
                        "total_balance": account_info.get("totalWalletBalance", 0),
                        "available_balance": balance_info.get("free", {}).get("USDT", 0),
                        "pnl": account_info.get("totalUnrealizedProfit", 0),
                        "margin_level": account_info.get("marginLevel", 0)
                    },
                    "positions": positions,
                    "connection": {
                        "status": "Connected",
                        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            })
        else:
            return jsonify({
                "status": "warning",
                "message": "API not connected",
                "data": {
                    "connection": {
                        "status": "Disconnected",
                        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            })

    except Exception as e:
        logger.error(f"Error getting dashboard status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/api/dashboard/settings", methods=["GET", "POST"])
@verify_ip
def manage_dashboard_settings():
    """إدارة إعدادات لوحة التحكم"""
    try:
        if request.method == "GET":
            return _get_dashboard_settings()
        elif request.method == "POST":
            return _update_dashboard_settings(request.get_json())

    except Exception as e:
        logger.error(f"Error managing dashboard settings: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/api/dashboard/positions/manage", methods=["POST"])
@require_api_key
@verify_ip
def manage_position():
    """إدارة المراكز المفتوحة"""
    try:
        data = request.get_json()
        action = data.get('action')
        symbol = data.get('symbol')
        
        if not action or not symbol:
            return jsonify({
                "status": "error",
                "message": "Missing required parameters"
            }), 400
            
        if action == 'close':
            return _close_position(symbol)
        elif action == 'modify':
            return _modify_position(symbol, data)
            
        return jsonify({
            "status": "error",
            "message": "Invalid action"
        }), 400
        
    except Exception as e:
        logger.error(f"Error managing position: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Helper Functions

def _get_default_account_info():
    """الحصول على معلومات الحساب الافتراضية"""
    return {
        "total_balance": 0,
        "available_balance": 0,
        "pnl": 0,
        "margin_level": 0,
        "positions": []
    }

def _get_dashboard_settings():
    """جلب إعدادات لوحة التحكم"""
    settings = config_manager.load_config()
    credentials = config_manager.load_credentials()
    
    # إخفاء المعلومات الحساسة
    if 'binance_futures' in credentials:
        credentials['binance_futures']['api_key'] = '********'
        credentials['binance_futures']['api_secret'] = '********'
    
    return jsonify({
        "status": "success",
        "settings": settings,
        "credentials": credentials
    })

def _update_dashboard_settings(data):
    """تحديث إعدادات لوحة التحكم"""
    if 'trading_settings' in data:
        config_manager.update_trading_config(data['trading_settings'])
    
    if 'security_settings' in data:
        config_manager.update_security_config(data['security_settings'])
    
    if 'api_settings' in data:
        success = config_manager.save_credentials({
            'binance_futures': data['api_settings']
        })
        if success:
            binance_manager.setup_connection()
    
    return jsonify({
        "status": "success",
        "message": "Settings updated successfully"
    })

def _close_position(symbol: str):
    """إغلاق مركز"""
    position = next((p for p in binance_manager.get_open_positions() 
                    if p['symbol'] == symbol), None)
    if position:
        close_side = 'sell' if position['side'] == 'buy' else 'buy'
        order = binance_manager.create_order(
            symbol=symbol,
            order_type='MARKET',
            side=close_side,
            amount=abs(float(position['size']))
        )
        return jsonify({
            "status": "success",
            "message": f"Position closed for {symbol}",
            "order": order
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"No open position found for {symbol}"
        }), 404

def _modify_position(symbol: str, data: dict):
    """تعديل مركز"""
    position = next((p for p in binance_manager.get_open_positions() 
                    if p['symbol'] == symbol), None)
    if position:
        if 'stopLoss' in data:
            binance_manager.modify_position(
                symbol=symbol,
                stop_loss=float(data['stopLoss'])
            )
        if 'takeProfit' in data:
            binance_manager.modify_position(
                symbol=symbol,
                take_profit=float(data['takeProfit'])
            )
        return jsonify({
            "status": "success",
            "message": f"Position modified for {symbol}"
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"No open position found for {symbol}"
        }), 404
    
# API Settings Routes

@app.route("/api/settings/api", methods=["GET", "POST"])
@verify_ip
def manage_api_settings():
    """إدارة إعدادات API"""
    if request.method == "POST":
        return save_api_settings(request.get_json())
    elif request.method == "GET":
        return get_api_settings()

@app.route("/api/settings/api/test", methods=["POST"])
@verify_ip
def test_api_connection():
    """اختبار اتصال API"""
    try:
        connection_test = binance_manager.test_connection()
        
        if connection_test.get('status') == 'success':
            return jsonify(connection_test)
        else:
            return jsonify({
                "status": "error",
                "message": connection_test.get('message', 'Connection test failed')
            }), 500
            
    except Exception as e:
        logger.error(f"Error testing API connection: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Error Handlers

@app.errorhandler(400)
def bad_request_error(error):
    """معالجة خطأ الطلب غير الصحيح"""
    logger.error(f"Bad request: {error}")
    return jsonify({
        "status": "error",
        "message": "Bad request",
        "details": str(error),
        "code": "BAD_REQUEST"
    }), 400

@app.errorhandler(401)
def unauthorized_error(error):
    """معالجة خطأ عدم التصريح"""
    logger.error(f"Unauthorized access: {error}")
    return jsonify({
        "status": "error",
        "message": "Unauthorized access",
        "code": "UNAUTHORIZED"
    }), 401

@app.errorhandler(403)
def forbidden_error(error):
    """معالجة خطأ الوصول المحظور"""
    logger.error(f"Forbidden access: {error}")
    return jsonify({
        "status": "error",
        "message": "Forbidden access",
        "code": "FORBIDDEN"
    }), 403

@app.errorhandler(404)
def not_found_error(error):
    """معالجة خطأ عدم العثور على الصفحة"""
    logger.error(f"Resource not found: {error}")
    return jsonify({
        "status": "error",
        "message": "Resource not found",
        "code": "NOT_FOUND"
    }), 404

@app.errorhandler(429)
def rate_limit_error(error):
    """معالجة خطأ تجاوز حد الطلبات"""
    logger.error(f"Rate limit exceeded: {error}")
    return jsonify({
        "status": "error",
        "message": "Too many requests",
        "code": "RATE_LIMIT_EXCEEDED"
    }), 429

@app.errorhandler(500)
def internal_server_error(error):
    """معالجة خطأ الخادم الداخلي"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "status": "error",
        "message": "Internal server error",
        "details": str(error),
        "code": "INTERNAL_ERROR"
    }), 500

# Helper Functions for API Settings

def save_api_settings(data: Dict) -> Response:
    """حفظ إعدادات API"""
    try:
        if not data or 'apiKey' not in data or 'apiSecret' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing API credentials"
            }), 400

        # حفظ بيانات الاعتماد
        credentials = {
            'binance_futures': {
                'api_key': data['apiKey'],
                'api_secret': data['apiSecret'],
                'testnet': data.get('testnet', False)
            }
        }
        
        # حفظ البيانات
        success = config_manager.save_credentials(credentials)
        if not success:
            return jsonify({
                "status": "error",
                "message": "Failed to save credentials"
            }), 500

        # إعادة تهيئة الاتصال مع Binance
        try:
            binance_manager.setup_connection()
            connection_test = binance_manager.test_connection()
            
            if connection_test.get('status') == 'success':
                return jsonify({
                    "status": "success",
                    "message": "API settings saved and connection tested successfully",
                    "data": connection_test
                })
            else:
                config_manager.clear_credentials()
                return jsonify({
                    "status": "error",
                    "message": connection_test.get('message', 'Connection test failed')
                }), 500
                
        except Exception as e:
            config_manager.clear_credentials()
            return jsonify({
                "status": "error",
                "message": f"Connection test failed: {str(e)}"
            }), 500

    except Exception as e:
        logger.error(f"Error saving API settings: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def get_api_settings() -> Response:
    """جلب إعدادات API"""
    try:
        credentials = config_manager.load_credentials()
        binance_config = credentials.get('binance_futures', {})
        
        # إخفاء المعلومات الحساسة
        if 'api_key' in binance_config:
            binance_config['api_key'] = '*' * 8
        if 'api_secret' in binance_config:
            binance_config['api_secret'] = '*' * 8
            
        return jsonify({
            "status": "success",
            "data": {
                "binance": binance_config
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting API settings: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Application Startup

def initialize_application():
    """تهيئة التطبيق عند بدء التشغيل"""
    try:
        # تهيئة المكونات
        initialize_components()
        
        # محاولة الاتصال مع Binance
        if binance_manager and binance_manager.exchange:
            logger.info("Binance connection established")
        else:
            logger.warning("No Binance credentials found or connection failed")

        # طباعة معلومات التشغيل
        logger.info(f"Server starting on port 5000")
        logger.info(f"Dashboard available at: http://127.0.0.1:5000")
        logger.info(f"Version: {VERSION_NUMBER}")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        initialize_application()
        
        # تشغيل التطبيق
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
