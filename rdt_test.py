from threading import Thread

import rdt_test_receiver as r_test
import rdt_test_sender as s_test

def main():
    r_thread = Thread(target=r_test.main)
    s_thread = Thread(target=s_test.main)
    r_thread.start()
    s_thread.start()
    while r_thread.is_alive():
        pass

main()
