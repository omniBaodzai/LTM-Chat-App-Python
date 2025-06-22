import socket
import threading
from datetime import datetime
from client.config import get_db_connection
import mysql.connector
import sys

HOST = '0.0.0.0'  # IP LAN
PORT = 12345

clients = {}        # conn -> (username, room_id or None for private)
usernames_to_conns = {} # username -> conn (for direct private messaging)
room_messages = {}  # room_id -> list of messages (only for public rooms)
rooms = {}          # room_id -> list of conn (only for public rooms)
private_messages = {} # (user1, user2) -> list of messages

last_known_rooms = set()
last_known_users = set()

def broadcast(message_data, room_id=None, recipient_conn=None):
    protocol, sender, content, timestamp, original_msg_for_display = message_data
    full_msg = f"{protocol}|{sender}|{content}|{timestamp}|{original_msg_for_display}"
    
    disconnected_clients = []

    if room_id:
        for client_conn in list(rooms.get(room_id, [])):
            try:
                client_conn.send((full_msg + '\n').encode())
            except Exception as e:
                print(f"[!] Error sending to client in room {room_id}: {e}")
                disconnected_clients.append(client_conn)
    elif recipient_conn:
        try:
            recipient_conn.send((full_msg + '\n').encode())
        except Exception as e:
            print(f"[!] Error sending private message to client: {e}")
            disconnected_clients.append(recipient_conn)
    
    for client in disconnected_clients:
        if client in clients:
            remove_client(client)

def broadcast_online_users(requester_conn=None):
    online_users_list = [info[0] for info in clients.values()]
    users_string = ",".join(online_users_list)
    message = f"ONLINE_USERS|{users_string}\n".encode()

    if requester_conn:
        try:
            requester_conn.send(message)
        except Exception as e:
            print(f"Error sending online users to requester: {e}")
            remove_client(requester_conn)
    else:
        disconnected_clients = []
        for client_conn in list(clients.keys()):
            try:
                client_conn.send(message)
            except Exception as e:
                print(f"Error sending online users to all clients: {e}")
                disconnected_clients.append(client_conn)
        for client in disconnected_clients:
            remove_client(client)

def broadcast_online_users_in_room(room_id):
    if room_id not in rooms:
        return
    
    online_users_in_room = []
    for client_conn in rooms[room_id]:
        if client_conn in clients:
            username, _ = clients[client_conn]
            online_users_in_room.append(username)
            
    users_string = ",".join(online_users_in_room)
    message = f"ONLINE_USERS|{users_string}\n".encode()

    disconnected_clients = []
    for client_conn in list(rooms[room_id]):
        try:
            client_conn.send(message)
        except Exception as e:
            print(f"Error sending room online users to client {client_conn}: {e}")
            disconnected_clients.append(client_conn)
    
    for client in disconnected_clients:
        remove_client(client)

def broadcast_public_rooms():
    rooms_list = get_public_rooms_from_db()
    rooms_string = ",".join(rooms_list)
    message = f"PUBLIC_ROOMS|{rooms_string}\n".encode()
    print(f"[BROADCAST] Sending PUBLIC_ROOMS: {rooms_string}")

    if not clients:
        print("[BROADCAST] No active clients to send PUBLIC_ROOMS")
        return

    disconnected_clients = []
    for client_conn in list(clients.keys()):
        try:
            if client_conn.fileno() != -1:
                client_conn.send(message)
                print(f"[BROADCAST] Sent PUBLIC_ROOMS to client {clients.get(client_conn, ('Unknown',))[0]}")
            else:
                print(f"[BROADCAST] Skipping invalid socket for client {clients.get(client_conn, ('Unknown',))[0]}")
                disconnected_clients.append(client_conn)
        except Exception as e:
            print(f"[BROADCAST] Error sending public rooms to client {clients.get(client_conn, ('Unknown',))[0]}: {e}")
            disconnected_clients.append(client_conn)
    
    for client in disconnected_clients:
        remove_client(client)

