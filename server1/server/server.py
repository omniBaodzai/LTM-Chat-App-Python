import socket
import threading
from datetime import datetime
from config import get_db_connection
import mysql.connector
import json  # ✅ Dùng JSON để truyền tin nhắn an toàn

HOST = '127.0.0.1'  # nên thay bằng IP LAN của máy chủ nếu muốn kết nối từ các máy khác
PORT = 12345
MAX_ROOM_CACHE = 200  # ✅ Giới hạn số tin nhắn trong bộ nhớ mỗi phòng

clients = {}         # conn -> room_id
usernames = {}       # Ánh xạ kết nối -> tên người dùng
room_messages = {}   # room_id -> list of messages
rooms = {}           # room_id -> list of conn

# Gửi tin nhắn đến tất cả client trừ người gửi/ Thông báo vào phòng
def broadcast(message_json, room_id=None, sender_conn=None):
    disconnected_clients = []
    encoded_message = (message_json + '\n').encode('utf-8')  # ✅ encode trước 1 lần
    for client, client_room in list(clients.items()):
        if client_room == room_id:
            try:
                client.send(encoded_message)
            except Exception as e:
                print(f"[!] Lỗi gửi tới client: {e}")
                disconnected_clients.append(client)

    # ✅ Gỡ socket bị lỗi ra khỏi toàn bộ dữ liệu
    for client in disconnected_clients:
        try:
            client.close()
        except:
            pass
        clients.pop(client, None)
        usernames.pop(client, None)
        if client in rooms.get(room_id, []):
            rooms[room_id].remove(client)

# ✅ Hàm xử lý mỗi client khi kết nối đến server
def handle_client(conn, addr):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [+] Kết nối từ {addr}")
    conn.settimeout(600)  # Tự động đóng nếu client không gửi dữ liệu sau 10 phút

    try:
        try:
            room_data = conn.recv(1024).decode('utf-8').strip()
        except Exception as e:
            print(f"[!] Không nhận được dữ liệu đầu vào từ {addr}: {e}")
            conn.close()
            return

        if '|' not in room_data:
            conn.send("Lỗi định dạng kết nối (cần room_id|username).".encode())
            conn.close()
            return

        room_id, username = room_data.split('|', 1)
        if any(un == username and clients[c] == room_id for c, un in usernames.items()):
            conn.send("Tên người dùng đã được sử dụng trong phòng này. Vui lòng chọn tên khác.".encode())
            conn.close()
            return

        usernames[conn] = username
        clients[conn] = room_id

        if room_id not in rooms:
            rooms[room_id] = []
        rooms[room_id].append(conn)

        # ✅ Khởi tạo lịch sử tin nhắn nếu chưa có
        if room_id not in room_messages:
            room_messages[room_id] = []
            try:
                conn_db = get_db_connection()
                cursor = conn_db.cursor()
                cursor.execute("SELECT name FROM rooms")
                print("[DEBUG] Các phòng hiện có trong DB:", [r[0] for r in cursor.fetchall()])

                # ✅ Giới hạn số tin nhắn nạp về
                query = """
                    SELECT u.username, m.content, m.timestamp
                    FROM messages m
                    JOIN users u ON m.user_id = u.id
                    JOIN rooms r ON m.room_id = r.id
                    WHERE r.name = %s
                    ORDER BY m.timestamp ASC
                    LIMIT 100
                """
                cursor.execute(query, (room_id,))
                rows = cursor.fetchall()
                print(f"[DB] Đã nạp {len(rows)} tin nhắn từ DB cho phòng {room_id}")
                for sender, content, timestamp in rows:
                    time_str = timestamp.strftime('%H:%M:%S')
                    msg_obj = {"sender": sender, "content": content, "timestamp": time_str}
                    room_messages[room_id].append(msg_obj)

                cursor.close()
                conn_db.close()
            except Exception as e:
                print(f"[DB ERROR] Không thể nạp lịch sử: {e}")

        # ✅ Gửi thông báo hệ thống khi có người mới vào phòng
        timestamp = datetime.now().strftime('%H:%M:%S')
        join_obj = {"sender": "system", "content": f"{username} đã vào phòng {room_id}", "timestamp": timestamp}
        broadcast(json.dumps(join_obj), sender_conn=conn, room_id=room_id)

        # ✅ Gửi lại toàn bộ lịch sử tin nhắn của phòng cho client mới
        try:
            conn.send("__history_start__\n".encode('utf-8'))
            for msg in room_messages[room_id]:
                conn.send((json.dumps(msg) + '\n').encode('utf-8'))
            conn.send("__history_end__\n".encode('utf-8'))
        except:
            print(f"[!] Không gửi được lịch sử tới {username}")

        # ✅ Vòng lặp chính nhận tin nhắn từ client
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    print(f"[!] Client {username} mất kết nối.")
                    break

                message = data.decode().strip()
                display_time = datetime.now().strftime('%H:%M:%S')
                db_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if message.strip() == "/quit":
                    break

                full_obj = {"sender": username, "content": message, "timestamp": display_time}
                print(f"[Room {room_id}] {username}: {message} [{display_time}]")

                save_message_to_db(room_id, username, message, db_timestamp)
                room_messages[room_id].append(full_obj)

                # ✅ Giới hạn số tin nhắn trong bộ nhớ
                if len(room_messages[room_id]) > MAX_ROOM_CACHE:
                    room_messages[room_id] = room_messages[room_id][-MAX_ROOM_CACHE:]

                broadcast(json.dumps(full_obj), sender_conn=conn, room_id=room_id)

            except ConnectionResetError:
                print(f"[!] Mất kết nối đột ngột từ {username} (ConnectionResetError).")
                break
            except Exception as e:
                print(f"[!] Lỗi nhận dữ liệu từ {username}: {e}")
                break

    finally:
        room_id = clients.get(conn)
        username = usernames.get(conn, "???")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] [-] {username} ({addr}) đã rời khỏi phòng.")
        conn.close()

        if room_id:
            if conn in rooms.get(room_id, []):
                rooms[room_id].remove(conn)
                if not rooms[room_id]:
                    del rooms[room_id]
            clients.pop(conn, None)
            usernames.pop(conn, None)

            leave_time = datetime.now().strftime('%H:%M:%S')
            leave_obj = {"sender": "system", "content": f"{username} đã rời phòng", "timestamp": leave_time}
            broadcast(json.dumps(leave_obj), room_id=room_id)

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
                print(f"[DB WARNING] Username '{username}' không tồn tại trong bảng users.")
            if not room_result:
                print(f"[DB WARNING] Room code '{room_code}' không tồn tại trong bảng rooms.")
    except Exception as e:
        print(f"[DB ERROR] Lỗi khi lưu tin nhắn: {e}")
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def room_exists_in_db(room_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM rooms WHERE name = %s", (room_code,))
        result = cursor.fetchone()
        return bool(result)
    except:
        return False
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# server.py không nên tự chạy, chỉ cung cấp hàm start_server
