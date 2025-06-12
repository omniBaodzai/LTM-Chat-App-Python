import socket
import json
from client.utils.config import SERVER_IP, SERVER_PORT

class ClientSocket:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False

    def connect(self):
        try:
            self.socket.connect((SERVER_IP, SERVER_PORT))
            self.connected = True
            return True, "Connected to server"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def send_request(self, request):
        if not self.connected:
            return False, "Not connected to server"
        
        try:
            self.socket.send(json.dumps(request).encode())
            response = self.socket.recv(1024).decode()
            return True, json.loads(response)
        except Exception as e:
            return False, f"Request failed: {e}"

    def close(self):
        if self.connected:
            self.socket.close()
            self.connected = False