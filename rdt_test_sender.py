import socket

from rdt import RDTConnection, BUFFER_SIZE
from common import BTPPacket

this_addr = ("127.0.0.1", 45561)
peer_addr = ("127.0.0.1", 45560)
this_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
this_sock.bind(this_addr)


# Test 5
def test_no_ack_receive():
    my_conn = RDTConnection(this_sock, peer_addr)
    pkt = BTPPacket("Hello receiver".encode("ASCII"))
    my_conn.send(pkt)

# Test 6
def test_wrong_ack_receive():
    my_conn = RDTConnection(this_sock, peer_addr)
    pkt = BTPPacket("Hello receiver".encode("ASCII"))
    my_conn.send(pkt)

# Test 7
def test_invalid_packet_send():
    pkt = BTPPacket(seq=69)
    this_sock.sendto(pkt.raw, peer_addr)
    data, _ = this_sock.recvfrom(BUFFER_SIZE)
    header, _ = BTPPacket.unpack(data)
    if header.ack == 1 and header.seq == 69:
        pkt = BTPPacket(seq=0)
        this_sock.sendto(pkt.raw, peer_addr)
    
    data, _ = this_sock.recvfrom(BUFFER_SIZE)


def main():
    test_no_ack_receive()
    test_wrong_ack_receive()
    test_invalid_packet_send()
    this_sock.close()