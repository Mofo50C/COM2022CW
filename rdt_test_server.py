import socket

from rdt import RDTSender, RDTReceiver
from common import BTPPacket

s_addr = ("127.0.0.1", 45560)
server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_sock.bind(s_addr)

s_receiver = RDTReceiver(server_sock)
pkt_header, pkt_payload = s_receiver.recv()
pkt_payload = pkt_payload.decode("ASCII")
print(pkt_header)
print(f"Client says: {pkt_payload}")
print("sending response")
msg = "Hi client :)"
resp = BTPPacket(msg.encode("ASCII"))
s_sender = RDTSender(server_sock, s_receiver.peer)
s_sender.send(resp)
print("Server shutting down...")
server_sock.close()
