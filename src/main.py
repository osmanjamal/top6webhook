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

# register actions, events, links
from settings import REGISTERED_ACTIONS, REGISTERED_EVENTS, REGISTERED_LINKS

registered_actions = [register_action(action) for action in REGISTERED_ACTIONS]
registered_events = [register_event(event) for event in REGISTERED_EVENTS]
registered_links = [register_link(link, em, am) for link in REGISTERED_LINKS]

app = Flask(__name__)

# configure logging
logger = get_logger(__name__)

schema_list = {
    'order': Order().as_json(),
    'position': Position().as_json()
}


@app.route("/", methods=["GET"])
def dashboard():
    if request.method == 'GET':
        try:
            # التحقق من وجود وصحة مفتاح واجهة المستخدم
            with open('.gui_key', 'r') as key_file:
                gui_key = key_file.read().strip()
                if gui_key == request.args.get('guiKey', None):
                    pass
                else:
                    logger.warning('Invalid GUI key provided')
                    return 'Access Denied', 401

        except FileNotFoundError:
            logger.warning('GUI key file not found. Open GUI mode detected.')

        try:
            # تحضير بيانات لوحة التحكم
            action_list = am.get_all()
            return render_template(
                template_name_or_list='dashboard.html',
                schema_list=schema_list,
                action_list=action_list,
                event_list=registered_events,
                version=VERSION_NUMBER
            )
        except Exception as e:
            logger.error(f'Error rendering dashboard: {str(e)}')
            return str(e), 500



@app.route("/webhook", methods=["POST"])
async def webhook():
    if request.method == 'POST':
        try:
            # استلام وفحص البيانات
            data = request.get_json()
            if data is None:
                logger.error('Error getting JSON data from request...')
                logger.error(f'Request data: {request.data}')
                logger.error(f'Request headers: {request.headers}')
                return 'Error getting JSON data from request', 400

            logger.info(f'Request Data: {data}')

            # التحقق من وجود المفتاح
            if 'key' not in data:
                logger.error('Missing key in webhook data')
                return 'Missing key in webhook data', 400

            # معالجة الأحداث
            triggered_events = []
            try:
                for event in em.get_all():
                    if event.webhook and event.key == data['key']:
                        await event.trigger(data=data)
                        triggered_events.append(event.name)
                        logger.info(f'Successfully triggered event: {event.name}')

                if not triggered_events:
                    logger.warning(f'No events triggered for webhook request {data}')
                else:
                    logger.info(f'Triggered events: {triggered_events}')

            except Exception as e:
                logger.error(f'Error triggering events: {str(e)}')
                return str(e), 500

            # تسجيل نجاح العملية
            log_event = LogEvent(
                'Webhook',
                'webhook_received',
                None,
                f'Successfully processed webhook for events: {", ".join(triggered_events)}'
            )
            log_event.write()

            return Response(status=200)

        except Exception as e:
            logger.error(f'Unexpected error in webhook endpoint: {str(e)}')
            return str(e), 500


@app.route("/logs", methods=["GET"])
def get_logs():
    if request.method == 'GET':
        try:
            with open(LOG_LOCATION, 'r') as log_file:
                logs = [LogEvent().from_line(log) for log in log_file.readlines()]
                return jsonify([log.as_json() for log in logs])
        except Exception as e:
            logger.error(f'Error retrieving logs: {str(e)}')
            return str(e), 500



@app.route("/event/active", methods=["POST"])
def activate_event():
    if request.method == 'POST':
        # get query parameters
        event_name = request.args.get('event', None)

        # if event name is not provided, or cannot be found, 404
        if event_name is None:
            return Response(f'Event name cannot be empty ({event_name})', status=404)
        try:
            event = em.get(event_name)
        except ValueError:
            return Response(f'Cannot find event with name: {event_name}', status=404)

        # set event to active or inactive, depending on current state
        event.active = request.args.get('active', True) == 'true'
        logger.info(f'Event {event.name} active set to: {event.active}, via POST request')
        return {'active': event.active}


if __name__ == '__main__':
    # في وضع التطوير، نستخدم debug=True
    logger.info('Starting application in development mode...')
    app.run(host='0.0.0.0', port=5000, debug=True)