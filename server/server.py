import socket
import threading
from datetime import datetime

HOST = '127.0.0.1'
PORT = 12345

clients = {}  # conn -> room_id
usernames = {}  # Ánh xạ kết nối -> tên người dùng
room_messages = {}  # room_id -> list of messages
rooms = {}            # room_id -> list of conn

# Gửi tin nhắn đến tất cả client trừ người gửi/ Thông báo vào phòng
def broadcast(message, room_id=None, sender_conn=None):
    disconnected_clients = []
    for client, client_room in list(clients.items()):
        if client_room == room_id:
            try:
                client.send(message.encode())
            except Exception as e:
                print(f"[!] Lỗi gửi tới client: {e}")
                disconnected_clients.append(client)

    # Xóa client bị lỗi khỏi danh sách
    for client in disconnected_clients:
        client.close()
        clients.pop(client, None)
        usernames.pop(client, None)

# ✅ Hàm xử lý mỗi client khi kết nối đến server
def handle_client(conn, addr):
    print(f"[+] Kết nối từ {addr}")

    try:
        # ✅ Bước 1: Nhận dòng định danh duy nhất từ client: room_id|username
        room_data = conn.recv(1024).decode().strip()

        if '|' not in room_data:
            conn.send("Lỗi định dạng kết nối (cần room_id|username).".encode())
            conn.close()
            return

        # ✅ Tách room_id và username từ dòng nhận được
        room_id, username = room_data.split('|', 1)
        usernames[conn] = username  # Ghi nhớ username
        clients[conn] = room_id     # Ghi nhớ phòng của client

        # ✅ Thêm client vào danh sách phòng
        if room_id not in rooms:
            rooms[room_id] = []
        rooms[room_id].append(conn)

        # ✅ Khởi tạo lịch sử tin nhắn nếu chưa có
        if room_id not in room_messages:
            room_messages[room_id] = []

        # ✅ Gửi thông báo hệ thống khi có người mới vào phòng
        timestamp = datetime.now().strftime('%H:%M:%S')
        join_msg = f"system|{username} đã vào phòng {room_id}|{timestamp}"
        broadcast(join_msg, sender_conn=conn, room_id=room_id)

        # ✅ Gửi lại toàn bộ lịch sử tin nhắn của phòng cho client mới
        for msg in room_messages[room_id]:
            try:
                conn.send(msg.encode())
            except:
                continue

        # ✅ Vòng lặp chính nhận tin nhắn từ client
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    print(f"[!] Client {username} mất kết nối.")
                    break

                message = data.decode()
                timestamp = datetime.now().strftime('%H:%M:%S')
                full_msg = f"{username}|{message}|{timestamp}"
                print(f"[Room {room_id}] {full_msg}")

                if message.strip() == "/quit":
                    break

                room_messages[room_id].append(full_msg)
                broadcast(full_msg, sender_conn=conn, room_id=room_id)

            except ConnectionResetError:
                print(f"[!] Mất kết nối đột ngột từ {username} (ConnectionResetError).")
                break
            except Exception as e:
                print(f"[!] Lỗi nhận dữ liệu từ {username}: {e}")
                break


    finally:
        # ✅ Ngắt kết nối, xóa client khỏi danh sách
        conn.close()
        print(f"[-] Ngắt kết nối từ {addr}")

        room_id = clients.get(conn)
        username = usernames.get(conn, "???")

        if room_id:
            if conn in rooms.get(room_id, []):
                rooms[room_id].remove(conn)
                if not rooms[room_id]:  # Nếu phòng rỗng thì xóa phòng
                    del rooms[room_id]
            del clients[conn]
            del usernames[conn]

            # ✅ Gửi thông báo người dùng rời phòng
            timestamp = datetime.now().strftime('%H:%M:%S')
            leave_msg = f"system|{username} đã rời phòng|{timestamp}"
            broadcast(leave_msg, room_id=room_id)

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[+] Server đang chạy tại {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
