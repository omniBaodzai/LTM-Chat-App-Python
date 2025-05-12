import socket

HOST = '127.0.0.1'
PORT = 12345

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"🟢 Server đang chạy tại {HOST}:{PORT}, chờ kết nối...")

conn, addr = server_socket.accept()
print(f"✅ Kết nối từ: {addr}")

while True:
    data = conn.recv(1024).decode()
    if not data:
        break
    print(f"👤 Client: {data}")
    
    msg = input("👨‍💻 Bạn: ")
    conn.send(msg.encode())

conn.close()
server_socket.close()
