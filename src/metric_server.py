import sys
import socket
import types
import selectors
import logging

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
                else:
                    print(f"Closing connection to {data.addr}")
                    self.sel.unregister(sock)
                    sock.close()
            if mask & selectors.EVENT_WRITE:
                if data.outb:
                    print(f"Echoing {data.outb!r} to {data.addr}")
                    sent = sock.send(data.outb)  # Should be ready to write
                    data.outb = data.outb[sent:]
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


if __name__ == "__main__":
    ms = MetricServer('my metric server')
    ms.run()