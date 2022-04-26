from select import select
from common import BUFFER_SIZE, RDT_TIMEOUT, BTPPacket

SELECTOR_TIMEOUT = RDT_TIMEOUT * 5

class RDTState:
    def __init__(self, ctx):
        self.ctx = ctx

    def recv(self):
        pass

    def send(self, data):
        pass


class WaitingForCall(RDTState):
    def __init__(self, ctx):
        super().__init__(ctx)
    
    def send(self, packet):
        print("sent...")
        packet.sequence = self.ctx.seq
        self.ctx.sent_packet = packet.raw
        self.ctx.sock.sendto(self.ctx.sent_packet, self.ctx.peer)
        self.ctx.sock.settimeout(RDT_TIMEOUT)
        self.ctx.next_state = 1


class WaitingForAck(RDTState):
    def __init__(self, ctx):
        super().__init__(ctx)

    def is_ack(self, data):
        header, _ = BTPPacket.unpack(data)
        return header.ack == 1 and header.seq == self.ctx.seq

    def recv(self):
        print("waiting for ack...")
        while True:
            r, _, _ = select([self.ctx.sock], [], [], SELECTOR_TIMEOUT)
            if not r:
                print("Error...")
                return

            try:                
                data, addr = self.ctx.sock.recvfrom(BUFFER_SIZE)  
                if addr != self.ctx.peer:
                    print("wrong address")
                    continue

                if self.is_ack(data):
                    print("ack received!")
                    self.ctx.sock.settimeout(None)
                    self.ctx.seq += 1
                    self.ctx.next_state = 0
                    break
                
                self.ctx.sock.sendto(self.ctx.sent_packet, self.ctx.peer)
                print("resent")
            except TimeoutError:
                self.ctx.sock.sendto(self.ctx.sent_packet, self.ctx.peer)
                print("timeout")
                print("resent")
        

class RDTSender:
    def __init__(self, sock, peer, seq=0):
        self.sock = sock
        self.peer = peer
        self.seq = seq
        self.next_state = 0
        self.sent_packet = None
        self._state_map = [WaitingForCall(self), WaitingForAck(self)]
        self._state = None

    @property
    def state(self):
        self._switch()
        return self._state

    def _switch(self):
        if self.next_state is None:
            return
        
        self._state = self._state_map[self.next_state]
        self.next_state = None

    def send(self, packet):
        self.state.send(packet)
        self.state.recv()


class RDTReceiver:
    def __init__(self, sock, peer=None, seq=0):
        self.sock = sock
        self.peer = peer
        self.seq = seq

    def recv(self):
        print("Waiting to receive...")
        while True:
            r_sock, _, _ = select([self.sock], [], [], SELECTOR_TIMEOUT)
            if not r_sock:
                print("Error...")
                return
            
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            print(addr)
            if self.peer is not None and addr != self.peer:
                print("wrong address")
                continue

            header, body = BTPPacket.unpack(data)
            print(header)
            print(f"receiver seq = {self.seq}")
            if header.seq == self.seq:
                if self.seq == 0 and self.peer is None:
                    self.peer = addr
    
                resp = BTPPacket(ack=1, seq=self.seq)
                self.sock.sendto(resp.raw, self.peer)
                self.seq += 1
                print("received!")
                return (header, body)
            else:
                resp = BTPPacket(ack=1, seq=header.seq)
                self.sock.sendto(resp.raw, addr)
        