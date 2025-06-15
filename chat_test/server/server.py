import socket
import threading
from datetime import datetime
from client.config import get_db_connection
import mysql.connector
import bcrypt

HOST = '192.168.1.17'  # IP LAN của bạn
PORT = 12345

clients = {}       # conn -> room_id
usernames = {}     # conn -> username
room_messages = {} # room_id -> list of messages
rooms = {}         # room_id -> list of conn

def broadcast(message, room_id=None, sender_conn=None):
    disconnected_clients = []
    for client, client_room in list(clients.items()):
        if client_room == room_id:
            try:
                client.send((message + '\n').encode())  # ✅ thêm \n để phân biệt tin
            except Exception as e:
                print(f"[!] Lỗi gửi tới client: {e}")
                disconnected_clients.append(client)

    for client in disconnected_clients:
        client.close()
        clients.pop(client, None)
        usernames.pop(client, None)

def handle_client(conn, addr):
    print(f"[+] Kết nối từ {addr}")

    try:
        room_data = conn.recv(1024).decode().strip()

        if '|' not in room_data:
            conn.send("Lỗi định dạng kết nối (cần room_id|username).".encode())
            conn.close()
            return

        room_id, username = room_data.split('|', 1)
        usernames[conn] = username
        clients[conn] = room_id

        if room_id not in rooms:
            rooms[room_id] = []
        rooms[room_id].append(conn)

        if room_id not in room_messages:
            room_messages[room_id] = []

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        join_msg = f"system|{username} đã vào phòng {room_id}|{timestamp}"
        broadcast(join_msg, sender_conn=conn, room_id=room_id)

        for msg in room_messages[room_id]:
            try:
                conn.send((msg + '\n').encode())
            except:
                continue

        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    print(f"[!] Client {username} mất kết nối.")
                    break

                message = data.decode()

                # ✅ Tách timestamp
                display_time = datetime.now().strftime('%H:%M:%S')                   # hiển thị
                db_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')          # lưu DB

                full_msg = f"{username}|{message}|{display_time}"
                print(f"[Room {room_id}] {full_msg}")

                if message.strip() == "/quit":
                    break

                save_message_to_db(room_id, username, message, db_timestamp)
                room_messages[room_id].append(full_msg)
                broadcast(full_msg, sender_conn=conn, room_id=room_id)

            except ConnectionResetError:
                print(f"[!] Mất kết nối đột ngột từ {username}.")
                break
            except Exception as e:
                print(f"[!] Lỗi nhận dữ liệu từ {username}: {e}")
                break

    finally:
        conn.close()
        print(f"[-] Ngắt kết nối từ {addr}")

        room_id = clients.get(conn)
        username = usernames.get(conn, "???")

        if room_id:
            if conn in rooms.get(room_id, []):
                rooms[room_id].remove(conn)
                if not rooms[room_id]:
                    del rooms[room_id]
            clients.pop(conn, None)
            usernames.pop(conn, None)

            # ✅ Gửi thông báo rời phòng
            display_time = datetime.now().strftime('%H:%M:%S')
            leave_msg = f"system|{username} đã rời phòng|{display_time}"
            broadcast(leave_msg, room_id=room_id)

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[+] Server đang chạy tại {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

def save_message_to_db(room_code, username, content, timestamp):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()

        cursor.execute("SELECT id FROM rooms WHERE name = %s", (room_code,))
        room_result = cursor.fetchone()

        if user_result and room_result:
            user_id = user_result[0]
            room_id = room_result[0]

            cursor.execute("""
                INSERT INTO messages (room_id, user_id, content, timestamp)
                VALUES (%s, %s, %s, %s)
            """, (room_id, user_id, content, timestamp))

            conn.commit()
        else:
            if not user_result:
                print(f"[DB WARNING] Username '{username}' không tồn tại.")
            if not room_result:
                print(f"[DB WARNING] Room '{room_code}' không tồn tại.")
    except Exception as e:
        print(f"[DB ERROR] Lỗi khi lưu tin nhắn: {e}")
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="uyen893605",
        database="chat_app1"
    )

if __name__ == "__main__":
    start_server()