def broadcast_all_users():
    users_list = get_all_users_from_db()
    users_string = ",".join(users_list)
    message = f"ALL_USERS|{users_string}\n".encode()
    print(f"[BROADCAST] Sending ALL_USERS: {users_string}")

    if not clients:
        print("[BROADCAST] No active clients to send ALL_USERS")
        return

    disconnected_clients = []
    for client_conn in list(clients.keys()):
        try:
            if client_conn.fileno() != -1:
                client_conn.send(message)
                print(f"[BROADCAST] Sent ALL_USERS to client {clients.get(client_conn, ('Unknown',))[0]}")
            else:
                print(f"[BROADCAST] Skipping invalid socket for client {clients.get(client_conn, ('Unknown',))[0]}")
                disconnected_clients.append(client_conn)
        except Exception as e:
            print(f"[BROADCAST] Error sending all users to client {clients.get(client_conn, ('Unknown',))[0]}: {e}")
            disconnected_clients.append(client_conn)
    
    for client in disconnected_clients:
        remove_client(client)

def monitor_database_changes():
    global last_known_rooms, last_known_users
    while True:
        try:
            current_rooms = set(get_public_rooms_from_db())
            if current_rooms != last_known_rooms:
                print(f"[DB MONITOR] Detected room changes: {current_rooms - last_known_rooms} added, {last_known_rooms - current_rooms} removed")
                last_known_rooms = current_rooms
                broadcast_public_rooms()

            current_users = set(get_all_users_from_db())
            if current_users != last_known_users:
                print(f"[DB MONITOR] Detected user changes: {current_users - last_known_users} added, {last_known_users - current_users} removed")
                last_known_users = current_users
                broadcast_all_users()

        except Exception as e:
            print(f"[DB MONITOR ERROR] Error checking database changes: {e}")
        
        threading.Event().wait(5)

