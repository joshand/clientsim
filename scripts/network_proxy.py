# import logging
import select
import socket
import struct
import time
from socketserver import ThreadingMixIn, TCPServer, StreamRequestHandler
from client_sim.models import *
import atexit
from apscheduler.schedulers.background import BackgroundScheduler


# logging.basicConfig(level=logging.DEBUG)
SOCKS_VERSION = 5
SOCKS_PORT = 9011
server = None


def dolog(fn, step, *txt):
    l = Log.objects.create(function=fn, step=step, log=",".join(map(str, txt)))
    l.save()


def start_server():
    global server
    try:
        # dolog("network_proxy", "start_server", "Starting proxy server on port " + str(SOCKS_PORT))
        with TCPServer(('0.0.0.0', SOCKS_PORT), SocksProxy) as server:
            server.serve_forever()
    except:
        print("Unable to start proxy server (it might already be running)")


# class ThreadingTCPServer(ThreadingMixIn, TCPServer):
#     pass


class SocksProxy(StreamRequestHandler):
    username = 'username'
    password = 'password'

    def handle(self):
        # logging.info('Accepting connection from %s:%s' % self.client_address)

        # greeting header
        # read and unpack 2 bytes from a client
        header = self.connection.recv(2)
        version, nmethods = struct.unpack("!BB", header)

        # socks 5
        assert version == SOCKS_VERSION
        assert nmethods > 0

        # get available methods
        methods = self.get_available_methods(nmethods)

        # accept only USERNAME/PASSWORD auth
        if 2 not in set(methods):
            # close connection
            self.server.close_request(self.request)
            return

        # send welcome message
        self.connection.sendall(struct.pack("!BB", SOCKS_VERSION, 2))

        # if not self.verify_credentials():
        #     return
        delay = self.parse_credentials()
        # print("=======", delay)

        # request
        version, cmd, _, address_type = struct.unpack("!BBBB", self.connection.recv(4))
        assert version == SOCKS_VERSION

        if address_type == 1:  # IPv4
            address = socket.inet_ntoa(self.connection.recv(4))
        elif address_type == 3:  # Domain name
            domain_length = ord(self.connection.recv(1)[0])
            address = self.connection.recv(domain_length)

        port = struct.unpack('!H', self.connection.recv(2))[0]

        # reply
        try:
            if cmd == 1:  # CONNECT
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.connect((address, port))
                bind_address = remote.getsockname()
                # logging.info('Connected to %s %s' % (address, port))
            else:
                self.server.close_request(self.request)

            addr = struct.unpack("!I", socket.inet_aton(bind_address[0]))[0]
            port = bind_address[1]
            reply = struct.pack("!BBBBIH", SOCKS_VERSION, 0, 0, address_type,
                                addr, port)

        except Exception as err:
            # logging.error(err)
            # return connection refused error
            reply = self.generate_failed_reply(address_type, 5)

        self.connection.sendall(reply)
        if delay:
            time.sleep(int(delay))

        # establish data exchange
        if reply[1] == 0 and cmd == 1:
            self.exchange_loop(self.connection, remote)

        self.server.close_request(self.request)

    def get_available_methods(self, n):
        methods = []
        for i in range(n):
            methods.append(ord(self.connection.recv(1)))
        return methods

    def parse_credentials(self):
        version = ord(self.connection.recv(1))
        assert version == 1

        username_len = ord(self.connection.recv(1))
        username = self.connection.recv(username_len).decode('utf-8')

        password_len = ord(self.connection.recv(1))
        password = self.connection.recv(password_len).decode('utf-8')

        if username == "delay":
            # success, status = 0
            response = struct.pack("!BB", version, 0)
            self.connection.sendall(response)
            return password

        # failure, status != 0
        response = struct.pack("!BB", version, 0xFF)
        self.connection.sendall(response)
        self.server.close_request(self.request)
        return False

    def verify_credentials(self):
        version = ord(self.connection.recv(1))
        assert version == 1

        username_len = ord(self.connection.recv(1))
        username = self.connection.recv(username_len).decode('utf-8')

        password_len = ord(self.connection.recv(1))
        password = self.connection.recv(password_len).decode('utf-8')

        if username == self.username and password == self.password:
            # success, status = 0
            response = struct.pack("!BB", version, 0)
            self.connection.sendall(response)
            return True

        # failure, status != 0
        response = struct.pack("!BB", version, 0xFF)
        self.connection.sendall(response)
        self.server.close_request(self.request)
        return False

    def generate_failed_reply(self, address_type, error_number):
        return struct.pack("!BBBBIH", SOCKS_VERSION, error_number, 0, address_type, 0, 0)

    def exchange_loop(self, client, remote):
        while True:
            # wait until client or remote is available for read
            r, w, e = select.select([client, remote], [], [])

            if client in r:
                data = client.recv(4096)
                if remote.send(data) <= 0:
                    break

            if remote in r:
                data = remote.recv(4096)
                if client.send(data) <= 0:
                    break


def shutdown():
    global server
    try:
        if server:
            server.shutdown()
            server.server_close()
        cron.shutdown(wait=False)
    except Exception as e:
        print("Error", e)


def run():
    # Enable the job scheduler to run schedule jobs
    cron = BackgroundScheduler(standalone=True)

    # Explicitly kick off the background thread
    cron.start()
    cron.remove_all_jobs()
    job = cron.add_job(start_server)

    # Shutdown your cron thread if the web process is stopped
    atexit.register(shutdown)      # lambda: cron.shutdown(wait=False)

    # if __name__ == '__main__':
    #     # with ThreadingTCPServer(('0.0.0.0', SOCKS_PORT), SocksProxy) as server:
    #     with TCPServer(('0.0.0.0', SOCKS_PORT), SocksProxy) as server:
    #         server.serve_forever()
