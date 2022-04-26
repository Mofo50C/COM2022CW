import socket
import rsa

from signal import signal, SIGINT
from threading import Event, Thread
from common import BTPPacket, SERVER_ADDR, RSA_BITS, DRINKS
from rdt import RDTSender, RDTReceiver

LAST_CLIENT_ID = 0
ClIENT_KEYS = {}
CLIENTS = {}
TABS = {}
S_PUB_KEY, S_PRIV_KEY = rsa.newkeys(RSA_BITS, accurate=True)
DONE = Event()
DONE.clear()

def encrypt(data, key):
    return rsa.encrypt(data, key)

def decrypt(data):
    return rsa.decrypt(data, S_PRIV_KEY)

def get_client_id():
    global LAST_CLIENT_ID 
    LAST_CLIENT_ID += 1
    return LAST_CLIENT_ID


class ClientRequestHandler:
    def __init__(self, sender, receiver):
        self.sender = sender
        self.receiver = receiver
        self.client = receiver.peer
        self.finished = False

    def handle(self, data=None):
        if data is None:
            print("no data...req still ongoing")
            pkt_header, pkt_payload = self.receiver.recv()
        else:
            pkt_header, pkt_payload = data
            data = None
        
        if pkt_header.fin == 1:
            print("got fin req")
            sndpkt = BTPPacket(fin=1, ack=1)
            self.sender.send(sndpkt)
            self.finished = True
        elif pkt_header.rsa == 1:
            new_client_key = rsa.PublicKey.load_pkcs1(pkt_payload)
            ClIENT_KEYS[self.client] = new_client_key
            sndpkt = BTPPacket(payload=S_PUB_KEY.save_pkcs1(), rsa=1, ack=1)
            self.sender.send(sndpkt)
        else:
            message = decrypt(pkt_payload).decode("ASCII").strip()

            if message == "OPEN":
                try:
                    cid = CLIENTS[self.client]
                except KeyError:
                    cid = get_client_id()
                    CLIENTS[self.client] = cid

                resp = f"SETID {cid}"
                resp = encrypt(resp.encode("ASCII"), ClIENT_KEYS[self.client])
                sndpkt = BTPPacket(payload=resp)
                self.sender.send(sndpkt)
                if cid not in TABS:
                    TABS[cid] = 0
            else:
                message = message.split("\r\n")
                id_string = message[0].split(" ")
                command_string = message[1].split(" ")
                if id_string[0] != "ID":
                    # TODO error...unknown command
                    pass
                 
                client_id = int(id_string[1])
                try:
                    CLIENTS[client_id]
                except KeyError:
                    # TODO error...unauthorised
                    pass

                if command_string[0] == "CLOSE":
                    del CLIENTS[self.client]
                    resp = f"TOTAL {TABS[client_id]:.2f}"
                    resp = encrypt(resp.encode("ASCII"), ClIENT_KEYS[self.client])
                    sndpkt = BTPPacket(payload=resp)
                    self.sender.send(sndpkt)
                    del ClIENT_KEYS[self.client]
                    del TABS[client_id]
                elif command_string[0] == "ADD":
                    drink_id = int(command_string[1])
                    quantity = 1
                    if len(command_string) > 2:
                        quantity = int(command_string[2])
                    
                    order_price = DRINKS[drink_id].price * quantity
                    TABS[client_id] += order_price
                    resp = f"TOTAL {TABS[client_id]:.2f}"
                    resp = encrypt(resp.encode("ASCII"), ClIENT_KEYS[self.client])
                    sndpkt = BTPPacket(payload=resp)
                    self.sender.send(sndpkt)
                else:
                    # TODO error...unknown command
                    pass

class Server:
    def __init__(self, event):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(SERVER_ADDR)
        self.current_request = None
        self.done = event

    def get_incoming(self):
        receiver = RDTReceiver(self.socket)
        req = receiver.recv()
        if req is None:
            return

        pkt_header, pkt_payload = req
        sender = RDTSender(self.socket, receiver.peer)
        return pkt_header, pkt_payload, sender, receiver

    def handle_requests(self):
        print(self.current_request)
        if self.current_request is not None:
            print(self.current_request.finished)
        if not (self.current_request is None or self.current_request.finished):
            print("continue req")
            self.current_request.handle()
        else: # new request
            incoming = self.get_incoming()
            if incoming is None:
                return
            
            header, body, sender, receiver = incoming
            self.current_request = ClientRequestHandler(sender, receiver)
            self.current_request.handle((header, body))

    def serve_once(self):
        self.handle_requests()
        self.socket.close()

    def serve_forever(self):
        while not self.done.is_set():
            self.handle_requests()
        
        self.socket.close()


def run_server():
    server = Server(DONE)
    server.serve_forever()

signal(SIGINT, lambda signal, framnum: DONE.set())
th = Thread(target=run_server)
th.start()
while th.is_alive():
    continue

print("Server shutting down...")
