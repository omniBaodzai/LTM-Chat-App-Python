import socket

HOST = '127.0.0.1'  
PORT = 12345        

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
print(f"🔌 Đã kết nối tới server {HOST}:{PORT}")

try:
    while True:
        msg = input("👩 Bạn: ")
        if not msg:
            continue
        client_socket.send(msg.encode())

        data = client_socket.recv(1024).decode()
        print(f"🤖 Server: {data}")

        if msg.lower() == "exit":
            break
finally:
    client_socket.close()
    print("🔒 Đã ngắt kết nối.")
