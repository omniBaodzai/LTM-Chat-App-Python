import socket
import threading

HOST = '127.0.0.1'
PORT = 12345

clients = []

def handle_client(conn, addr):
    print(f"[+] Kết nối từ {addr}")
    while True:
        try:
            message = conn.recv(1024).decode()
            if not message:
                break
            print(f"[{addr}] >> {message}")  # <-- in ra message từ client
            broadcast(message, conn)
        except:
            break
    conn.close()
    clients.remove(conn)
    print(f"[-] Ngắt kết nối từ {addr}")

def broadcast(message, sender_conn):
    for client in clients:
        if client != sender_conn:
            try:
                client.send(message.encode())
            except:
                client.close()
                clients.remove(client)

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[+] Server đang lắng nghe tại {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        clients.append(conn)
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start_server()
