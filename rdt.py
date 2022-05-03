from select import select
from common import BUFFER_SIZE, RDT_TIMEOUT, BTPPacket

SELECTOR_TIMEOUT = RDT_TIMEOUT * 10
        

class AbstractRDT:
    def __init__(self, ctx, debug):
        self.ctx = ctx
        self.debug = debug
    
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
    def __init__(self, ctx, debug):
        super().__init__(ctx, debug)
        self.sent_packet = None
        self._waiting = False
    
    def is_ack(self, data):
        header, _ = BTPPacket.unpack(data)
        if self.debug:
            print(header)
        return header.ack == 1 and header.seq == self.seq

    def send(self, packet):
        if not self._waiting:
            if self.debug:
                print("Sending packet...")

            packet.sequence = self.seq
            self.sent_packet = packet.raw
            self.sock.sendto(self.sent_packet, self.peer)
            self.sock.settimeout(RDT_TIMEOUT)
            self._waiting = True

        while self._waiting:
            if self.debug:
                print("Waiting for ACK...")

            try:                
                data, addr = self.sock.recvfrom(BUFFER_SIZE)  
                if addr != self.peer:
                    if self.debug:
                        print("Invalid hostname")

                    continue

                if self.is_ack(data):
                    if self.debug:
                        print("Correct ACK received.")

                    self.sock.settimeout(None)
                    self.seq += 1
                    self._waiting = False
                    break
                
                self.sock.sendto(self.sent_packet, self.peer)
                if self.debug:
                    print("Incorrect ACK...resent last packet.")

            except TimeoutError:
                self.sock.sendto(self.sent_packet, self.peer)
                if self.debug:
                    print("Timeout...resent last packet.")


class RDTReceiver(AbstractRDT):
    def __init__(self, ctx, debug):
        super().__init__(ctx, debug)

    def recv(self):
        while True:
            if self.debug:
                print("Waiting to receive...")

            r, _, _ = select([self.sock], [], [], SELECTOR_TIMEOUT)
            if not r:
                if self.debug:
                    print("Connection timed out.")

                return
            
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            if self.peer is not None and addr != self.peer:
                if self.debug:
                    print(addr)
                    print("Invalid hostname")
    
                continue

            header, body = BTPPacket.unpack(data)
            if self.debug:
                print(header)
        
            if header.seq == self.seq:
                if self.debug:
                    print(f"Correct sequence...sending ack {self.seq}.")
                
                if self.seq == 0 and self.peer is None:
                    self.peer = addr
    
                resp = BTPPacket(ack=1, seq=self.seq)
                self.sock.sendto(resp.raw, self.peer)
                self.seq += 1
                return (header, body)
            else:
                if self.debug:
                    print(f"Incorrect sequence...sending ack {header.seq}.")
    
                resp = BTPPacket(ack=1, seq=header.seq)
                self.sock.sendto(resp.raw, addr)


class RDTConnection:
    def __init__(self, sock, peer=None, seq=0, debug=False):
        self.sock = sock
        self.peer = peer
        self.seq = seq
        self.sender = RDTSender(self, debug)
        self.receiver = RDTReceiver(self, debug)

    def send(self, packet):
        self.sender.send(packet)
    
    def recv(self):
        return self.receiver.recv()


        