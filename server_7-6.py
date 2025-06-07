import socket
import threading

clients = []

def broadcast(message, conn=None):
    for client in clients:
        if client != conn:  # tránh gửi lại cho chính người gửi
            try:
                client.send(message)
            except:
                client.close()
                clients.remove(client)

def handle_client(conn, addr):
    print(f"📲 Client {addr} connected.")
    clients.append(conn)
    try:
        while True:
            msg = conn.recv(1024)
            if not msg:
                break
            broadcast(msg, conn)
    except:
        pass
    finally:
        print(f"❌ Client {addr} disconnected.")
        clients.remove(conn)
        conn.close()

def handle_server_input():
    while True:
        msg = input()
        if msg.strip():
            full_msg = f"💻 SERVER: {msg}".encode()
            broadcast(full_msg)

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 12345))
    server.listen()
    print("🟢 Server đang lắng nghe tại cổng 12345...")

    threading.Thread(target=handle_server_input, daemon=True).start()

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

start_server()
