# COM2022CW
Bar Tab Protocol for COM2022 coursework

---

## Usage

- Requires python 3.8+

- Change server address in common.py and client address in client.py (optional)

- Run server.py first then in another shell run client.py

- Follow menu instructions on client

---

## Proprietary Extension

By default, the server and client run in compatibility mode, and they are interoperable with other implementations of the protocol.

To enable the propietary extensions, change COMPAT_MODE to False in common.py

(Note: this will mean that this implementation of the server and client will only work with each other.)

---

## Testing Reliable Data Transfer

These tests are only ran on localhost and simulates packet loss. They internally conduct tests 5, 6 and 7 from the protocol design document. 

- Run the receiver first on a separate terminal with `python rdt_test_receiver.py`.
- Then run the sender after on another terminal with `python rdt_test_sender.py`.
