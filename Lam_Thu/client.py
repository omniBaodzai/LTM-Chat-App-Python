import socket

HOST = '127.0.0.1'
PORT = 12345

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
print("📲 Đã kết nối đến server.")

while True:
    msg = input("👨‍💻 Bạn: ")
    client_socket.send(msg.encode())

    data = client_socket.recv(1024).decode()
    print(f" Server: {data}")

client_socket.close()
