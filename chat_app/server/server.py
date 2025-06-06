import socket
import threading
from server.client_handler import handle_client
from config import HOST, PORT, MAX_CONNECTIONS, SYSTEM_MESSAGE

clients = {}  # Dictionary để lưu client_socket và username
chat_history = "chat_history.txt"  # File lưu lịch sử chat

def broadcast(message, sender_socket=None):
    with open(chat_history, "a") as file:
        file.write(message + "\n")  # Lưu tin nhắn vào file
    for client_socket in clients.keys():
        if client_socket != sender_socket:
            try:
                client_socket.sendall(message.encode())
            except:
                del clients[client_socket]

def send_online_users():
    online_users = ", ".join(clients.values())
    for client_socket in clients.keys():
        try:
            client_socket.sendall(f"{SYSTEM_MESSAGE} Online users: {online_users}".encode())
        except:
            del clients[client_socket]

def handle_new_connection(client_socket, addr):
    try:
        username = client_socket.recv(1024).decode()  # Nhận tên người dùng từ client
        clients[client_socket] = username
        broadcast(f"{SYSTEM_MESSAGE} {username} has joined the chat.")
        send_online_users()
        thread = threading.Thread(target=handle_client, args=(client_socket, broadcast, clients))
        thread.start()
    except Exception as e:
        print(f"[ERROR] {e}")
        client_socket.close()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(MAX_CONNECTIONS)
print(f"[SERVER] Listening on {HOST}:{PORT}...")

try:
    while True:
        client_socket, addr = server.accept()
        print(f"[NEW CONNECTION] {addr} connected.")
        handle_new_connection(client_socket, addr)
except KeyboardInterrupt:
    print("[SERVER] Shutting down...")
finally:
    server.close()