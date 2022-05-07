import socket
import rsa

from signal import signal, SIGINT
from threading import Event, Thread
from common import BTPPacket, SERVER_ADDR, RSA_BITS, DRINKS, COMPAT_MODE
from rdt import RDTConnection

LAST_CLIENT_ID = 0
CLIENT_KEYS = {}
CLIENTS = {}
TABS = {}
S_PUB_KEY, S_PRIV_KEY = rsa.newkeys(RSA_BITS, accurate=True)
S_KEY_PEM = S_PUB_KEY.save_pkcs1()
EXIT_EVENT = Event()
EXIT_EVENT.clear()

def encrypt(data, key):
    return rsa.encrypt(data, key)

def decrypt(data):
    return rsa.decrypt(data, S_PRIV_KEY)

def get_client_id():
    global LAST_CLIENT_ID 
    LAST_CLIENT_ID += 1
    return LAST_CLIENT_ID


class ClientRequestHandler:
    def __init__(self, conn):
        self.conn = conn
        self.client = conn.peer
        self.finished = False

    def send_response(self, message):
        resp = encrypt(message.encode("ASCII"), CLIENT_KEYS[self.client])
        sndpkt = BTPPacket(resp)
        self.conn.send(sndpkt)

    def handle_error(self, status, message):
        self.finished = True
        if not COMPAT_MODE:
            resp = f"ERROR {status} {message}"
            self.send_response(resp)
        

    def handle(self, data=None):
        if data is None:
            if (data := self.conn.recv()) is None:
                return
        
        pkt_header, pkt_payload = data
        
        if pkt_header.fin == 1:
            print("FIN REQ")
            sndpkt = BTPPacket(fin=1, ack=1)
            self.conn.send(sndpkt)
            self.finished = True
        elif pkt_header.rsa == 1:
            print("RSA REQ")
            sndpkt = BTPPacket(payload=S_KEY_PEM, rsa=1, ack=1)
            self.conn.send(sndpkt)
            CLIENT_KEYS[self.client] = rsa.PublicKey.load_pkcs1(pkt_payload)
        else:
            message = decrypt(pkt_payload).decode("ASCII").strip()

            if message == "OPEN":
                print("OPEN REQ")
                if self.client in CLIENTS:
                    cid = CLIENTS[self.client]
                else:
                    cid = get_client_id()
                    CLIENTS[self.client] = cid

                resp = f"SETID {cid}"
                self.send_response(resp)
                if cid not in TABS:
                    TABS[cid] = 0
            else:
                message = message.split("\r\n", 1)
                id_string = message[0].split(" ")
                
                if id_string[0] != "ID":
                    self.handle_error(1, "UKNOWN COMMAND")
                    return
                
                try:
                    cid = int(id_string[1])
                except ValueError:
                    self.handle_error(1, "UNKNOWN COMMAND")
                    return

                if cid != CLIENTS[self.client]:
                    self.handle_error(2, "UNAUTHORISED")
                    return

                command_string = message[1]
                if command_string == "CLOSE":
                    print("CLOSE REQ")
                    del CLIENTS[self.client]
                    resp = f"TOTAL {TABS[cid]:.2f}"
                    self.send_response(resp)
                    del CLIENT_KEYS[self.client]
                    del TABS[cid]
                else:
                    order_string = command_string.split("\r\n")
                    if len(order_string) == 1:
                        add_string = order_string[0].split(" ")
                        if add_string[0] == "ADD":
                            print("SINGLE ADD REQ")
                            drink_id = add_string[1]
                            quantity = 1
                            if len(add_string) > 2:
                                quantity = int(add_string[2])
                            
                            order_price = DRINKS[drink_id].price * quantity
                            TABS[cid] += order_price
                            resp = f"TOTAL {TABS[cid]:.2f}"
                            self.send_response(resp)
                    elif not COMPAT_MODE:
                        if order_string[0] == "ADD":
                            print("MULTIPLE ADD REQ")
                            total = 0
                            for order in order_string[1:]:
                                drink_string = order.split(" ")
                                drink_id = drink_string[0]
                                quantity = 1
                                if len(drink_string) > 1:
                                    quantity = int(drink_string[1])
                                
                                total += DRINKS[drink_id].price * quantity
                            
                            TABS[cid] += total
                            resp = f"TOTAL {TABS[cid]:.2f}"
                            self.send_response(resp)
                        else:
                            self.handle_error(1, "UNKNOWN COMMAND")


class Server:
    def __init__(self, event):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(SERVER_ADDR)
        self.current_request = None
        self.done = event

    def get_incoming(self):
        conn = RDTConnection(self.socket)
        req = conn.recv()
        if req is None:
            return

        pkt_header, pkt_payload = req
        return pkt_header, pkt_payload, conn

    def handle_requests(self):
        if not (self.current_request is None or self.current_request.finished):
            print("continue...")
            self.current_request.handle()
        else: # new request
            incoming = self.get_incoming()
            if incoming is None:
                return
            
            header, body, conn = incoming
            self.current_request = ClientRequestHandler(conn)
            self.current_request.handle((header, body))

    def serve_forever(self):
        while not self.done.is_set():
            self.handle_requests()
        
        self.socket.close()


def run_server():
    server = Server(EXIT_EVENT)
    server.serve_forever()

def main():
    signal(SIGINT, lambda signal, framnum: EXIT_EVENT.set())
    th = Thread(target=run_server)
    th.start()
    while th.is_alive():
        continue

    print("Server shutting down...")


main()