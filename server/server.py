import socket
import threading

HOST = '127.0.0.1'
PORT = 12345

# Tạo socket TCP server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"🟢 Server đang chạy tại {HOST}:{PORT}, chờ nhiều kết nối...")

# Hàm xử lý từng client trong một luồng riêng
def handle_client(conn, addr):
    print(f"✅ Kết nối mới từ: {addr}")
    conn.send("Chào mừng bạn đến với server chat!".encode())

    while True:
        try:
            data = conn.recv(1024).decode()
            if not data:
                break
            print(f"[{addr}] 👤 Client: {data}")
            reply = input(f"[Bạn trả lời {addr}]: ")
            conn.send(reply.encode())
        except:
            break

    print(f"❌ Kết nối đóng từ: {addr}")
    conn.close()

# Vòng lặp chính chờ kết nối mới
while True:
    conn, addr = server_socket.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()
