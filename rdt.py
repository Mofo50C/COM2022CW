from select import select
from common import BUFFER_SIZE, RDT_TIMEOUT, BTPPacket

SELECTOR_TIMEOUT = RDT_TIMEOUT * 10
        

class AbstractRDT:
    def __init__(self, ctx):
        self.ctx = ctx
    
    @property
    def seq(self):
        return self.ctx.seq

    @seq.setter
    def seq(self, seq):
        self.ctx.seq = seq

    @property
    def peer(self):
        return self.ctx.peer
    
    @peer.setter
    def peer(self, peer):
        self.ctx.peer = peer
    
    @property
    def sock(self):
        return self.ctx.sock


class RDTSender(AbstractRDT):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.sent_packet = None
        self._waiting = False
    
    def is_ack(self, data):
        header, _ = BTPPacket.unpack(data)
        print(header)
        return header.ack == 1 and header.seq == self.seq

    def send(self, packet):
        if not self._waiting:
            print("Sending...")
            packet.sequence = self.seq
            self.sent_packet = packet.raw
            self.sock.sendto(self.sent_packet, self.peer)
            self.sock.settimeout(RDT_TIMEOUT)
            self._waiting = True

        while self._waiting:
            print("Waiting for ACK...")

            try:                
                data, addr = self.sock.recvfrom(BUFFER_SIZE)  
                if addr != self.peer:
                    print("Invalid hostname")
                    continue

                if self.is_ack(data):
                    print("ACK received!")
                    self.sock.settimeout(None)
                    self.seq += 1
                    self._waiting = False
                    break
                
                self.sock.sendto(self.sent_packet, self.peer)
                print("Resent last packet")
            except TimeoutError:
                self.sock.sendto(self.sent_packet, self.peer)
                print("Timeout")
                print("Resent last packet")


class RDTReceiver(AbstractRDT):
    def __init__(self, ctx):
        super().__init__(ctx)

    def recv(self):
        while True:
            print("Waiting to receive...")
            print(f"receiver.seq: {self.seq}")
            r, _, _ = select([self.sock], [], [], SELECTOR_TIMEOUT)
            if not r:
                print("Retry")
                return
            
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            print(addr)
            if self.peer is not None and addr != self.peer:
                print("Invalid hostname")
                continue

            header, body = BTPPacket.unpack(data)
            print(header)
            if header.seq == self.seq:
                print("Packet received")
                if self.seq == 0 and self.peer is None:
                    self.peer = addr
    
                resp = BTPPacket(ack=1, seq=self.seq)
                self.sock.sendto(resp.raw, self.peer)
                self.seq += 1
                print(f"receiver.seq: {self.seq}")
                return (header, body)
            else:
                resp = BTPPacket(ack=1, seq=header.seq)
                self.sock.sendto(resp.raw, addr)


class RDTConnection:
    def __init__(self, sock, peer=None, seq=0):
        self.sock = sock
        self.peer = peer
        self.seq = seq
        self.sender = RDTSender(self)
        self.receiver = RDTReceiver(self)

    def send(self, packet):
        self.sender.send(packet)
    
    def recv(self):
        return self.receiver.recv()


        