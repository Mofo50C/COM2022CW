# COM2022CW
Bar Tab Protocol for COM2022 coursework

---

## Usage

- Change server address in common.py and client address in client.py

- Run server first then in another shell run client.

- Follow menu instructions on client

---

## Testing Reliable Data Transfer

These tests are only ran on localhost and simulates packet loss. They internally conduct tests 5, 6 and 7 from the protocol design document. Run tests with:

`python rdt_test.py`

The implementation for the tests are in rdt_test_receiver.p and rdt_test_sender.py and simulate a "sender" and a "receiver".
