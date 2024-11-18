from flask import Flask, jsonify, request
import requests
import pika
import threading
import json
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

city = "Lisboa"

port = 5155
temperature_measure = "F"
url = f"http://10.151.101.126:{port}/"
# Configure logging
log_file_path = "/var/log/flask/lisboa_temperatures.log"
log_format = '%(h)s %(l)s %(u)s [%(t)s] "%(r)s" %(s)s %(b)s "%(referer)s" "%(user_agent)s"'

# Custom log formatter to match Apache2 log format
class ApacheLogFormatter(logging.Formatter):
    def format(self, record):
        record.h = record.__dict__.get('ip', '-')
        record.l = '-'
        record.u = '-'
        record.t = self.formatTime(record, "%d/%b/%Y:%H:%M:%S %z")
        record.r = record.__dict__.get('request', '-')
        record.s = record.__dict__.get('status_code', '-')
        record.b = record.__dict__.get('content_length', '-')
        record.referer = record.__dict__.get('referer', '-')
        record.user_agent = record.__dict__.get('user_agent', '-')
        return super().format(record)
    


handler = RotatingFileHandler(log_file_path, maxBytes=10*1024*1024, backupCount=5)
handler.setFormatter(ApacheLogFormatter(log_format))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

def log_request(response):
    headers = dict(request.headers)
    app.logger.info(
        '',
        extra={
            'ip': request.remote_addr,
            'request': f"{request.method} {request.path} {request.environ.get('SERVER_PROTOCOL')}",
            'status_code': response.status_code,
            'content_length': response.content_length or '-',
            'referer': headers.get('Referer', '-'),
            'user_agent': headers.get('User-Agent', '-'),
        },
    )
    return response

# Apply log_request function after each request
app.after_request(log_request)

# Global variable to hold the latest temperature in Fahrenheit received
latest_temperature_fahrenheit = None

def callback_fahrenheit(ch, method, properties, body):
    global latest_temperature_fahrenheit
    # Decode the message and update the latest temperature in Fahrenheit
    data = json.loads(body.decode())  # Convert from JSON to dictionary
    if data.get("type") == "F":  # Check if it's temperature in Fahrenheit
        if data.get("city") == "Lisboa":
            latest_temperature_fahrenheit = data.get("value")
            print(f"Temperatura Fahrenheit Lisboa recebida: {latest_temperature_fahrenheit} °F")

def consume_temperature_fahrenheit():
    # Connect to RabbitMQ
    credentials = pika.PlainCredentials('myuser', 'mypassword')
    connection = pika.BlockingConnection(pika.ConnectionParameters('10.151.101.221', credentials=credentials))
    channel = connection.channel()

    # Declare the exchange for temperatures
    channel.exchange_declare(exchange='temperaturas', exchange_type='fanout')

    # Create an exclusive queue for this consumer
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # Bind the queue to the exchange
    channel.queue_bind(exchange='temperaturas', queue=queue_name)

    # Set up a consumer for the Fahrenheit temperature queue
    channel.basic_consume(queue=queue_name, on_message_callback=callback_fahrenheit, auto_ack=True)

    print('Aguardando mensagens de temperatura em Fahrenheit...')
    channel.start_consuming()

@app.route('/', methods=['GET'])
def get_data():
    data = {'key': latest_temperature_fahrenheit} if latest_temperature_fahrenheit else {'key': 'No data received'}
    return jsonify(data)

if __name__ == '__main__':
    data = {"type": temperature_measure,"city":city , "url": url}
    print(data)
    requests.post("http://10.151.101.80:5020/services", data=data)

    # Start the RabbitMQ consumer in a separate thread
    consumer_thread = threading.Thread(target=consume_temperature_fahrenheit)
    consumer_thread.start()

    # Start the Flask app
    app.run(debug=True, port=port, use_reloader=False, host='0.0.0.0')
    