import socket
import rsa
from common import DRINKS, BTPPacket, SERVER_ADDR, RSA_BITS
from rdt import RDTSender, RDTReceiver

DRINK_MENU = "./barMenu.txt"
CLIENT_ADDR = ("127.0.0.1", 45561)
CLIENT_SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
CLIENT_SOCK.bind(CLIENT_ADDR)
C_PUB_KEY, C_PRIV_KEY = rsa.newkeys(RSA_BITS, accurate=True)
CLIENT_ID = 0
TAB = 0


def encrypt(data):
    return rsa.encrypt(data, S_KEY)

def decrypt(data):
    return rsa.decrypt(data, C_PRIV_KEY)


class Client:
    def __init__(self):
        self.sender = RDTSender(CLIENT_SOCK, SERVER_ADDR)
        self.receiver = RDTReceiver(CLIENT_SOCK, SERVER_ADDR)
    
    def finish_request(self):
        print("FINISHING REQUEST")
        while True:
            sndpkt = BTPPacket(fin=1)
            self.sender.send(sndpkt)
            pkt_header, pkt_payload = self.receiver.recv()
            if pkt_header.fin == 1 and pkt_header.ack == 1:
                break

    def open_tab(self):
        print("OPENING TAB")
        message = "OPEN"
        message = encrypt(message.encode("ASCII"))
        sndpkt = BTPPacket(message)
        self.sender.send(sndpkt)
        pkt_header, pkt_payload = self.receiver.recv()
        resp = decrypt(pkt_payload).decode("ASCII").split(" ")
        cid = int(resp[1])
        print(f"TAB OPENED: {cid}")
        return cid
    
    def close_tab(self):
        print("CLOSING TAB")
        auth_msg = f"ID {CLIENT_ID}\r\n"
        message = auth_msg + f"CLOSE"
        message = encrypt(message.encode("ASCII"))
        sndpkt = BTPPacket(message)
        self.sender.send(sndpkt)
        pkt_header, pkt_payload = self.receiver.recv()
        resp = decrypt(pkt_payload).decode("ASCII").split(" ")
        final_tab = float(resp[1])
        return final_tab

    def order(self, drink, quantity):
        print("ORDERING")
        auth_msg = f"ID {CLIENT_ID}\r\n"
        message = auth_msg + f"ADD {drink.id}"
        if quantity > 1:
            message += f" {quantity}"

        message = encrypt(message.encode("ASCII"))
        sndpkt = BTPPacket(message)
        self.sender.send(sndpkt)
        pkt_header, pkt_payload = self.receiver.recv()
        resp = decrypt(pkt_payload).decode("ASCII").split(" ")
        tab = float(resp[1])
        return tab
    
    def send(self, sndpkt):
        self.sender.send(sndpkt)
    
    def recv(self):
        return self.receiver.recv()


def exchange_rsa():
    client = Client()
    while True:
        sndpkt = BTPPacket(C_PUB_KEY.save_pkcs1(), rsa=1)
        client.send(sndpkt)
        pkt_header, pkt_payload = client.recv()
        if pkt_header.rsa == 1 and pkt_header.ack == 1:
            break

    client.finish_request()
    return rsa.PublicKey.load_pkcs1(pkt_payload)

def handle_order(orders):
    global TAB, CLIENT_ID
    print("Ordering...")
    client = Client()
    if CLIENT_ID == 0:
        CLIENT_ID = client.open_tab()

    for drink, quantity in orders.values():
        TAB = client.order(drink, quantity)
    
    client.finish_request()
    print(f"Total tab: £{TAB:.2f}")

def handle_exit():
    global TAB
    if CLIENT_ID == 0 or TAB == 0:
        print("No open tab to close...")
        return

    print("Closing tab...")
    client = Client()
    TAB = client.close_tab()
    client.finish_request()
    print(f"Please pay the tab £{TAB:.2f} at the bar.")

def print_drink_menu():
    print("\nDRINKS MENU\n")
    print("Enter drink number or S to continue")
    print("X to cancel and exit")
    drink_menu = ""
    with open(DRINK_MENU, "r", encoding="utf-8") as f:
        while (line := f.readline()):
            drink_menu += "\t" + line.strip() + "\n"
    
    print(drink_menu + "\n")

def print_order(orders):
    if len(orders) > 0:
        print("\nCURRENT ORDER\n")
        total = 0
        for d, q in orders.values():
            price = q * d.price
            total += price
            print(f"\t{q}x {d.name}: £{price:.2f}")
        
        print(f"\n\tTOTAL: £{total:.2f}")

S_KEY = exchange_rsa()
DONE = False
while not DONE:
    print("\nCLIENT MENU\n\t1. Order drink\n\t2. Show tab\n\t3. Pay and exit\n")
    usr_menu_choice = 0
    while True:
        try:
            usr_menu_choice = int(input(">>> "))
            if usr_menu_choice in [1, 2, 3]:
                break
        except ValueError as e:
            pass
    
    if usr_menu_choice == 1:
        finish_order = False
        drinks_to_order = {}

        while not finish_order:
            print_order(drinks_to_order)
            print_drink_menu()
            usr_drink_choice = None
            while True:
                usr_drink_choice = input(">>> ")
                try:
                    usr_drink_choice = int(usr_drink_choice)
                    if usr_drink_choice in DRINKS.keys():
                        break
                except ValueError as e:
                    if usr_drink_choice.upper() in ["X", "S"]:
                        break

            if isinstance(usr_drink_choice, int):
                quantity = 0
                while True:
                    try:
                        quantity = int(input("How many? "))
                        break
                    except ValueError as e:
                        pass
                        
                if usr_drink_choice in drinks_to_order:
                    drink, prev_q = drinks_to_order[usr_drink_choice]
                    drinks_to_order[usr_drink_choice] = (drink, prev_q + quantity)
                else:
                    drinks_to_order[usr_drink_choice] = (DRINKS[usr_drink_choice], quantity)
            
            if isinstance(usr_drink_choice, str):
                finish_order = True
                if usr_drink_choice.upper() == "S" and len(drinks_to_order) > 0:
                    handle_order(drinks_to_order)
    elif usr_menu_choice == 2:
        if TAB == 0:
            print("No open tab...")
        else:
            print(f"Current tab: £{TAB:.2f}")
    elif usr_menu_choice == 3:
        handle_exit()
        print("Thank you and goodbye!")
        DONE = True

CLIENT_SOCK.close()
