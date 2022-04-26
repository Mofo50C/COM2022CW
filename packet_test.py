from common import BTPPacket

msg = "Hello world!"
my_packet = BTPPacket(msg.encode("ASCII"))
my_packet.ack = 1
my_packet.rsa = 1
my_packet.fin = 1
header, body = BTPPacket.unpack(my_packet.raw)
print(header)