def get_room_details_from_db(room_name):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("[DB ERROR] Cannot connect to database.")
            return None, None, None, []

        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT r.name AS room_name, r.created_at AS room_creation_date, u.username AS creator_username
        FROM rooms r
        JOIN users u ON r.created_by = u.id
        WHERE r.name = %s;
        """
        cursor.execute(query, (room_name,))
        room_info = cursor.fetchone()

        online_users_in_room = []
        if room_name in rooms:
            for client_conn in rooms[room_name]:
                if client_conn in clients:
                    username_in_room, _ = clients[client_conn]
                    online_users_in_room.append(username_in_room)
        
        if room_info:
            creation_date_str = room_info['room_creation_date'].strftime("%Y-%m-%d %H:%M:%S")
            return room_info['room_name'], room_info['creator_username'], creation_date_str, online_users_in_room
        else:
            return None, None, None, []
    except mysql.connector.Error as err:
        print(f"[DB ERROR] Error querying room info: {err}")
        return None, None, None, []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def delete_room_from_db(room_name, deleter_username):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("[DB ERROR] Cannot connect to database.")
            return False, "Database connection error."

        cursor = conn.cursor()
        cursor.execute("SELECT r.id, r.created_by FROM rooms r JOIN users u ON r.created_by = u.id WHERE r.name = %s", (room_name,))
        room_info = cursor.fetchone()

        if not room_info:
            return False, "Room does not exist."
        
        room_id_db = room_info[0]
        room_creator_id = room_info[1]

        cursor.execute("SELECT id FROM users WHERE username = %s", (deleter_username,))
        deleter_user_id = cursor.fetchone()
        if not deleter_user_id:
            return False, "User does not exist."
        deleter_user_id = deleter_user_id[0]

        if room_creator_id != deleter_user_id:
            return False, "You are not the creator of this room. You cannot delete it."

        cursor.execute("DELETE FROM messages WHERE room_id = %s", (room_id_db,))
        conn.commit()
        print(f"[DB] Deleted messages for room '{room_name}'")
        cursor.execute("DELETE FROM rooms WHERE id = %s", (room_id_db,))
        conn.commit()
        print(f"[DB] Deleted room '{room_name}' by '{deleter_username}'")
        
        broadcast_public_rooms()
        return True, "Room deleted successfully."
    except mysql.connector.Error as err:
        print(f"[DB ERROR] Error deleting room '{room_name}': {err}")
        return False, f"Database error: {err}"
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def authenticate_user(username, hashed_password):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("[DB ERROR] Cannot connect to database.")
            return None, None
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE username = %s AND password = %s", (username, hashed_password))
        user = cursor.fetchone()
        if user:
            return user[0], user[1]
        return None, None
    except Exception as e:
        print(f"[DB ERROR] Error authenticating user: {e}")
        return None, None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def register_user(username, hashed_password, email):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("[DB ERROR] Cannot connect to database.")
            return False, "Database connection error."
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, hashed_password, email))
        conn.commit()
        print(f"[DB] Registered new user '{username}'")
        broadcast_all_users()
        return True, "Success"
    except mysql.connector.IntegrityError as err:
        if "username" in str(err).lower():
            return False, "Username already exists."
        elif "email" in str(err).lower():
            return False, "Email already in use."
        else:
            return False, str(err)
    except Exception as e:
        print(f"[DB ERROR] Error registering user: {e}")
        return False, str(e)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def create_room_in_db(room_name, user_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("[DB ERROR] Cannot connect to database.")
            return False, "Database connection error."
        cursor = conn.cursor()
        cursor.execute("INSERT INTO rooms (name, created_by) VALUES (%s, %s)", (room_name, user_id))
        conn.commit()
        print(f"[DB] Created room '{room_name}' by user ID {user_id}")
        broadcast_public_rooms()
        return True, "Success"
    except mysql.connector.IntegrityError as err:
        return False, "Room name already exists."
    except Exception as e:
        print(f"[DB ERROR] Error creating room: {e}")
        return False, str(e)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def get_public_rooms_from_db():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("[DB ERROR] Cannot connect to database.")
            return []
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM rooms ORDER BY name ASC")
        rooms = [row[0] for row in cursor.fetchall()]
        return rooms
    except Exception as e:
        print(f"[DB ERROR] Error fetching rooms: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def get_all_users_from_db():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("[DB ERROR] Cannot connect to database.")
            return []
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users ORDER BY username ASC")
        users = [row[0] for row in cursor.fetchall()]
        return users
    except Exception as e:
        print(f"[DB ERROR] Error fetching users: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    username = None
    chat_mode = None
    room_id = None

    try:
        initial_data = conn.recv(1024).decode()
        if not initial_data:
            raise Exception("No initial data received.")

        parts = initial_data.split('|')
        protocol = parts[0]

        if protocol == "PUBLIC_CONNECT":
            if len(parts) == 3:
                room_id = parts[1]
                username = parts[2]
                chat_mode = "public"
            else:
                raise Exception("Invalid PUBLIC_CONNECT format.")
        elif protocol == "PRIVATE_CONNECT":
            if len(parts) == 2:
                username = parts[1]
                chat_mode = "private"
            else:
                raise Exception("Invalid PRIVATE_CONNECT format.")
        elif protocol == "LOGIN":
            if len(parts) == 3:
                username, hashed_password = parts[1], parts[2]
                user_id, username_from_db = authenticate_user(username, hashed_password)
                if user_id:
                    conn.send(f"LOGIN_SUCCESS|{user_id}|{username_from_db}".encode())
                else:
                    conn.send("LOGIN_FAILED|Invalid credentials".encode())
                conn.close()
                return
        elif protocol == "REGISTER":
            if len(parts) == 4:
                username, hashed_password, email = parts[1], parts[2], parts[3]
                success, message = register_user(username, hashed_password, email)
                if success:
                    conn.send("REGISTER_SUCCESS".encode())
                else:
                    conn.send(f"REGISTER_FAILED|{message}".encode())
                conn.close()
                return
        elif protocol == "CREATE_ROOM":
            if len(parts) == 3:
                room_name, user_id = parts[1], int(parts[2])
                success, message = create_room_in_db(room_name, user_id)
                if success:
                    conn.send("CREATE_ROOM_SUCCESS".encode())
                else:
                    conn.send(f"CREATE_ROOM_FAILED|{message}".encode())
                conn.close()
                return
        elif protocol == "GET_PUBLIC_ROOMS":
            rooms_list = get_public_rooms_from_db()
            conn.send(f"PUBLIC_ROOMS|{','.join(rooms_list)}".encode())
            conn.close()
            return
        elif protocol == "GET_ALL_USERS":
            users_list = get_all_users_from_db()
            conn.send(f"ALL_USERS|{','.join(users_list)}".encode())
            conn.close()
            return
        else:
            raise Exception(f"Unknown initial protocol: {protocol}")

        if not username:
            conn.send("system|Invalid username.\n".encode())
            conn.close()
            return

        with threading.Lock():
            if username in usernames_to_conns:
                conn.send("system|Username already exists or is online. Please choose another.\n".encode())
                conn.close()
                return
            
            clients[conn] = (username, room_id)
            usernames_to_conns[username] = conn
            print(f"[CLIENT ADDED] Added {username} to clients list")
            
            if chat_mode == "public":
                if room_id not in rooms:
                    rooms[room_id] = []
                rooms[room_id].append(conn)
                print(f"[ACTIVE] {username} (Public - Room: {room_id}) connected from {addr}")
                send_message_history(conn, room_id)
                system_msg = f"{username} has joined the chat room."
                broadcast(("SYSTEM_MSG_RECV", "system", system_msg, datetime.now().strftime("%H:%M:%S"), system_msg), room_id=room_id)
                broadcast_online_users_in_room(room_id)
            elif chat_mode == "private":
                print(f"[ACTIVE] {username} (Private) connected from {addr}")
                broadcast_online_users()

        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                msg = data.decode(errors='ignore')
            except Exception as e:
                print(f"[RECV ERROR] {addr} - {e}")
                break

            if not msg:
                break

            with threading.Lock():
                if msg == "/quit":
                    break
                elif msg == "/get_online_users" and chat_mode == "private":
                    broadcast_online_users(conn)
                    continue
                elif msg.startswith("GET_ROOM_ONLINE_USERS|") and chat_mode == "public":
                    requested_room_id = msg.split('|')[1]
                    if requested_room_id == room_id:
                        broadcast_online_users_in_room(room_id)
                    continue
                elif msg.startswith("GET_ROOM_INFO_AND_USERS|") and chat_mode == "public":
                    parts = msg.split('|', 1)
                    if len(parts) == 2:
                        requested_room_name = parts[1]
                        room_name, creator_username, creation_date_str, online_users_list = get_room_details_from_db(requested_room_name)
                        if room_name and creator_username and creation_date_str:
                            users_string = ",".join(online_users_list)
                            response = f"ROOM_INFO_AND_USERS|{room_name}|{creator_username}|{creation_date_str}|{users_string}\n"
                            try:
                                conn.send(response.encode())
                            except Exception as e:
                                print(f"Error sending room info to client {username}: {e}")
                                remove_client(conn)
                        else:
                            print(f"[SERVER] No info found for room '{requested_room_name}'")
                    continue
                elif msg.startswith("DELETE_ROOM|") and chat_mode == "public":
                    parts = msg.split('|', 1)
                    if len(parts) == 2:
                        room_to_delete = parts[1]
                        current_username, _ = clients.get(conn, (None, None))
                        room_name_db, creator_username_db, _, _ = get_room_details_from_db(room_to_delete)
                        if room_name_db and creator_username_db == current_username:
                            success, message = delete_room_from_db(room_to_delete, current_username)
                            if success:
                                system_msg_to_room = f"Phòng chat '{room_to_delete}' đã bị người tạo xóa."
                                clients_in_deleted_room = list(rooms.get(room_to_delete, []))
                                for client_in_room_conn in clients_in_deleted_room:
                                    broadcast(("SYSTEM_MSG_RECV", "system", system_msg_to_room, datetime.now().strftime("%H:%M:%S"), system_msg_to_room), recipient_conn=client_in_room_conn)
                                    try:
                                        client_in_room_conn.send("/quit\n".encode())
                                        client_in_room_conn.shutdown(socket.SHUT_RDWR)
                                        client_in_room_conn.close()
                                    except Exception as e:
                                        print(f"Error disconnecting client {clients.get(client_in_room_conn, ('Unknown',))[0]} from deleted room: {e}")
                                    remove_client(client_in_room_conn)
                                if room_to_delete in rooms:
                                    del rooms[room_to_delete]
                                if room_to_delete in room_messages:
                                    del room_messages[room_to_delete]
                                success_msg_to_deleter = f"Phòng chat '{room_to_delete}' của bạn đã được xóa thành công."
                                broadcast(("SYSTEM_MSG_RECV", "system", success_msg_to_deleter, datetime.now().strftime("%H:%M:%S"), success_msg_to_deleter), recipient_conn=conn)
                            else:
                                error_msg = f"Không thể xóa phòng '{room_to_delete}': {message}"
                                broadcast(("SYSTEM_MSG_RECV", "system", error_msg, datetime.now().strftime("%H:%M:%S"), error_msg), recipient_conn=conn)
                        else:
                            error_msg = f"Bạn không có quyền xóa phòng '{room_to_delete}' hoặc phòng không tồn tại."
                            broadcast(("SYSTEM_MSG_RECV", "system", error_msg, datetime.now().strftime("%H:%M:%S"), error_msg), recipient_conn=conn)
                    else:
                        print(f"[{current_username}] Invalid DELETE_ROOM format: {msg}")
                    continue
                current_username, current_room_id = clients.get(conn, (None, None))
                if current_username is None:
                    break
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if msg.startswith("PUBLIC_MSG|"):
                    parts = msg.split('|', 2)
                    if len(parts) == 3:
                        room_id_from_msg = parts[1]
                        content = parts[2]
                        if room_id_from_msg == current_room_id:
                            message_data = ("PUBLIC_MSG_RECV", current_username, content, timestamp, f"{current_username}: {content}")
                            broadcast(message_data, room_id=current_room_id)
                            save_message_to_db(current_room_id, current_username, content, timestamp)
                        else:
                            print(f"[{current_username}] Tried to send public msg to wrong room: {room_id_from_msg}")
                    else:
                        print(f"[{current_username}] Invalid PUBLIC_MSG format: {msg}")
                elif msg.startswith("PRIVATE_MSG|"):
                    parts = msg.split('|', 2)
                    if len(parts) == 3:
                        target_username = parts[1]
                        content = parts[2]
                        target_conn = usernames_to_conns.get(target_username)
                        if target_conn:
                            sender_msg_data = ("PRIVATE_MSG_RECV", current_username, content, timestamp, f"You (to {target_username}): {content}")
                            broadcast(sender_msg_data, recipient_conn=conn)
                            receiver_msg_data = ("PRIVATE_MSG_RECV", current_username, content, timestamp, f"Private from {current_username}: {content}")
                            broadcast(receiver_msg_data, recipient_conn=target_conn)
                            save_private_message_to_db(current_username, target_username, content, timestamp)
                        else:
                            system_msg = f"Người dùng '{target_username}' hiện đang offline."
                            broadcast(("SYSTEM_MSG_RECV", "system", system_msg, timestamp, system_msg), recipient_conn=conn)
                    else:
                        print(f"[{current_username}] Invalid PRIVATE_MSG format: {msg}")
                elif msg.startswith("REQUEST_PRIVATE_HISTORY|"):
                    parts = msg.split('|', 1)
                    if len(parts) == 2:
                        target_username = parts[1]
                        send_private_message_history(conn, current_username, target_username)
                    else:
                        print(f"[{current_username}] Invalid REQUEST_PRIVATE_HISTORY format: {msg}")

    except Exception as e:
        print(f"[ERROR] {addr} - {e}")
    finally:
        remove_client(conn)
        print(f"[DISCONNECTED] {username if username else addr} disconnected.")
        if chat_mode == "public" and room_id:
            if room_id in rooms:
                system_msg = f"{username} đã rời phòng chat."
                broadcast(("SYSTEM_MSG_RECV", "system", system_msg, datetime.now().strftime("%H:%M:%S"), system_msg), room_id=room_id)
                broadcast_online_users_in_room(room_id)
        elif chat_mode == "private":
            broadcast_online_users()

def remove_client(conn):
    with threading.Lock():
        if conn in clients:
            username, room_id = clients[conn]
            if room_id and room_id in rooms:
                if conn in rooms[room_id]:
                    rooms[room_id].remove(conn)
            clients.pop(conn, None)
            if username in usernames_to_conns and usernames_to_conns[username] == conn:
                usernames_to_conns.pop(username, None)
                print(f"[CLIENT REMOVED] Removed {username} from online users.")

def send_message_history(conn, room_code):
    conn_db = None
    cursor = None
    try:
        conn_db = get_db_connection()
        if conn_db is None:
            print("[DB ERROR] Cannot connect to database.")
            return
        cursor = conn_db.cursor(buffered=True)
        cursor.execute("SELECT id FROM rooms WHERE name = %s", (room_code,))
        room_result = cursor.fetchone()
        if room_result:
            room_id_db = room_result[0]
            cursor.execute("""
                SELECT u.username, m.content, m.timestamp 
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.room_id = %s
                ORDER BY m.timestamp ASC
            """, (room_id_db,))
            history = cursor.fetchall()
            for username, content, timestamp in history:
                time_str = timestamp.strftime("%H:%M:%S")
                message_data = ("PUBLIC_MSG_RECV", username, content, time_str, f"[{time_str}] {username}: {content}")
                full_msg = f"{message_data[0]}|{message_data[1]}|{message_data[2]}|{message_data[3]}|{message_data[4]}"
                conn.send((full_msg + '\n').encode())
    except Exception as e:
        print(f"[DB ERROR] Error sending message history for room {room_code}: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn_db and conn_db.is_connected():
            conn_db.close()

def save_message_to_db(room_code, username, content, timestamp):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("[DB ERROR] Cannot connect to database.")
            return
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
            print(f"[DB] Saved message to room '{room_code}' by '{username}'")
        else:
            if not user_result:
                print(f"[DB WARNING] Username '{username}' does not exist.")
            if not room_result:
                print(f"[DB WARNING] Room '{room_code}' does not exist.")
    except Exception as e:
        print(f"[DB ERROR] Error saving message: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def save_private_message_to_db(sender_username, receiver_username, content, timestamp):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("[DB ERROR] Cannot connect to database.")
            return
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (sender_username,))
        sender_id = cursor.fetchone()
        if not sender_id:
            print(f"[DB WARNING] Sender '{sender_username}' does not exist.")
            return
        sender_id = sender_id[0]
        cursor.execute("SELECT id FROM users WHERE username = %s", (receiver_username,))
        receiver_id = cursor.fetchone()
        if not receiver_id:
            print(f"[DB WARNING] Receiver '{receiver_username}' does not exist.")
            return
        receiver_id = receiver_id[0]
        cursor.execute("""
            INSERT INTO private_messages (sender_id, receiver_id, content, timestamp)
            VALUES (%s, %s, %s, %s)
        """, (sender_id, receiver_id, content, timestamp))
        conn.commit()
        print(f"[DB] Saved private message from '{sender_username}' to '{receiver_username}'")
    except Exception as e:
        print(f"[DB ERROR] Error saving private message: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def send_private_message_history(conn, user1_username, user2_username):
    conn_db = None
    cursor = None
    try:
        conn_db = get_db_connection()
        if conn_db is None:
            print("[DB ERROR] Cannot connect to database.")
            return
        cursor = conn_db.cursor(buffered=True)
        cursor.execute("SELECT id FROM users WHERE username = %s", (user1_username,))
        user1_id = cursor.fetchone()
        if not user1_id:
            print(f"[DB WARNING] User '{user1_username}' does not exist.")
            return
        user1_id = user1_id[0]
        cursor.execute("SELECT id FROM users WHERE username = %s", (user2_username,))
        user2_id = cursor.fetchone()
        if not user2_id:
            print(f"[DB WARNING] User '{user2_username}' does not exist.")
            return
        user2_id = user2_id[0]
        cursor.execute("""
            SELECT u_sender.username, u_receiver.username, pm.content, pm.timestamp
            FROM private_messages pm
            JOIN users u_sender ON pm.sender_id = u_sender.id
            JOIN users u_receiver ON pm.receiver_id = u_receiver.id
            WHERE (pm.sender_id = %s AND pm.receiver_id = %s)
                OR (pm.sender_id = %s AND pm.receiver_id = %s)
            ORDER BY pm.timestamp ASC
        """, (user1_id, user2_id, user2_id, user1_id))
        history = cursor.fetchall()
        for sender_u, receiver_u, content, timestamp in history:
            time_str = timestamp.strftime("%H:%M:%S")
            message_data = ("PRIVATE_MSG_RECV", sender_u, content, time_str, f"[{time_str}] {sender_u}: {content}")
            full_msg = f"{message_data[0]}|{message_data[1]}|{message_data[2]}|{message_data[3]}|{message_data[4]}"
            conn.send((full_msg + '\n').encode())
    except Exception as e:
        print(f"[DB ERROR] Error sending private message history between {user1_username} and {user2_username}: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn_db and conn_db.is_connected():
            conn_db.close()

def start_server():
    global last_known_rooms, last_known_users

    # 1. Load dữ liệu ban đầu
    last_known_rooms = set(get_public_rooms_from_db())
    last_known_users = set(get_all_users_from_db())
    print(f"[STARTUP] Initial rooms: {last_known_rooms}")
    print(f"[STARTUP] Initial users: {last_known_users}")

    # 2. Bắt đầu theo dõi thay đổi DB
    threading.Thread(target=monitor_database_changes, daemon=True).start()

    # 3. Thiết lập socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    server.settimeout(1.0)  # timeout mỗi 1s cho accept()

    print(f"[✅ Server] Đang lắng nghe trên {HOST}:{PORT}")
    print("Ấn Ctrl + C để thoát an toàn...")

    try:
        while True:
            try:
                conn, addr = server.accept()
                print(f"[KẾT NỐI] Client mới từ {addr}")
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("\n[💤 Server] Đang tắt an toàn do Ctrl + C...")
    finally:
        try:
            server.close()
            print("[✅] Socket đã được đóng.")
        except Exception as e:
            print(f"[⚠️] Lỗi khi đóng socket: {e}")
        sys.exit(0)

if __name__ == "__main__":
    start_server()