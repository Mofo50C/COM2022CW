import socket
import time

from rdt import RDTConnection
from common import BTPPacket, BUFFER_SIZE

this_addr = ("127.0.0.1", 45560)
peer_addr = ("127.0.0.1", 45561)
this_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
this_sock.bind(this_addr)

def assert_test(num, cond):
    if cond:
        print(f"Test {num}: Passed.")
    else:
        print(f"Test {num}: Failed!")

# Test 5
def test_no_ack_send():
    data, _ = this_sock.recvfrom(BUFFER_SIZE)
    time.sleep(7)
    data2, _ = this_sock.recvfrom(BUFFER_SIZE)
    ack = BTPPacket(seq=0, ack=1)
    this_sock.sendto(ack.raw, peer_addr)
    assert_test(5, (data == data2))
# Test 6
def test_wrong_ack_send():
    data, _ = this_sock.recvfrom(BUFFER_SIZE)
    ack = BTPPacket(seq=69, ack=1)
    this_sock.sendto(ack.raw, peer_addr)
    data2, _ = this_sock.recvfrom(BUFFER_SIZE)
    ack = BTPPacket(seq=0, ack=1)
    this_sock.sendto(ack.raw, peer_addr)
    assert_test(6, (data == data2))

# Test 7
def test_invalid_packet_receive():
    my_conn = RDTConnection(this_sock, peer=peer_addr, debug=False)
    incoming = my_conn.recv()
    assert_test(7, (incoming is not None))


def main():
    test_no_ack_send()
    test_wrong_ack_send()
    test_invalid_packet_receive()
    this_sock.close()