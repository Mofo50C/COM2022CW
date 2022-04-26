import socket

from rdt import RDTReceiver, RDTSender
from common import BTPPacket

c_addr = ("127.0.0.1", 45561)
s_addr = ("127.0.0.1", 45560)
client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_sock.bind(c_addr)

c_sender = RDTSender(client_sock, s_addr)
c_receiver = RDTReceiver(client_sock, s_addr)

msg = "Hello server!"
req = BTPPacket(msg.encode("ASCII"))
c_sender.send(req)

pkt_header, pkt_payload = c_receiver.recv()
pkt_payload = pkt_payload.decode("ASCII")
print(f"Server says: {pkt_payload}")
print("Client shutting down...")

client_sock.close()

