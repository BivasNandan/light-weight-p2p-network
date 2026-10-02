import socket
import threading
import uuid
import os

from protocol import send_message, receive_message


class P2PNode:
    def __init__(self, peer_name, host="0.0.0.0", port=5000, event_callback=None):
        self.peer_name = peer_name
        self.host = host
        self.port = port

        # Unique ID for this peer
        self.peer_id = str(uuid.uuid4())

        # Connected peers
        self.peers = {}

        # Protect peer dictionary
        self.peers_lock = threading.Lock()

        # GUI callback
        self.event_callback = event_callback

        # Server state
        self.running = False

        # Downloads folder
        os.makedirs("downloads", exist_ok=True)

        # Create TCP server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server_socket.bind((self.host, self.port))

        self.server_socket.listen(10)

    # =========================================================
    # EVENT / LOG
    # =========================================================

    def log(self, message):

        print(f"{self.peer_name}: {message}")

        if self.event_callback:
            self.event_callback(f"{self.peer_name}: {message}")

    # =========================================================
    # START SERVER
    # =========================================================

    def start(self):

        if self.running:
            self.log("Server is already running.")
            return

        self.running = True

        threading.Thread(target=self.accept_connections, daemon=True).start()

        self.log(f"Server started on {self.host}:{self.port}")

    # =========================================================
    # STOP SERVER
    # =========================================================

    def stop(self):

        if not self.running:
            return

        self.running = False

        # Close connected peers
        with self.peers_lock:
            peer_sockets = [info["socket"] for info in self.peers.values()]

            self.peers.clear()

        for peer_socket in peer_sockets:
            try:
                peer_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass

            try:
                peer_socket.close()
            except Exception:
                pass

        # Close server socket
        try:
            self.server_socket.close()
        except Exception:
            pass

        self.log("Server stopped.")

    # =========================================================
    # ACCEPT CONNECTIONS
    # =========================================================

    def accept_connections(self):

        while self.running:
            try:
                client_socket, address = self.server_socket.accept()

                self.log(f"Connection from {address[0]}:{address[1]}")

                threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True,
                ).start()

            except OSError:
                break

            except Exception as e:
                if self.running:
                    self.log(f"Error accepting connection: {e}")

    # =========================================================
    # HANDLE CONNECTION
    # =========================================================

    def handle_client(self, client_socket, address=None):

        peer_id = None

        try:
            while self.running:
                message = receive_message(client_socket)

                message_type = message.get("type")

                # -------------------------------------------------
                # HELLO
                # -------------------------------------------------

                if message_type == "hello":
                    peer_id = message.get("peer_id")

                    peer_name = message.get("peer_name")

                    peer_port = message.get("port")

                    peer_host = None

                    if address:
                        peer_host = address[0]

                    with self.peers_lock:
                        self.peers[peer_id] = {
                            "name": peer_name,
                            "host": peer_host,
                            "port": peer_port,
                            "socket": client_socket,
                        }

                    self.log(f"HELLO received from {peer_name}")

                    hello_ack = {
                        "type": "hello_ack",
                        "peer_id": self.peer_id,
                        "peer_name": self.peer_name,
                        "port": self.port,
                    }

                    send_message(client_socket, hello_ack)

                    self.log(f"Connected with {peer_name}")

                # -------------------------------------------------
                # HELLO ACK
                # -------------------------------------------------

                elif message_type == "hello_ack":
                    peer_id = message.get("peer_id")

                    peer_name = message.get("peer_name")

                    peer_port = message.get("port")

                    peer_host = None

                    try:
                        peer_host = client_socket.getpeername()[0]
                    except Exception:
                        pass

                    with self.peers_lock:
                        self.peers[peer_id] = {
                            "name": peer_name,
                            "host": peer_host,
                            "port": peer_port,
                            "socket": client_socket,
                        }

                    self.log(f"Connected to {peer_name}")

                # -------------------------------------------------
                # TEXT
                # -------------------------------------------------

                elif message_type == "text":
                    sender_name = message.get("sender_name")

                    text = message.get("text")

                    self.log(f"Message from {sender_name}: {text}")

                # -------------------------------------------------
                # FILE
                # -------------------------------------------------

                elif message_type == "file":
                    sender_name = message.get("sender_name")

                    filename = message.get("filename")

                    filesize = message.get("filesize")

                    self.log(f"Receiving {filename} from {sender_name}")

                    self.receive_file(client_socket, filename, filesize)

                else:
                    self.log(f"Unknown message type: {message_type}")

        except ConnectionError:
            self.log("Peer disconnected.")

        except Exception as e:
            if self.running:
                self.log(f"Connection error: {e}")

        finally:
            if peer_id is not None:
                with self.peers_lock:
                    self.peers.pop(peer_id, None)

            try:
                client_socket.close()
            except Exception:
                pass

    # =========================================================
    # CONNECT TO PEER
    # =========================================================

    def connect_to_peer(self, peer_host, peer_port):

        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            peer_socket.settimeout(5)

            peer_socket.connect((peer_host, peer_port))

            peer_socket.settimeout(None)

            self.log(f"Connected to {peer_host}:{peer_port}")

            self.send_hello(peer_socket)

            threading.Thread(
                target=self.handle_client,
                args=(peer_socket, (peer_host, peer_port)),
                daemon=True,
            ).start()

            return peer_socket

        except ConnectionRefusedError:
            self.log("Connection refused. Is the other peer running?")

        except socket.timeout:
            self.log("Connection timed out.")

        except Exception as e:
            self.log(f"Error connecting: {e}")

        return None

    # =========================================================
    # SEND HELLO
    # =========================================================

    def send_hello(self, peer_socket):

        message = {
            "type": "hello",
            "peer_id": self.peer_id,
            "peer_name": self.peer_name,
            "port": self.port,
        }

        send_message(peer_socket, message)

        self.log("HELLO sent.")

    # =========================================================
    # SEND TEXT
    # =========================================================

    def send_text(self, peer_id, text):

        with self.peers_lock:
            peer = self.peers.get(peer_id)

        if peer is None:
            self.log("Peer not found.")
            return

        message = {
            "type": "text",
            "sender_id": self.peer_id,
            "sender_name": self.peer_name,
            "text": text,
        }

        try:
            send_message(peer["socket"], message)

            self.log(f"Message sent to {peer['name']} : {text}")

        except Exception as e:
            self.log(f"Error sending message: {e}")

    # =========================================================
    # SEND FILE
    # =========================================================

    def send_file(self, peer_id, file_path):

        with self.peers_lock:
            peer = self.peers.get(peer_id)

        if peer is None:
            self.log("Peer not found.")
            return

        if not os.path.isfile(file_path):
            self.log(f"File not found: {file_path}")

            return

        filename = os.path.basename(file_path)

        filesize = os.path.getsize(file_path)

        message = {
            "type": "file",
            "sender_id": self.peer_id,
            "sender_name": self.peer_name,
            "filename": filename,
            "filesize": filesize,
        }

        try:
            send_message(peer["socket"], message)

            self.log(f"Sending file {filename} ({filesize} bytes)")

            with open(file_path, "rb") as file:
                while True:
                    chunk = file.read(64 * 1024)

                    if not chunk:
                        break

                    peer["socket"].sendall(chunk)

            self.log(f"File sent successfully: {filename}")

        except Exception as e:
            self.log(f"Error sending file: {e}")

    # =========================================================
    # RECEIVE FILE
    # =========================================================

    def receive_file(self, peer_socket, filename, filesize):

        filename = os.path.basename(filename)

        download_path = os.path.join("downloads", filename)

        # Prevent overwriting
        if os.path.exists(download_path):
            name, extension = os.path.splitext(filename)

            counter = 1

            while os.path.exists(download_path):
                new_filename = f"{name}_{counter}{extension}"

                download_path = os.path.join("downloads", new_filename)

                counter += 1

        received = 0

        try:
            with open(download_path, "wb") as file:
                while received < filesize:
                    remaining = filesize - received

                    chunk_size = min(64 * 1024, remaining)

                    chunk = peer_socket.recv(chunk_size)

                    if not chunk:
                        raise ConnectionError("Peer disconnected during file transfer.")

                    file.write(chunk)

                    received += len(chunk)

            self.log(f"File received: {os.path.basename(download_path)}")

        except Exception as e:
            self.log(f"Error receiving file: {e}")

    # =========================================================
    # GET PEER SNAPSHOT
    # =========================================================

    def get_peers_snapshot(self):

        with self.peers_lock:
            return {peer_id: info.copy() for peer_id, info in self.peers.items()}
