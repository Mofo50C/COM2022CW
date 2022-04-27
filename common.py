import json
import struct
from bitarray.util import zeros, ba2int, int2ba
from dataclasses import dataclass

# constants
BUFFER_SIZE = 4096
RSA_BITS = 512
RDT_TIMEOUT = 5
SERVER_ADDR = ("127.0.0.1", 45560)
MENU_FILE = "./menu.json"
HEADER_FORMAT = "!LHH"
HEADER_LENGTH = struct.calcsize(HEADER_FORMAT)
PAYLOAD_LENGTH = BUFFER_SIZE - HEADER_LENGTH

@dataclass
class BTPHeader:
    seq: int = 0
    ack: int = 0
    rsa: int = 0
    fin: int = 0
    body_len: int = 0


class BTPPacket:
    def __init__(self, payload=b"", seq=0, ack=0, rsa=0, fin=0):
        self.payload = payload
        self.sequence = seq
        self.ack = ack
        self.rsa = rsa
        self.fin = fin
        self._raw = None

    @property
    def raw(self):
        self._build()
        return self._raw

    def _build(self):
        flags = zeros(16, endian="big")
        flags[0] = self.ack
        flags[1] = self.rsa
        flags[2] = self.fin
        body_len = len(self.payload)
        raw_pkt = struct.pack(HEADER_FORMAT, self.sequence, ba2int(flags, signed=False), body_len)

        if body_len > 0:
            raw_pkt += self.payload

        self._raw = raw_pkt

    @staticmethod
    def unpack(raw):
        seq, flags, body_len = struct.unpack(HEADER_FORMAT, raw[:HEADER_LENGTH])
        body = raw[HEADER_LENGTH:]
        flags = int2ba(flags, 16, endian="big", signed=False)
        ack, rsa, fin, *_ = flags
        return BTPHeader(seq, ack, rsa, fin, body_len), body


class Drink:
    def __init__(self, json_data):
        self.id = json_data["id"]
        self.name = json_data["name"]
        self.price = json_data["price"]

    def __repr__(self):
        return f"{self.id}: {self.name} £{self.price:.2f}"


with open(MENU_FILE, "r") as f:
    DRINKS = json.load(f)

DRINKS = [Drink(x) for x in DRINKS]
DRINKS = {d.id: d for d in DRINKS}


