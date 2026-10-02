import socket
import json
import struct


# ---------------------------------------------------------
# SEND JSON MESSAGE
# ---------------------------------------------------------


def send_message(sock, message):

    json_data = json.dumps(message)

    data = json_data.encode("utf-8")

    message_length = len(data)

    # 4-byte length header
    length_header = struct.pack("!I", message_length)

    # Send header
    sock.sendall(length_header)

    # Send JSON data
    sock.sendall(data)


# ---------------------------------------------------------
# RECEIVE EXACT NUMBER OF BYTES
# ---------------------------------------------------------


def receive_exactly(sock, number_of_bytes):

    data = b""

    while len(data) < number_of_bytes:
        chunk = sock.recv(number_of_bytes - len(data))

        if not chunk:
            raise ConnectionError("Peer disconnected while receiving data.")

        data += chunk

    return data


# ---------------------------------------------------------
# RECEIVE JSON MESSAGE
# ---------------------------------------------------------


def receive_message(sock):

    # First receive 4-byte length
    length_header = receive_exactly(sock, 4)

    # Convert bytes to integer
    message_length = struct.unpack("!I", length_header)[0]

    # Receive JSON payload
    data = receive_exactly(sock, message_length)

    # Convert JSON to Python dictionary
    message = json.loads(data.decode("utf-8"))

    return message
