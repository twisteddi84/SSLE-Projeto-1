import time
import random
import pika
import json  # Importa o módulo JSON

# Função para medir a temperatura em Celsius
def medir_temperatura_celsius():
    return round(random.uniform(15.0, 30.0), 2)

# Função para converter de Celsius para Fahrenheit
def celsius_para_fahrenheit(celsius):
    return round((celsius * 9/5) + 32, 2)

# Função principal do sensor de temperatura simulado
def sensor_temperatura_simulado():
    # Conexão com o RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # Declara um exchange do tipo 'fanout'
    channel.exchange_declare(exchange='temperaturas', exchange_type='fanout')

    try:
        while True:
            celsius = medir_temperatura_celsius()  # Mede a temperatura em Celsius
            fahrenheit = celsius_para_fahrenheit(celsius)  # Converte para Fahrenheit

            # Dicionário para Celsius para Lisboa
            temperatura_celsius_lisboa = {
                "type": "C",
                "value": celsius
                , "city": "Lisboa"
            }

            temperatura_celsius_Porto = {
                "type": "C",
                "value": celsius + 1
                , "city": "Porto"
            }

            # Dicionário para Fahrenheit
            temperatura_fahrenheit = {
                "type": "F",
                "value": fahrenheit
            }

            # Converte os dicionários para JSON
            message_celsius_lisboa = json.dumps(temperatura_celsius_lisboa)
            message_fahrenheit = json.dumps(temperatura_fahrenheit)
            message_celsius_porto = json.dumps(temperatura_celsius_Porto)

            # Publica a temperatura na exchange 'temperaturas'
            channel.basic_publish(exchange='temperaturas', routing_key='', body=message_celsius_lisboa)
            print(f"Temperatura Celsius Lisboa enviada: {temperatura_celsius_lisboa}")

            channel.basic_publish(exchange='temperaturas', routing_key='', body=message_celsius_porto)
            print(f"Temperatura Celsius Porto enviada: {temperatura_celsius_Porto}")

            # Publica a temperatura na exchange 'temperaturas'
            channel.basic_publish(exchange='temperaturas', routing_key='', body=message_fahrenheit)
            print(f"Temperatura Fahrenheit enviada: {temperatura_fahrenheit}")

            time.sleep(10)  # Aguarda 30 segundos antes da próxima medição
    except KeyboardInterrupt:
        print("\nSimulação encerrada.")
    finally:
        connection.close()  # Fecha a conexão com o RabbitMQ

if __name__ == "__main__":
    sensor_temperatura_simulado()  # Inicia o sensor de temperatura