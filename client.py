import socket
import rsa
from common import DRINKS, BTPPacket, SERVER_ADDR, RSA_BITS
from rdt import RDTConnection

DRINK_MENU = "./barMenu.txt"
CLIENT_ADDR = ("127.0.0.1", 45561)
CLIENT_COMPAT_MODE = True
CLIENT_SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
CLIENT_SOCK.bind(CLIENT_ADDR)
C_PUB_KEY, C_PRIV_KEY = rsa.newkeys(RSA_BITS, accurate=True)
C_KEY_PEM = C_PUB_KEY.save_pkcs1()
CLIENT_ID = None
S_KEY = None
TAB = 0


def encrypt(data):
    return rsa.encrypt(data, S_KEY)

def decrypt(data):
    return rsa.decrypt(data, C_PRIV_KEY)


class CompatClient:
    def __init__(self):
        self.conn = RDTConnection(CLIENT_SOCK, SERVER_ADDR)
    
    def finish_request(self):
        print("FINISHING REQUEST")
        while True:
            sndpkt = BTPPacket(fin=1)
            self._send(sndpkt)
            pkt_header, _ = self._recv()
            if pkt_header.fin == 1 and pkt_header.ack == 1:
                break

    def open_tab(self):
        print("OPENING TAB")
        message = "OPEN"
        message = encrypt(message.encode("ASCII"))
        sndpkt = BTPPacket(message)
        self._send(sndpkt)
        pkt_header, pkt_payload = self._recv()
        resp = decrypt(pkt_payload).decode("ASCII").split(" ")
        cid = int(resp[1])
        print(f"TAB OPENED: {cid}")
        self.finish_request()
        return cid
    
    def close_tab(self):
        print("CLOSING TAB")
        auth_msg = f"ID {CLIENT_ID}\r\n"
        message = auth_msg + f"CLOSE"
        message = encrypt(message.encode("ASCII"))
        sndpkt = BTPPacket(message)
        self._send(sndpkt)
        pkt_header, pkt_payload = self._recv()
        resp = decrypt(pkt_payload).decode("ASCII").split(" ")
        final_tab = float(resp[1])
        self.finish_request()
        return final_tab

    def order(self, drink, quantity):
        print("ORDERING")
        auth_msg = f"ID {CLIENT_ID}\r\n"
        message = auth_msg + f"ADD {drink.id} {quantity}"
        message = encrypt(message.encode("ASCII"))
        sndpkt = BTPPacket(message)
        self._send(sndpkt)
        pkt_header, pkt_payload = self._recv()
        resp = decrypt(pkt_payload).decode("ASCII").split(" ")
        tab = float(resp[1])
        self.finish_request()
        return tab
    
    def exchange_rsa(self):
        print("EXCHANGING RSA")
        while True:
            sndpkt = BTPPacket(C_KEY_PEM, rsa=1)
            self._send(sndpkt)
            pkt_header, pkt_payload = self._recv()
            if pkt_header.rsa == 1 and pkt_header.ack == 1:
                break
        
        self.finish_request()
        return rsa.PublicKey.load_pkcs1(pkt_payload)

    
    def _send(self, sndpkt):
        self.conn.send(sndpkt)
    
    def _recv(self):
        return self.conn.recv()


class Client(CompatClient):
    def order(self, orders):
        if len(orders) == 1:
            drink = orders.keys()[0]
            quantity = orders[drink]
            return super().order(drink, quantity)
        
        print("ORDERING MULTIPLE")
        auth_msg = f"ID {CLIENT_ID}\r\n"
        message = auth_msg + f"ADD\r\n"
        
        for drink, quantity in orders:
            message += f"{drink.id}"
            if quantity > 1:
                message += f" {quantity}"
            
            message += "\r\n"

        message = encrypt(message.encode("ASCII"))
        sndpkt = BTPPacket(message)
        self._send(sndpkt)
        pkt_header, pkt_payload = self._recv()
        resp = decrypt(pkt_payload).decode("ASCII").split(" ")
        tab = float(resp[1])
        self.finish_request()
        return tab


def handle_order(orders):
    global TAB
    print("Ordering...")

    if CLIENT_COMPAT_MODE:
        for drink, quantity in orders.values():
            client = CompatClient()
            TAB = client.order(drink, quantity)
    else:
        client = Client()
        TAB = client.order(orders)
    
    print(f"Total tab: £{TAB:.2f}")

def handle_exit():
    global TAB
    if CLIENT_ID == 0 or TAB == 0:
        print("No open tab to close...")
        return

    print("Closing tab...")
    client = CompatClient()
    TAB = client.close_tab()
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


def main_menu():
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
                        usr_drink_choice = f"0{usr_drink_choice}"
                        print(usr_drink_choice)
                        if usr_drink_choice in DRINKS:
                            break
                    except ValueError as e:
                        if usr_drink_choice.upper() in ["X", "S"]:
                            finish_order = True
                            break
                
                if not finish_order:
                    quantity = 0
                    while True:
                        try:
                            quantity = int(input("How many? "))
                            if quantity > 0 and quantity <= 50:
                                break
                        except ValueError as e:
                            pass
                            
                    if usr_drink_choice in drinks_to_order:
                        drink, prev_q = drinks_to_order[usr_drink_choice]
                        drinks_to_order[usr_drink_choice] = (drink, prev_q + quantity)
                    else:
                        drinks_to_order[usr_drink_choice] = (DRINKS[usr_drink_choice], quantity)
                else:
                    if usr_drink_choice.upper() == "S" and len(drinks_to_order) > 0:
                        handle_order(drinks_to_order)
    
        elif usr_menu_choice == 2:
            print(f"Current tab: £{TAB:.2f}")

        elif usr_menu_choice == 3:
            handle_exit()
            print("Thank you and goodbye!")
            DONE = True

def main():
    global S_KEY, CLIENT_ID

    if S_KEY is None:
        client = CompatClient()
        S_KEY = client.exchange_rsa()

    if CLIENT_ID is None:
        client = CompatClient()
        CLIENT_ID = client.open_tab()

    main_menu()
    CLIENT_SOCK.close()


main()