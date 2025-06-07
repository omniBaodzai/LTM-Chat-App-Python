import socket
import threading

# Kết nối CSDL (nếu dùng)
import mysql.connector

HOST = '192.168.1.12'
PORT = 12345

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print(f"✅ Server đang chạy tại {HOST}:{PORT}")

clients = []  # [(conn, addr, room_id, name)]
rooms = {}    # room_id -> list of client conn

# Kết nối MySQL (bạn phải bật XAMPP)
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="chat_app"
)
cursor = db.cursor()

def save_message_to_db(room_id, name, message):
    try:
        cursor.execute("INSERT INTO messages (room_id, sender, message) VALUES (%s, %s, %s)",
                       (room_id, name, message))
        db.commit()
    except Exception as e:
        print("❌ DB Error:", e)

def handle_client(conn, addr):
    print(f"🔌 Kết nối từ {addr}")
    try:
        # Tin nhắn đầu tiên phải chứa room_id và name
        join_msg = conn.recv(1024).decode()
        if not join_msg.startswith("[") or "]" not in join_msg:
            conn.send("❌ Sai định dạng tin nhắn đầu tiên!".encode())
            conn.close()
            return

        room_id = join_msg.split("]")[0][1:]  # [room1] -> room1
        name = join_msg.split("]")[1].split("đã")[0].strip()

        # Thêm vào danh sách phòng
        if room_id not in rooms:
            rooms[room_id] = []
        rooms[room_id].append(conn)
        clients.append((conn, addr, room_id, name))

        print(f"👤 {name} vào phòng [{room_id}]")

        broadcast(join_msg, room_id, exclude=conn)

        while True:
            msg = conn.recv(1024).decode()
            if not msg:
                break
            print(f"📨 {msg}")
            save_message_to_db(room_id, name, msg)
            broadcast(msg, room_id, exclude=None)

    except:
        pass
    finally:
        print(f"❌ Mất kết nối: {addr}")
        conn.close()
        # Xóa client khỏi danh sách
        clients[:] = [c for c in clients if c[0] != conn]
        if room_id in rooms:
            rooms[room_id] = [c for c in rooms[room_id] if c != conn]

def broadcast(msg, room_id, exclude=None):
    for client in rooms.get(room_id, []):
        if client != exclude:
            try:
                client.send(msg.encode())
            except:
                pass

while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()
