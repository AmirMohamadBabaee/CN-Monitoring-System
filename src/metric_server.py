import socket
import types
import selectors
import logging
import json
from prometheus_client import Counter, Gauge, Histogram, start_http_server

HOST = '127.0.0.1'
PORT = 9999

class MetricServer:

    def __init__(self, server_name, server_ip='127.0.0.1', server_port=9999):
        self.server_name = server_name
        self.server_ip = server_ip
        self.server_port = server_port
        self.sel = selectors.DefaultSelector()
        self.logger = self.init_logger()
        self.main_socket = self.init_socket()
        self.prometues_metrics = self.init_prometheus_metrics()

    def init_logger(self):
        # init logger object
        logger = logging.getLogger(__name__)

        # declare console handler for logger object
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # declare logging format of logger object
        console_format = logging.Formatter('[%(asctime)s][%(process)s][%(levelname)s] - %(name)s - %(message)s')                        
        console_handler.setFormatter(console_format)

        logger.addHandler(console_handler)

        logger.debug('logger object created.')
        return logger

    def init_socket(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((self.server_ip, self.server_port))
        lsock.listen()
        self.logger.info(f'listen on {(self.server_ip, self.server_port)}')
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)
        return lsock

    def run(self):
        
        try:
            start_http_server(8000)
            while True:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        self.service_connection(key, mask)
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.sel.close()

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print(f"Accepted connection from {addr}")
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)

    def service_connection(self, key, mask):
            
        try:

            sock = key.fileobj
            data = key.data

            if mask & selectors.EVENT_READ:

                recv_data = sock.recv(1024)  # Should be ready to read
                
                if recv_data:
                    data.outb += recv_data

            if mask & selectors.EVENT_WRITE:
                
                if data.outb:

                    # Acknowledge Receive of data to agents
                    print(f"Echoing {len(data.outb)} byte received from {data.addr}")
                    sock.send(f'{len(data.outb)}'.encode('utf-8'))  # Should be ready to write
                    print(f'Closing current socket {data.addr}')
                    self.sel.unregister(sock)
                    sock.close()

                    self.load_metrics(data.outb)

        except ConnectionResetError as e:
            print(f'Closing current socket {data.addr}')
            self.sel.unregister(sock)
            sock.close()
            print(e)
        except socket.timeout as e:
            print(f'Closing current socket {data.addr}')
            self.sel.unregister(sock)
            sock.close()
            print(e)

    def load_metrics(self, metrics_json_encoded):
        
        metrics_json = metrics_json_encoded.decode('utf-8')
        metrics = json.loads(metrics_json)
        # print(f'metrics: {metrics}')
        self.update_prometheus_metrics(metrics)

    def init_prometheus_metrics(self):

        prometheus_metrics = dict()

        prometheus_metrics['cpu_utilization_percent']  = Gauge('cpu_utilization_percent', 'current CPU utilization', ['agent_name'])
        prometheus_metrics['cpu_frequency_average']    = Histogram('cpu_frequency_average', 'current average of CPU frequency of all cores', ['agent_name'])
        prometheus_metrics['cpu_temperature']          = Histogram('cpu_temperature', 'current temperature of acpitz (CPU)', ['agent_name'])
        prometheus_metrics['cpu_fan_speed']            = Histogram('cpu_fan_speed', 'current CPU fan speed in RPM', ['agent_name'])

        prometheus_metrics['memory_usage_percent']     = Gauge('memory_usage_percent', 'current memory usage', ['agent_name'])
        prometheus_metrics['memory_usage_bytes']       = Histogram('memory_usage_bytes', 'current used memory bytes', ['agent_name'])

        prometheus_metrics['swap_usage_percent']       = Gauge('swap_usage_percent', 'current swap usage', ['agent_name'])
        prometheus_metrics['swap_usage_bytes']         = Histogram('swap_usage_bytes', 'current used swap bytes', ['agent_name'])

        prometheus_metrics['net_packet_sent_count']    = Gauge('net_packet_sent', 'current number of sent packets', ['agent_name'])
        prometheus_metrics['net_packet_rcvd_count']    = Gauge('net_packet_rcvd', 'current number of received packets', ['agent_name'])
        prometheus_metrics['net_connections_number']   = Gauge('net_connections', 'current number of net connections of inet protocol', ['agent_name'])

        prometheus_metrics['battery_percent']          = Gauge('battery_percent', 'current percentage of battery power', ['agent_name'])

        return prometheus_metrics

    def update_prometheus_metrics(self, metrics):

        agent_name = metrics['agent_name']

        self.prometues_metrics['cpu_utilization_percent'].labels(agent_name).set(metrics['cpu_utilization_percent'])
        self.prometues_metrics['cpu_frequency_average'].labels(agent_name).observe(metrics['cpu_frequency_average'])
        self.prometues_metrics['cpu_temperature'].labels(agent_name).observe(metrics['cpu_temperature'])
        self.prometues_metrics['cpu_fan_speed'].labels(agent_name).observe(metrics['cpu_fan_speed'])

        self.prometues_metrics['memory_usage_percent'].labels(agent_name).set(metrics['memory_usage_percent'])
        self.prometues_metrics['memory_usage_bytes'].labels(agent_name).observe(metrics['memory_usage_bytes'])

        self.prometues_metrics['swap_usage_percent'].labels(agent_name).set(metrics['swap_usage_percent'])
        self.prometues_metrics['swap_usage_bytes'].labels(agent_name).observe(metrics['swap_usage_bytes'])

        self.prometues_metrics['net_packet_sent_count'].labels(agent_name).set(metrics['net_packet_sent_count'])
        self.prometues_metrics['net_packet_rcvd_count'].labels(agent_name).set(metrics['net_packet_rcvd_count'])
        self.prometues_metrics['net_connections_number'].labels(agent_name).set(metrics['net_connections_number'])
        
        self.prometues_metrics['battery_percent'].labels(agent_name).set(metrics['battery_percent'])


if __name__ == "__main__":
    ms = MetricServer('my metric server')
    ms.run()