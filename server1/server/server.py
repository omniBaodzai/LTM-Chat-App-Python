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
        room_id = int(room_id.strip())
        

        # ✅ Kiểm tra trùng tên trong cùng phòng (trên RAM)
        if any(un == username and clients[c] == room_id for c, un in usernames.items()):
            conn.send("Tên người dùng đã được sử dụng trong phòng này. Vui lòng chọn tên khác.".encode())
            conn.close()
            return

        usernames[conn] = username
        clients[conn] = room_id

        
        # ✅ Thêm thành viên vào bảng room_members
        add_user_to_room_members(room_id, username)
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
                if message == "/leave":
                    try:
                        conn_check = get_db_connection()
                        cursor_check = conn_check.cursor()
                        cursor_check.execute("SELECT COUNT(*) FROM room_members WHERE room_id = %s", (room_id,))
                        member_count = cursor_check.fetchone()[0]

                        if member_count <= 1:
                            warning_obj = {
                                "sender": "system",
                                "content": (
                                    "⚠️ Bạn là người cuối cùng trong nhóm.\n"
                                    "Nếu bạn rời phòng, toàn bộ tin nhắn và phòng này sẽ bị xóa vĩnh viễn.\n"
                                    "Gõ `/confirm_leave` để xác nhận rời phòng.\n"
                                    "Gõ `/cancel` để hủy."
                                ),
                                "timestamp": display_time
                            }
                            conn.sendall((json.dumps(warning_obj) + '\n').encode())
                            continue
                        else:
                            success = remove_user_from_room(room_id, username)
                            if success:
                                leave_obj = {"sender": "system", "content": f"{username} đã rời nhóm.", "timestamp": display_time}
                                broadcast(json.dumps(leave_obj), room_id=room_id)
                                break
                            else:
                                error_obj = {"sender": "system", "content": "❌ Không thể rời nhóm. Vui lòng thử lại.", "timestamp": display_time}
                                conn.sendall(json.dumps(error_obj).encode())
                    except Exception as e:
                        print(f"[!] Lỗi khi xử lý /leave: {e}")
                    finally:
                        try:
                            cursor_check.close()
                            conn_check.close()
                        except:
                            pass
                    continue

                if message == "/confirm_leave":
                    success = remove_user_from_room(room_id, username)
                    if success:
                        leave_obj = {"sender": "system", "content": f"{username} đã rời nhóm (Xác nhận xóa nhóm nếu bạn là người cuối).", "timestamp": display_time}
                        broadcast(json.dumps(leave_obj), room_id=room_id)
                        break
                    else:
                        error_obj = {"sender": "system", "content": "❌ Không thể rời nhóm. Vui lòng thử lại.", "timestamp": display_time}
                        conn.sendall(json.dumps(error_obj).encode())
                    continue

                if message == "/cancel":
                    cancel_obj = {"sender": "system", "content": "✅ Bạn đã hủy lệnh rời phòng.", "timestamp": display_time}
                    conn.sendall((json.dumps(cancel_obj) + '\n').encode())  # <-- Đảm bảo có \n
                    continue

                #Kích thành viên
                if message.startswith("/kick "):
                    if not is_user_admin(room_id, username):
                        error_obj = {"sender": "system", "content": "❌ Bạn không có quyền kick người khác.", "timestamp": display_time}
                        conn.sendall((json.dumps(error_obj) + '\n').encode())
                        continue

                    parts = message.split(' ', 1)
                    if len(parts) != 2 or not parts[1].strip():
                        error_obj = {"sender": "system", "content": "⚠️ Cú pháp đúng: /kick <tên_người_dùng>", "timestamp": display_time}
                        conn.sendall((json.dumps(error_obj) + '\n').encode())
                        continue

                    target_username = parts[1].strip()
                    if target_username == username:
                        error_obj = {"sender": "system", "content": "❌ Không thể tự kick chính mình.", "timestamp": display_time}
                        conn.sendall((json.dumps(error_obj) + '\n').encode())
                        continue

                    # ➤ Tìm kết nối tương ứng với user bị kick
                    target_conn = None
                    for c, un in usernames.items():
                        if un == target_username and clients.get(c) == room_id:
                            target_conn = c
                            break

                    kicked = remove_user_from_room(room_id, target_username)
                    if kicked:
                        # Gửi tin báo cho toàn phòng
                        kick_msg = {"sender": "system", "content": f"⚠️ {target_username} đã bị {username} kick khỏi phòng.", "timestamp": display_time}
                        broadcast(json.dumps(kick_msg), room_id=room_id)

                        # Nếu tìm được kết nối socket -> đóng và xoá khỏi RAM
                        if target_conn:
                            try:
                                target_conn.sendall((json.dumps({
                                        "sender": "system",
                                        "content": "🚫 Bạn đã bị kick khỏi phòng.",
                                        "timestamp": display_time
                                    }) + '\n').encode())

                                target_conn.close()
                            except:
                                pass
                            clients.pop(target_conn, None)
                            usernames.pop(target_conn, None)
                            if target_conn in rooms.get(room_id, []):
                                rooms[room_id].remove(target_conn)
                    else:
                        error_msg = {"sender": "system", "content": f"❌ Không thể kick {target_username}.", "timestamp": display_time}
                        conn.sendall((json.dumps(error_msg) + '\n').encode())
                    continue


                
                # Gán admin
                if message.startswith("/transfer_admin"):
                    parts = message.split(' ', 1)
                    if len(parts) != 2 or not parts[1].strip():
                        error_obj = {"sender": "system", "content": "⚠️ Cú pháp đúng: /transfer_admin <tên_người_dùng_mới>", "timestamp": display_time}
                        conn.sendall((json.dumps(error_obj) + '\n').encode())
                        continue

                    if not is_user_admin(room_id, username):
                        error_obj = {"sender": "system", "content": "❌ Bạn không phải là admin.", "timestamp": display_time}
                        conn.sendall((json.dumps(error_obj) + '\n').encode())
                        continue

                    new_admin = parts[1].strip()
                    try:
                        conn_db = get_db_connection()
                        cursor = conn_db.cursor()
                        # Đặt tất cả về is_admin = False
                        cursor.execute("""
                            UPDATE room_members SET is_admin = FALSE
                            WHERE room_id = %s
                        """, (room_id,))
                        # Gán admin cho người mới
                        cursor.execute("""
                            UPDATE room_members
                            SET is_admin = TRUE
                            WHERE room_id = %s AND user_id = (SELECT id FROM users WHERE username = %s)
                        """, (room_id, new_admin))
                        conn_db.commit()
                        info_msg = {"sender": "system", "content": f"🔄 {username} đã chuyển quyền admin cho {new_admin}.", "timestamp": display_time}
                        broadcast(json.dumps(info_msg), room_id=room_id)
                    except Exception as e:
                        print(f"[!] Lỗi khi chuyển quyền admin: {e}")
                    finally:
                        try:
                            cursor.close()
                            conn_db.close()
                        except:
                            pass
                    continue

                # Trực tiếp xóa phòng chat dù vẫn còn thành viên
                if message == "/delete_room":
                    if not is_user_admin(room_id, username):
                        error_obj = {"sender": "system", "content": "❌ Bạn không có quyền xoá phòng.", "timestamp": display_time}
                        conn.sendall((json.dumps(error_obj) + '\n').encode())
                        continue

                    try:
                        conn_db = get_db_connection()
                        cursor = conn_db.cursor()
                        cursor.execute("DELETE FROM messages WHERE room_id = %s", (room_id,))
                        cursor.execute("DELETE FROM room_members WHERE room_id = %s", (room_id,))
                        cursor.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
                        conn_db.commit()
                        info_msg = {"sender": "system", "content": f"💣 {username} đã xoá phòng.", "timestamp": display_time}
                        broadcast(json.dumps(info_msg), room_id=room_id)
                        break  # Rời khỏi vòng lặp
                    except Exception as e:
                        print(f"[!] Lỗi khi xoá phòng: {e}")
                    finally:
                        try:
                            cursor.close()
                            conn_db.close()
                        except:
                            pass
                    continue






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
        # ➤ Thoát tạm (do Ctrl+C, tắt app, v.v.)
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

