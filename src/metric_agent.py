#!/usr/bin/python3

import time
import psutil
import logging
import socket
import selectors
import types
import json

class MetricAgent:

    def __init__(self, agentName, server_ip='127.0.0.1', server_port=9999):
        
        self.agentName = agentName
        self.logger = self.init_logger()
        self.sel = selectors.DefaultSelector()
        self.server_ip = server_ip
        self.server_port = server_port
        self.messages = [b'I am Here']

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

    def __str__(self) -> str:
        print(f'[{self.agentName}]')

    # CPU Metrics

    def extract_cpu_utilization_percent(self):

        cpu_utilization_percent = psutil.cpu_percent()
        return cpu_utilization_percent

    def extract_cpu_frequency_average(self):

        cpu_freq = psutil.cpu_freq().current

        return cpu_freq

    def extract_cpu_temperature(self):

        try:
            cpu_temperature = psutil.sensors_temperatures().get('acpitz')[0][1]
            return cpu_temperature
        except:
            self.logger.error('Exception in extract_cpu_temperature', exc_info=True)

    def extract_cpu_fan_speed(self):

        try:
            cpu_fan_speed = psutil.sensors_fans().get('asus')[0][1]
            return cpu_fan_speed
        except: 
            self.logger.error('Exception in extract_cpu_fan_speed', exc_info=True)

    # Memory Metrics

    def extract_memory_usage_percent(self):

        memory_usage_percent = psutil.virtual_memory().percent
        return memory_usage_percent

    def extract_memory_usage_bytes(self):

        memory_usage_percent = psutil.virtual_memory().used
        return memory_usage_percent

    def extract_swap_usage_percent(self):

        swap_usage_percent = psutil.swap_memory().percent
        return swap_usage_percent

    def extract_swap_usage_bytes(self):

        memory_usage_percent = psutil.swap_memory().used
        return memory_usage_percent

    # Disk Metrics

    def extract_disk_usage_percent(self, path):

        try:
            
            disk_usage_percent = psutil.disk_usage(path).percent
            return disk_usage_percent

        except OSError:
            self.logger.error('Exception in extract_disk_usage_percent', exc_info=True)

    def extract_disk_rw_count(self):

        disk_io_counters = psutil.disk_io_counters()
        disk_rw_count = (disk_io_counters.read_count, disk_io_counters.write_count)
        return disk_rw_count

    # Network Metrics

    def extract_net_packet_sent_rcvd_count(self):

        net_io_counters = psutil.net_io_counters()
        net_packet_sent_rcvd_count = (net_io_counters.packets_sent, net_io_counters.packets_recv)
        return net_packet_sent_rcvd_count

    def extract_net_connections_number(self):

        net_connections_number = len(psutil.net_connections(kind='inet'))
        return net_connections_number

    # Battery Metrics

    def extrct_battery_percent(self):

        try:
            battery_percent = psutil.sensors_battery().percent
            return battery_percent
        except:
            self.logger.error('There is no battery in this agent.', exc_info=True)

    # Connect to Server to Send Metrics
    def send_to_server(self, num_conns):

        server_addr = (self.server_ip, self.server_port)
        for i in range(0, num_conns):
            while True:
                connid = i + 1
                print(f"Starting connection {connid} to {server_addr}")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setblocking(False)
                sock.connect_ex(server_addr)
                if self.is_socket_closed(sock):
                    self.logger.warning('Server is down. try again in 5s')
                    time.sleep(5)
                    continue
                events = selectors.EVENT_READ | selectors.EVENT_WRITE
                data = types.SimpleNamespace(
                    connid=connid,
                    msg_total=sum(len(m) for m in self.messages),
                    recv_total=0,
                    messages=self.messages.copy(),
                    outb=b"",
                )
                self.sel.register(sock, events, data=data)
                break

        try:
            while True:
                result = None
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    result = self.service_connection(key, mask)
                if result:
                    break
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        except:
            self.logger.error('Exception in send_to_server', exc_info=True)
        finally:
            self.sel.close()

    def service_connection(self, key, mask):
        
        try:

            sock = key.fileobj
            data = key.data

            if mask & selectors.EVENT_READ:

                recv_data = sock.recv(1024)  # Should be ready to read
                
                if recv_data:
                    print(f"Received {recv_data!r} from connection {data.connid}")
                    data.recv_total += int(recv_data)

                if not recv_data or data.recv_total == data.msg_total:
                    print(f"Closing connection to {self.server_ip, self.server_port}")
                    self.sel.unregister(sock)
                    sock.close()
                    return 1

            if mask & selectors.EVENT_WRITE:

                if not data.outb and data.messages:
                    data.outb = data.messages.pop(0)

                if data.outb:
                    print(f"Sending {data.outb!r} to connection {data.connid}")
                    sent = sock.send(data.outb)  # Should be ready to write
                    data.outb = data.outb[sent:] 

        except ConnectionRefusedError as e:
            self.logger.warning('Server is down. try again in 5s')
            time.sleep(5)

    def is_socket_closed(self, sock: socket.socket) -> bool:
        
        try:
            # this will try to read bytes without blocking and also without removing them from buffer (peek only)
            data = sock.recv(16, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        except BlockingIOError:
            return False  # socket is open and reading from it would block or no application listening on this port
        except (ConnectionResetError, ConnectionRefusedError):
            return True  # socket was closed for some other reason
        except Exception as e:
            self.logger.exception("unexpected exception when checking if a socket is closed")
            return False
        return False

    def aggregate_metrics(self):

        metrics = dict()

        metrics['cpu_utilization_percent']  = self.extract_cpu_utilization_percent()
        metrics['cpu_frequency_average']    = self.extract_cpu_frequency_average()
        metrics['extract_cpu_temperature']  = self.extract_cpu_temperature()
        metrics['cpu_fan_speed']            = self.extract_cpu_fan_speed()

        metrics['memory_usage_percent']     = self.extract_memory_usage_percent()
        metrics['memory_usage_bytes']       = self.extract_memory_usage_bytes()

        metrics['swap_usage_percent']       = self.extract_swap_usage_percent()
        metrics['swap_usage_bytes']         = self.extract_swap_usage_bytes()

        pkt_sent, pkt_rcvd                  = self.extract_net_packet_sent_rcvd_count()
        metrics['net_packet_sent_count']    = pkt_sent
        metrics['net_packet_rcvd_count']    = pkt_rcvd
        metrics['net_connections_number']   = self.extract_net_connections_number()

        metrics['battery_percent']          = self.extrct_battery_percent()

        return metrics

    def send_metrics(self):
        metrics = self.aggregate_metrics()
        metrics_json = json.dumps(metrics)
        metrics_json_encoded = metrics_json.encode('utf-8')
        # print(f'{metrics_json_encoded!r}')
        self.messages = [metrics_json_encoded]
        self.send_to_server(num_conns=1)



if __name__ == '__main__':
    ma = MetricAgent('first agent')
    # ma.send_to_server(1)
    ma.send_metrics()