from flask import Flask, jsonify, request
import requests
import pika
import threading
import json
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

port = 5001
temperature_measure = "C"
city = "Lisboa"
url = f"http://10.151.101.126:{port}/"

# Configure logging
log_file_path = "/var/log/flask/lisboa_temperatures.log"
log_format = '%(h)s %(l)s %(u)s [%(t)s] "%(r)s" %(s)s %(b)s Headers: %(headers)s'

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
        record.headers = record.__dict__.get('headers', '-')  # Add headers to the format
        return super().format(record)
    


handler = RotatingFileHandler(log_file_path, maxBytes=10*1024*1024, backupCount=5)
handler.setFormatter(ApacheLogFormatter(log_format))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

def log_request(response):
    # Extract necessary data for Apache2 log format
    headers = dict(request.headers)  # Convert headers to a dictionary
    app.logger.info(
        '',
        extra={
            'ip': request.remote_addr,
            'request': f"{request.method} {request.path} {request.environ.get('SERVER_PROTOCOL')}",
            'status_code': response.status_code,
            'content_length': response.content_length or '-',
            'headers': json.dumps(headers),  # Store headers as a JSON string
        },
    )
    return response

# Apply log_request function after each request
app.after_request(log_request)

# Variável global para armazenar a última temperatura em Celsius recebida
latest_temperature_celsius = None

def callback_celsius(ch, method, properties, body):
    global latest_temperature_celsius
    # Decodifica a mensagem e atualiza a última temperatura em Celsius
    data = json.loads(body.decode())  # Converte de JSON para dicionário
    if data.get("type") == "C":  # Verifica se é temperatura em Celsius
        if data.get("city") == city:
            latest_temperature_celsius = data.get("value")
            print(f"Temperatura Celsius recebida: {latest_temperature_celsius} °C")

def consume_temperature_celsius():
    # Conecta ao RabbitMQ
    credentials = pika.PlainCredentials('myuser', 'mypassword')
    connection = pika.BlockingConnection(pika.ConnectionParameters('10.151.101.221', credentials=credentials))
    channel = connection.channel()

    # Declara um exchange do tipo 'fanout'
    channel.exchange_declare(exchange='temperaturas', exchange_type='fanout')

    # Cria uma fila exclusiva para este consumidor
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # Liga a fila ao exchange
    channel.queue_bind(exchange='temperaturas', queue=queue_name)

    # Configura um consumidor para a fila de temperaturas em Celsius
    channel.basic_consume(queue=queue_name, on_message_callback=callback_celsius, auto_ack=True)

    print('Aguardando mensagens de temperatura em Celsius...')
    channel.start_consuming()

@app.route('/', methods=['GET'])
def get_data():
    data = {'key': latest_temperature_celsius} if latest_temperature_celsius else {'key': 'No data received'}
    return jsonify(data)

if __name__ == '__main__':
    data = {"type": temperature_measure, "city" : city ,  "url": url}
    print(data)
    requests.post("http://10.151.101.80:5020/services", data=data)

    # Inicia o consumidor RabbitMQ em uma thread separada
    consumer_thread = threading.Thread(target=consume_temperature_celsius)
    consumer_thread.start()

    # Inicia o aplicativo Flask
    app.run(debug=True, port=port, use_reloader=False,host='0.0.0.0')
