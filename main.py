import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import queue

from p2p_node import P2PNode


class P2PGUI:
    def __init__(self, root):

        self.root = root
        self.root.title("P2P File Sharing Network")

        self.root.geometry("850x700")

        self.node = None

        # Thread-safe event queue
        self.event_queue = queue.Queue()

        # Peer IDs corresponding to listbox rows
        self.peer_ids = []

        self.create_widgets()

        # Periodic GUI updates
        self.process_events()
        self.refresh_peers()

        self.root.protocol("WM_DELETE_WINDOW", self.close_application)

    # =========================================================
    # CREATE GUI
    # =========================================================

    def create_widgets(self):

        title = tk.Label(
            self.root, text="P2P File Sharing Network", font=("Arial", 20, "bold")
        )

        title.pack(pady=10)

        # -----------------------------------------------------
        # LOCAL PEER
        # -----------------------------------------------------

        local_frame = tk.LabelFrame(self.root, text="Local Peer", padx=10, pady=10)

        local_frame.pack(fill="x", padx=15, pady=5)

        tk.Label(local_frame, text="Peer Name:").grid(row=0, column=0, padx=5, pady=5)

        self.name_entry = tk.Entry(local_frame, width=25)

        self.name_entry.grid(row=0, column=1, padx=5)

        self.name_entry.insert(0, "Alice")

        tk.Label(local_frame, text="Port:").grid(row=0, column=2, padx=5)

        self.port_entry = tk.Entry(local_frame, width=10)

        self.port_entry.grid(row=0, column=3, padx=5)

        self.port_entry.insert(0, "5000")

        self.start_button = tk.Button(
            local_frame, text="Start", width=10, command=self.start_node
        )

        self.start_button.grid(row=0, column=4, padx=5)

        self.stop_button = tk.Button(
            local_frame,
            text="Stop",
            width=10,
            command=self.stop_node,
            state=tk.DISABLED,
        )

        self.stop_button.grid(row=0, column=5, padx=5)

        # -----------------------------------------------------
        # REMOTE PEER
        # -----------------------------------------------------

        connect_frame = tk.LabelFrame(
            self.root, text="Connect to Peer", padx=10, pady=10
        )

        connect_frame.pack(fill="x", padx=15, pady=5)

        tk.Label(connect_frame, text="Remote IP:").grid(row=0, column=0, padx=5)

        self.ip_entry = tk.Entry(connect_frame, width=20)

        self.ip_entry.grid(row=0, column=1, padx=5)

        self.ip_entry.insert(0, "127.0.0.1")

        tk.Label(connect_frame, text="Remote Port:").grid(row=0, column=2, padx=5)

        self.remote_port_entry = tk.Entry(connect_frame, width=10)

        self.remote_port_entry.grid(row=0, column=3, padx=5)

        self.remote_port_entry.insert(0, "5001")

        self.connect_button = tk.Button(
            connect_frame, text="Connect", width=12, command=self.connect_peer
        )

        self.connect_button.grid(row=0, column=4, padx=5)

        # -----------------------------------------------------
        # CONNECTED PEERS
        # -----------------------------------------------------

        peer_frame = tk.LabelFrame(self.root, text="Connected Peers", padx=10, pady=10)

        peer_frame.pack(fill="both", padx=15, pady=5)

        self.peer_listbox = tk.Listbox(peer_frame, height=6, width=70)

        self.peer_listbox.pack(fill="both")

        # -----------------------------------------------------
        # MESSAGE
        # -----------------------------------------------------

        message_frame = tk.Frame(self.root)

        message_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(message_frame, text="Message:").pack(side="left")

        self.message_entry = tk.Entry(message_frame)

        self.message_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.send_button = tk.Button(
            message_frame, text="Send Message", command=self.send_text
        )

        self.send_button.pack(side="right")

        # -----------------------------------------------------
        # FILE
        # -----------------------------------------------------

        file_frame = tk.Frame(self.root)

        file_frame.pack(fill="x", padx=15, pady=5)

        self.file_label = tk.Label(file_frame, text="No file selected", anchor="w")

        self.file_label.pack(side="left", fill="x", expand=True)

        self.choose_button = tk.Button(
            file_frame, text="Choose File", command=self.choose_file
        )

        self.choose_button.pack(side="left", padx=5)

        self.send_file_button = tk.Button(
            file_frame, text="Send File", command=self.send_file
        )

        self.send_file_button.pack(side="left")

        self.selected_file = None

        # -----------------------------------------------------
        # EVENT LOG
        # -----------------------------------------------------

        log_frame = tk.LabelFrame(self.root, text="Event Log", padx=10, pady=10)

        log_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.log_text = tk.Text(log_frame, height=12, state=tk.DISABLED)

        self.log_text.pack(fill="both", expand=True)

    # =========================================================
    # LOG EVENT
    # =========================================================

    def add_log(self, message):

        self.log_text.config(state=tk.NORMAL)

        self.log_text.insert(tk.END, message + "\n")

        self.log_text.see(tk.END)

        self.log_text.config(state=tk.DISABLED)

    # =========================================================
    # CALLBACK FROM NETWORK THREADS
    # =========================================================

    def network_event(self, message):

        self.event_queue.put(message)

    # =========================================================
    # PROCESS EVENTS
    # =========================================================

    def process_events(self):

        while True:
            try:
                message = self.event_queue.get_nowait()

                self.add_log(message)

            except queue.Empty:
                break

        self.root.after(100, self.process_events)

    # =========================================================
    # START NODE
    # =========================================================

    def start_node(self):

        if self.node is not None:
            messagebox.showinfo("Already Running", "The peer is already running.")

            return

        name = self.name_entry.get().strip()

        if not name:
            messagebox.showerror("Error", "Enter a peer name.")

            return

        try:
            port = int(self.port_entry.get())

            if not (1 <= port <= 65535):
                raise ValueError

        except ValueError:
            messagebox.showerror("Error", "Enter a valid port.")

            return

        try:
            self.node = P2PNode(
                peer_name=name,
                host="0.0.0.0",
                port=port,
                event_callback=self.network_event,
            )

            self.node.start()

            self.start_button.config(state=tk.DISABLED)

            self.stop_button.config(state=tk.NORMAL)

            self.add_log(f"Peer {name} started on port {port}")

        except OSError as e:
            self.node = None

            messagebox.showerror("Port Error", f"Could not start peer:\n{e}")

    # =========================================================
    # STOP NODE
    # =========================================================

    def stop_node(self):

        if self.node is None:
            return

        self.node.stop()

        self.node = None

        self.peer_ids.clear()

        self.peer_listbox.delete(0, tk.END)

        self.stop_button.config(state=tk.DISABLED)

        self.start_button.config(state=tk.NORMAL)

    # =========================================================
    # CONNECT TO PEER
    # =========================================================

    def connect_peer(self):

        if self.node is None:
            messagebox.showwarning("Start Peer", "Start your peer first.")

            return

        host = self.ip_entry.get().strip()

        try:
            port = int(self.remote_port_entry.get())

        except ValueError:
            messagebox.showerror("Error", "Invalid remote port.")

            return

        # Connect in background thread
        threading.Thread(
            target=self._connect_worker, args=(host, port), daemon=True
        ).start()

    def _connect_worker(self, host, port):

        self.node.connect_to_peer(host, port)

    # =========================================================
    # GET SELECTED PEER
    # =========================================================

    def get_selected_peer_id(self):

        selection = self.peer_listbox.curselection()

        if not selection:
            messagebox.showwarning("Select Peer", "Select a connected peer first.")

            return None

        index = selection[0]

        if index >= len(self.peer_ids):
            return None

        return self.peer_ids[index]

    # =========================================================
    # SEND TEXT
    # =========================================================

    def send_text(self):

        if self.node is None:
            messagebox.showwarning("Start Peer", "Start your peer first.")

            return

        peer_id = self.get_selected_peer_id()

        if peer_id is None:
            return

        text = self.message_entry.get().strip()

        if not text:
            return

        self.node.send_text(peer_id, text)

        self.message_entry.delete(0, tk.END)

    # =========================================================
    # CHOOSE FILE
    # =========================================================

    def choose_file(self):

        file_path = filedialog.askopenfilename()

        if not file_path:
            return

        self.selected_file = file_path

        self.file_label.config(text=file_path)

    # =========================================================
    # SEND FILE
    # =========================================================

    def send_file(self):

        if self.node is None:
            messagebox.showwarning("Start Peer", "Start your peer first.")

            return

        peer_id = self.get_selected_peer_id()

        if peer_id is None:
            return

        if not self.selected_file:
            messagebox.showwarning("Choose File", "Choose a file first.")

            return

        # Send file in background
        threading.Thread(
            target=self.node.send_file, args=(peer_id, self.selected_file), daemon=True
        ).start()

    # =========================================================
    # REFRESH PEER LIST
    # =========================================================

    def refresh_peers(self):

        if self.node is not None:
            peers = self.node.get_peers_snapshot()

            new_ids = list(peers.keys())

            current_ids = self.peer_ids

            if new_ids != current_ids:
                self.peer_listbox.delete(0, tk.END)

                self.peer_ids = new_ids

                for peer_id in new_ids:
                    info = peers[peer_id]

                    host = info.get("host")

                    port = info.get("port")

                    name = info.get("name")

                    if host:
                        display = f"{name} ({host}:{port})"

                    else:
                        display = f"{name} (port {port})"

                    self.peer_listbox.insert(tk.END, display)

        self.root.after(500, self.refresh_peers)

    # =========================================================
    # CLOSE APPLICATION
    # =========================================================

    def close_application(self):

        if self.node is not None:
            self.node.stop()

        self.root.destroy()


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":
    root = tk.Tk()

    app = P2PGUI(root)

    root.mainloop()
