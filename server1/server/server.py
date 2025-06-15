import socket
import threading
from datetime import datetime
from config import get_db_connection
import mysql.connector


HOST = '127.0.0.1' #nên thay bằng IP LAN của máy chủ nếu muốn kết nối từ các máy khác
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
                client.send(message + '\n'.encode()) # Thêm '\n' để đảm bảo mỗi tin nhắn kết thúc bằng dòng mới
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
    #print(f"[+] Kết nối từ {addr}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [+] Kết nối từ {addr}")
    conn.settimeout(600)  # Tự động đóng nếu client không gửi dữ liệu sau 10 phút

    try:
        # ✅ Nhận dòng định danh duy nhất từ client: room_id|username
        room_data = conn.recv(1024).decode().strip()

        if '|' not in room_data:
            conn.send("Lỗi định dạng kết nối (cần room_id|username).".encode())
            conn.close()
            return

        # ✅ Tách room_id và username từ dòng nhận được
        room_id, username = room_data.split('|', 1)
            # ✅ Kiểm tra nếu username đã tồn tại trong cùng phòng
        if any(un == username and clients[c] == room_id for c, un in usernames.items()):
            conn.send("Tên người dùng đã được sử dụng trong phòng này. Vui lòng chọn tên khác.".encode())
            conn.close()
            return
        
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
                conn.send(msg + '\n'.encode())
            except:
                continue

        # ✅ Vòng lặp chính nhận tin nhắn từ client
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    print(f"[!] Client {username} mất kết nối.") #cần sửa nếu muốn mở rộng quản lý nhiều client (35 & 117)
                    break

                message = data.decode().strip() # Loại bỏ khoảng trắng đầu cuối
                display_time = datetime.now().strftime('%H:%M:%S')
                db_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # ✅ Kiểm tra nếu tin nhắn là lệnh thoát
                if message.strip() == "/quit":
                    break

                full_msg = f"{username}|{message}|{display_time}"
                print(f"[Room {room_id}] {full_msg}")

                
                # ✅ Lưu tin nhắn vào cơ sở dữ liệu
                save_message_to_db(room_id, username, message, db_timestamp)
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
        #print(f"[-] Ngắt kết nối từ {addr}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [-] {username} ({addr}) đã rời khỏi phòng.")


        room_id = clients.get(conn)
        username = usernames.get(conn, "???")

        if room_id:
            if conn in rooms.get(room_id, []):
                rooms[room_id].remove(conn)
                if not rooms[room_id]:  # Nếu phòng rỗng thì xóa phòng
                    del rooms[room_id]
            clients.pop(conn, None)
            usernames.pop(conn, None)

            # ✅ Gửi thông báo người dùng rời phòng
            leave_time = datetime.now().strftime('%H:%M:%S')
            leave_msg = f"system|{username} đã rời phòng|{leave_time}"
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

        # Lấy user_id từ username
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()

        # Lấy room_id từ room name (room_code)
        cursor.execute("SELECT id FROM rooms WHERE name = %s", (room_code,))
        room_result = cursor.fetchone()

        if user_result and room_result:
            user_id = user_result[0]
            room_id = room_result[0]

            # Thêm tin nhắn vào bảng messages
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