def add_user_to_room_members(room_code, username, is_admin=False):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Lấy user_id từ username
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()

        # Lấy room_id từ room_code
        cursor.execute("SELECT id FROM rooms WHERE name = %s", (room_code,))
        room_result = cursor.fetchone()

        if user_result and room_result:
            user_id = user_result[0]
            room_id = room_result[0]

            # Thêm nếu chưa tồn tại
            cursor.execute("""
                INSERT IGNORE INTO room_members (room_id, user_id, is_admin)
                VALUES (%s, %s, %s)
            """, (room_id, user_id, is_admin))
            conn.commit()
        else:
            print(f"[DB WARNING] Không thể thêm {username} vào room_members (chưa có user hoặc phòng).")

    except Exception as e:
        print(f"[DB ERROR] Lỗi thêm thành viên vào room_members: {e}")
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def remove_user_from_room(room_id, username):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Lấy user_id từ username
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_row = cursor.fetchone()
        if not user_row:
            print(f"[WARN] ➤ Không tìm thấy user {username}")
            return False
        user_id = user_row[0]

        # Kiểm tra xem người dùng có trong phòng không
        cursor.execute("""
            SELECT is_admin FROM room_members
            WHERE room_id = %s AND user_id = %s
        """, (room_id, user_id))
        result = cursor.fetchone()
        if not result:
            print(f"[WARN] ➤ {username} không phải thành viên phòng ID {room_id}")
            return False
        is_admin = result[0]

        # Nếu là admin, tìm người khác làm admin
        if is_admin:
            cursor.execute("""
                SELECT user_id FROM room_members
                WHERE room_id = %s AND user_id != %s
                ORDER BY user_id ASC LIMIT 1
            """, (room_id, user_id))
            next_admin = cursor.fetchone()
            if next_admin:
                next_admin_id = next_admin[0]
                cursor.execute("""
                    UPDATE room_members
                    SET is_admin = TRUE
                    WHERE room_id = %s AND user_id = %s
                """, (room_id, next_admin_id))
                print(f"[INFO] ➤ Chuyển quyền admin cho user_id {next_admin_id} trong phòng ID {room_id}")
            else:
                print(f"[INFO] ➤ Không còn ai khác trong phòng ID {room_id} để làm admin")

        # Xoá user khỏi room_members
        cursor.execute("""
            DELETE FROM room_members
            WHERE room_id = %s AND user_id = %s
        """, (room_id, user_id))
        conn.commit()

        print(f"[DB] ➤ {username} đã rời phòng ID {room_id}")
        # ✅ Kiểm tra nếu không còn ai trong phòng thì xoá luôn phòng
        cursor.execute("""
            SELECT COUNT(*) FROM room_members WHERE room_id = %s
        """, (room_id,))
        member_count = cursor.fetchone()[0]
        if member_count == 0:
            cursor.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
            conn.commit()
            print(f"[DB] ➤ Đã xoá phòng ID {room_id} vì không còn thành viên.")

        return True

    except Exception as e:
        print(f"[DB ERROR] Lỗi khi {username} rời phòng ID {room_id}: {e}")
        return False
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

def is_user_admin(room_id, username):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rm.is_admin
            FROM room_members rm
            JOIN users u ON rm.user_id = u.id
            WHERE rm.room_id = %s AND u.username = %s
        """, (room_id, username))
        result = cursor.fetchone()
        return result and result[0] == 1
    except:
        return False
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# server.py không nên tự chạy, chỉ cung cấp hàm start_server
