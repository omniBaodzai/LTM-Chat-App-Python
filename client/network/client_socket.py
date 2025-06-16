import socket
import json
from client.utils.config import SERVER_IP, SERVER_PORT

class ClientSocket:
    def __init__(self):
        self.sock = None
        self.connected = False

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SERVER_IP, SERVER_PORT))
            self.connected = True
            return True, "Connected to server"
        except Exception as e:
            self.connected = False
            return False, f"Connection error: {e}"

    def send_request(self, request):
        if not self.connected:
            return False, "Not connected to server"
        
        try:
            self.sock.send(json.dumps(request).encode())
            response = self.sock.recv(1024).decode().strip()
            return True, json.loads(response)
        except Exception as e:
            return False, f"Request error: {e}"

    def close(self):
        if self.sock:
            self.sock.close()
            self.connected = False
