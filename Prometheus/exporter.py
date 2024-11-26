from prometheus_client import start_http_server, Gauge
import random
import requests
from time import sleep
import time
import logging
import json

# Configure logging
# Configure logging for Wazuh
log_file_path = "/var/log/prometheus/prometheus.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_to_wazuh_apache(service):
    """Log in an Apache2-compatible format with DDoS alert details."""
    # Apache2 log fields
    # http://10.151.101.126:5001/ remove http:// and / from the service and port
    service_ip = service.split("://")[1].split(":")[0]
    datacenter = "Some"
    if service_ip == "10.151.101.126":
        datacenter = "Lisboa"
    elif service_ip == "10.151.101.121":
        datacenter = "Porto"
    remote_log_name = "MyHost"         # Placeholder
    authenticated_user = "example[12345]"      # Placeholder
    timestamp = time.strftime('%b %d %H:%M:%S', time.gmtime())

    # Construct the log entry Dec 25 20:45:02 admin admin: Datacenter 'Lisboa' is being DDos attacked from '192.168.1.100'
    log_entry = f'{timestamp} {remote_log_name} {authenticated_user}: Datacenter {datacenter} is being DDoS attacked from {service_ip}'


    # Write to the log
    logging.info(log_entry)




# Create a metric to track health status
label_location = ['Lisboa','Lisboa','Porto','Porto']
health_metric = Gauge('service_health', 'Health status of the service', ['service', 'alive','location'])
response_time_metric = Gauge('service_response_time_seconds', 'Average response time of the service in seconds', ['service', 'location'])
#Create services array – these are examples
SERVICES=['http://10.151.101.126:5001/','http://10.151.101.126:5155/','http://10.151.101.121:5003/','http://10.151.101.121:5000/']

# Dictionary to store the accumulated response times and request counts for each service
# Dictionary to store the current response times for each service
current_response_time = {service: 0 for service in SERVICES}

# Threshold for detecting a sudden increase (e.g., 50% increase)
RESPONSE_TIME_THRESHOLD = 1.5


def check_service_health():
    for i in range(len(SERVICES)):
        service = SERVICES[i]

        try:
            # Track response times for the first 10 requests
            total_response_time = 0
            proxy_detected = False
            for _ in range(10):
                start_time = time.time()  # Start time of the request
                response = requests.get(service)
                end_time = time.time()  # End time of the request
                total_response_time += (end_time - start_time)  # Accumulate response time
                print(f"Request to {service} took {end_time - start_time:.4f} seconds")
            proxy_headers = ['Via', 'X-Forwarded-For', 'Forwarded', 'X-Forwarded-Host']
            if any(header in response.headers for header in proxy_headers):
                proxy_detected = True
                print(f"Proxy detected for {service}")
            # Calculate average response time
            avg_response_time = total_response_time / 10
            print(f"Average response time for {service}: {avg_response_time:.4f} seconds")

            # Compare the new response time with the stored one
            if current_response_time[service] > 0:  # Ensure we have a previous value
                if avg_response_time > current_response_time[service] * RESPONSE_TIME_THRESHOLD:
                    alert_message = f"ALERTA de DDoS: Aumento significativo no tempo de resposta para {service}! ({current_response_time[service]:.4f} -> {avg_response_time:.4f} segundos)"
                    print(alert_message)
                    log_to_wazuh_apache(
                        service=service,
                    )
                else:
                    # Update the current response time with the new value
                    current_response_time[service] = avg_response_time
            else:
                current_response_time[service] = avg_response_time

            # Update Prometheus metrics
            health_metric.labels(service=service, alive='Up', location=label_location[i])
            response_time_metric.labels(service=service, location=label_location[i]).set(avg_response_time)

        except requests.exceptions.RequestException as e:
            print(service + " Down")
            health_metric.labels(service=service, alive='Down', location=label_location[i])


if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(8000)
    # Simulate health checks periodically
    while True:
        check_service_health()
        sleep(10)
