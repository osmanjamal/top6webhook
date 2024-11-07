# initialize our Flask application
from logging import getLogger, DEBUG
from flask import Flask, request, jsonify, render_template, Response
from commons import VERSION_NUMBER, LOG_LOCATION
from components.actions.base.action import am
from components.events.base.event import em
from components.logs.log_event import LogEvent
from components.schemas.trading import Order, Position
from utils.log import get_logger
from utils.register import register_action, register_event, register_link

from utils.config_manager import ConfigManager
config_manager = ConfigManager()
# register actions, events, links
from settings import REGISTERED_ACTIONS, REGISTERED_EVENTS, REGISTERED_LINKS

registered_actions = [register_action(action) for action in REGISTERED_ACTIONS]
registered_events = [register_event(event) for event in REGISTERED_EVENTS]
registered_links = [register_link(link, em, am) for link in REGISTERED_LINKS]

app = Flask(__name__)

# configure logging
logger = get_logger(__name__)

# Define schema list (important - keep this!)
schema_list = {
    'order': Order().as_json(),
    'position': Position().as_json()
}

@app.route("/", methods=["GET"])
def dashboard():
    if request.method == 'GET':
        try:
            with open('.gui_key', 'r') as key_file:
                gui_key = key_file.read().strip()
                if gui_key == request.args.get('guiKey', None):
                    action_list = am.get_all()
                    account_info = {}  # يمكن إضافة معلومات الحساب هنا
                    
                    return render_template(
                        template_name_or_list='dashboard.html',
                        schema_list=schema_list,
                        action_list=action_list,
                        event_list=registered_events,
                        version=VERSION_NUMBER,
                        account_info=account_info
                    )
                    
            return 'Access Denied - Invalid GUI Key', 401
            
        except FileNotFoundError:
            logger.warning('GUI key file not found. Open GUI mode detected.')
            return 'Access Denied - No GUI Key File', 401


@app.route("/webhook", methods=["POST"])
async def webhook():
    if request.method == 'POST':
        data = request.get_json()
        if data is None:
            logger.error(f'Error getting JSON data from request...')
            logger.error(f'Request data: {request.data}')
            logger.error(f'Request headers: {request.headers}')
            return 'Error getting JSON data from request', 400

        logger.info(f'Request Data: {data}')
        triggered_events = []
        for event in em.get_all():
            if event.webhook:
                if event.key == data['key']:
                    event.trigger(data=data)
                    triggered_events.append(event.name)

        if not triggered_events:
            logger.warning(f'No events triggered for webhook request {request.get_json()}')
        else:
            logger.info(f'Triggered events: {triggered_events}')

    return Response(status=200)

@app.route("/logs", methods=["GET"])
def get_logs():
    if request.method == 'GET':
        log_file = open(LOG_LOCATION, 'r')
        logs = [LogEvent().from_line(log) for log in log_file.readlines()]
        return jsonify([log.as_json() for log in logs])

@app.route("/event/active", methods=["POST"])
def activate_event():
    if request.method == 'POST':
        event_name = request.args.get('event', None)
        if event_name is None:
            return Response(f'Event name cannot be empty ({event_name})', status=404)
        try:
            event = em.get(event_name)
        except ValueError:
            return Response(f'Cannot find event with name: {event_name}', status=404)

        event.active = request.args.get('active', True) == 'true'
        logger.info(f'Event {event.name} active set to: {event.active}, via POST request')
        return {'active': event.active}

@app.route("/api/security/ip", methods=["GET", "POST"])
def manage_security_ip():
    if request.method == "GET":
        config = config_manager.load_config()
        return jsonify(config.get('security', {}).get('allowed_ips', []))
        
    elif request.method == "POST":
        try:
            data = request.get_json()
            ip_address = data.get('ip')
            if not ip_address:
                return "IP address required", 400
                
            config = config_manager.load_config()
            if 'security' not in config:
                config['security'] = {'allowed_ips': []}
                
            if ip_address not in config['security']['allowed_ips']:
                config['security']['allowed_ips'].append(ip_address)
                
            if config_manager.save_config(config):
                return jsonify({"status": "success", "message": f"Added IP {ip_address}"})
            return "Error adding IP", 500
            
        except Exception as e:
            logger.error(f"Error managing IP: {str(e)}")
            return str(e), 500


@app.route("/api/settings/api", methods=["POST"])
def update_api_settings():
    try:
        data = request.get_json()
        creds = config_manager.load_credentials()
        
        # تحديث إعدادات Binance
        creds['binance_futures'] = {
            "api_key": data.get('apiKey', ''),
            "api_secret": data.get('apiSecret', ''),
            "testnet": data.get('testnet', True),
            "allowed_ips": creds.get('binance_futures', {}).get('allowed_ips', [])
        }
        
        if config_manager.save_credentials(creds):
            return jsonify({"status": "success"})
        return "Error saving settings", 500
            
    except Exception as e:
        logger.error(f"Error updating API settings: {str(e)}")
        return str(e), 500



@app.route("/api/settings", methods=["GET"])
def get_settings():
    """الحصول على الإعدادات الحالية"""
    try:
        settings = {
            "api": config_manager.load_credentials().get('binance_futures', {}),
            "app": config_manager.load_config()
        }
        # إخفاء البيانات الحساسة
        if 'api_key' in settings['api']:
            settings['api']['api_key'] = '********'
        if 'api_secret' in settings['api']:
            settings['api']['api_secret'] = '********'
            
        return jsonify(settings)
    except Exception as e:
        return str(e), 500
# New API Endpoints
@app.route("/api/actions", methods=["GET"])
def get_actions():
    try:
        actions = [{"name": action.name, "linkedEvents": [e.name for e in em.get_all() if action in e._actions]} 
                  for action in am.get_all()]
        return jsonify(actions)
    except Exception as e:
        logger.error(f"Error getting actions: {str(e)}")
        return str(e), 500

@app.route("/api/events", methods=["GET"])
def get_events():
    try:
        events = [{"name": event.name, "key": event.key, "active": event.active} 
                 for event in em.get_all()]
        return jsonify(events)
    except Exception as e:
        logger.error(f"Error getting events: {str(e)}")
        return str(e), 500

@app.route("/api/account/info", methods=["GET"])
def get_account_info():
    try:
        return jsonify({
            "balance": 0.0,
            "marginLevel": 0,
            "availableBalance": 0.0
        })
    except Exception as e:
        logger.error(f"Error getting account info: {str(e)}")
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
