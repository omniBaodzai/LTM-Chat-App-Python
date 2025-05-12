import socket

HOST = '127.0.0.1'  # Địa chỉ IP của server (localhost)
PORT = 12345        # Cổng kết nối (giống với server)

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client_socket.connect((HOST, PORT))
    print(f"🔵 Đã kết nối đến server tại {HOST}:{PORT}")

    while True:
        msg = input("👨‍💻 Bạn: ")
        if not msg:
            break
        client_socket.send(msg.encode())

        data = client_socket.recv(1024).decode()
        if not data:
            print("⚠️ Server đã ngắt kết nối.")
            break
        print(f"👤 Server: {data}")

except ConnectionRefusedError:
    print("❌ Không thể kết nối tới server. Hãy chắc chắn rằng server đang chạy.")
finally:
    client_socket.close()
