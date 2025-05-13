import socket

HOST = '127.0.0.1'
PORT = 12345

def generate_reply(message):
    message = message.lower()
    
    if "Xin chào" in message:
        return "Chào bạn! Tôi là server chatbot 🤖"
    elif "Tên của bạn là gì" in message or "bạn tên gì" in message:
        return "Tôi là server đơn giản, chưa có tên 😅"
    elif "Bạn có khỏe không" in message:
        return "Tôi luôn khỏe và sẵn sàng phục vụ bạn! 💪"
    elif "Bạn làm được gì" in message:
        return "Tôi có thể trò chuyện đơn giản với bạn 🤗"
    elif "Hello" in message or "hi" in message:
        return "Hello bạn! 👋"
    elif "exit" in message:
        return "Tạm biệt! Hẹn gặp lại 👋"
    else:
        return f"Bạn vừa nói: {message}"


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"🟢 Server đang chạy tại {HOST}:{PORT}, chờ kết nối...")

conn, addr = server_socket.accept()
print(f"✅ Kết nối từ: {addr}")

try:
    while True:
        data = conn.recv(1024).decode()
        if not data:
            print("⚠️ Không nhận được dữ liệu. Đóng kết nối.")
            break

        print(f" Client: {data}")

        if data.lower() == "exit":
            conn.send("Tạm biệt! 👋".encode())
            break

        reply = generate_reply(data)
        conn.send(reply.encode())
finally:
    conn.close()
    server_socket.close()
    print("🔒 Server đã đóng kết nối.")
