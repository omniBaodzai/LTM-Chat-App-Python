import socket
import threading
from datetime import datetime
from client.config import get_db_connection
import mysql.connector

HOST = '192.168.1.16'  # IP LAN của bạn
PORT = 12345

clients = {}       # conn -> (username, room_id or None for private)
usernames_to_conns = {} # username -> conn (for direct private messaging)
room_messages = {} # room_id -> list of messages (only for public rooms)
rooms = {}         # room_id -> list of conn (only for public rooms)
private_messages = {} # (user1, user2) -> list of messages

def broadcast(message_data, room_id=None, recipient_conn=None):
    """
    Sends a message to clients.
    message_data: tuple (protocol, sender, content, timestamp, original_msg_for_display)
    room_id: If specified, broadcast to all clients in that room.
    recipient_conn: If specified, send only to this connection (for private messages).
    """
    protocol, sender, content, timestamp, original_msg_for_display = message_data
    full_msg = f"{protocol}|{sender}|{content}|{timestamp}|{original_msg_for_display}"
    
    disconnected_clients = []

    if room_id: # Public broadcast to a room
        for client_conn in list(rooms.get(room_id, [])):
            try:
                client_conn.send((full_msg + '\n').encode())
            except Exception as e:
                print(f"[!] Lỗi gửi tới client trong phòng {room_id}: {e}")
                disconnected_clients.append(client_conn)
    elif recipient_conn: # Private message to a specific connection
        try:
            recipient_conn.send((full_msg + '\n').encode())
        except Exception as e:
            print(f"[!] Lỗi gửi tin riêng tới client: {e}")
            disconnected_clients.append(recipient_conn)
    
    # Handle disconnected clients
    for client in disconnected_clients:
        if client in clients:
            remove_client(client)

def broadcast_online_users(requester_conn=None):
    """
    Sends the current list of ALL online users to a specific requester, or all clients.
    """
    online_users_list = [info[0] for info in clients.values()] # Get all usernames
    users_string = ",".join(online_users_list)
    message = f"ONLINE_USERS|{users_string}\n".encode()

    if requester_conn:
        try:
            requester_conn.send(message)
        except Exception as e:
            print(f"Error sending online users to requester: {e}")
            remove_client(requester_conn)
    else: # Broadcast to all
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
    """
    Sends the current list of online users in a specific public room to clients in that room.
    """
    if room_id not in rooms:
        return
    
    # Get usernames of clients in this specific room
    online_users_in_room = []
    for client_conn in rooms[room_id]:
        if client_conn in clients: # Ensure the client is still generally connected
            username, _ = clients[client_conn]
            online_users_in_room.append(username)
            
    users_string = ",".join(online_users_in_room)
    message = f"ONLINE_USERS|{users_string}\n".encode() # Use the same protocol for simplicity

    disconnected_clients = []
    for client_conn in list(rooms[room_id]):
        try:
            client_conn.send(message)
        except Exception as e:
            print(f"Error sending room online users to client {client_conn}: {e}")
            disconnected_clients.append(client_conn)
    
    for client in disconnected_clients:
        remove_client(client) # Remove if disconnected during broadcast


def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    username = None
    chat_mode = None
    room_id = None

    try:
        # First message determines chat mode
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
        else:
            raise Exception(f"Unknown initial protocol: {protocol}")

        if not username:
            conn.send("system|Tên đăng nhập không hợp lệ.\n".encode())
            conn.close()
            return

        with threading.Lock(): # Protect shared data
            if username in usernames_to_conns:
                conn.send("system|Tên đăng nhập đã tồn tại hoặc đang online. Vui lòng chọn tên khác.\n".encode())
                conn.close()
                return
            
            clients[conn] = (username, room_id)
            usernames_to_conns[username] = conn
            
            if chat_mode == "public":
                if room_id not in rooms:
                    rooms[room_id] = []
                    room_messages[room_id] = [] # Initialize message history for new room
                    # Create room in DB if it doesn't exist
                    try:
                        db_conn = get_db_connection()
                        cursor = db_conn.cursor()
                        cursor.execute("INSERT IGNORE INTO rooms (name) VALUES (%s)", (room_id,))
                        db_conn.commit()
                        cursor.close()
                        db_conn.close()
                    except mysql.connector.Error as err:
                        print(f"[DB ERROR] Lỗi khi tạo phòng chat: {err}")
                
                rooms[room_id].append(conn)
                print(f"[ACTIVE] {username} (Public - Room: {room_id}) connected from {addr}")
                
                # Load and send message history for public room
                send_message_history(conn, room_id)
                
                # Notify others in the room and update their online list
                system_msg = f"{username} đã tham gia phòng chat."
                broadcast(("SYSTEM_MSG_RECV", "system", system_msg, datetime.now().strftime("%H:%M"), system_msg), room_id=room_id)
                broadcast_online_users_in_room(room_id) # Update online users in THIS room
            
            elif chat_mode == "private":
                print(f"[ACTIVE] {username} (Private) connected from {addr}")
                # For private chat, notify all other clients that this user is online
                # and also send the full list of online users to the newly connected private client.
                system_msg = f"Người dùng {username} đã online."
                # We need to send this system message to all other *private* chat clients
                # Or simply rely on the periodic online user list update.
                # For now, let's just broadcast the updated online list to ALL private clients.
                broadcast_online_users() # Update all private clients

        while True:
            msg = conn.recv(1024).decode()
            if not msg:
                break

            with threading.Lock(): # Protect shared data for message processing
                if msg == "/quit":
                    break
                elif msg == "/get_online_users" and chat_mode == "private":
                    broadcast_online_users(conn) # Send full list to this private client
                    continue
                elif msg.startswith("GET_ROOM_ONLINE_USERS|") and chat_mode == "public":
                    # This is a specific request for online users in the *current* public room
                    requested_room_id = msg.split('|')[1]
                    if requested_room_id == room_id:
                        broadcast_online_users_in_room(room_id)
                    continue

                current_username, current_room_id = clients.get(conn, (None, None))
                if current_username is None: # Client somehow disconnected or data corrupted
                    break

                timestamp = datetime.now().strftime("%H:%M:%S")
                
                if msg.startswith("PUBLIC_MSG|"):
                    parts = msg.split('|', 2)
                    if len(parts) == 3:
                        room_id_from_msg = parts[1]
                        content = parts[2]
                        if room_id_from_msg == current_room_id: # Ensure message is for client's current room
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
                            # Send to sender
                            sender_msg_data = ("PRIVATE_MSG_RECV", current_username, content, timestamp, f"Bạn (tới {target_username}): {content}")
                            broadcast(sender_msg_data, recipient_conn=conn)
                            
                            # Send to receiver
                            receiver_msg_data = ("PRIVATE_MSG_RECV", current_username, content, timestamp, f"Tin riêng từ {current_username}: {content}")
                            broadcast(receiver_msg_data, recipient_conn=target_conn)
                            
                            save_private_message_to_db(current_username, target_username, content, timestamp)
                        else:
                            system_msg = f"Người dùng '{target_username}' hiện không online."
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
        # If it was a public chat client, update room online list
        if chat_mode == "public" and room_id:
            system_msg = f"{username} đã rời phòng chat."
            broadcast(("SYSTEM_MSG_RECV", "system", system_msg, datetime.now().strftime("%H:%M"), system_msg), room_id=room_id)
            broadcast_online_users_in_room(room_id) # Update online users in THIS room
        # If it was a private chat client, update all private clients' online list
        elif chat_mode == "private":
            broadcast_online_users()


def remove_client(conn):
    with threading.Lock():
        if conn in clients:
            username, room_id = clients[conn]
            
            # Remove from rooms if public
            if room_id and room_id in rooms:
                if conn in rooms[room_id]:
                    rooms[room_id].remove(conn)
                    if not rooms[room_id]: # If room becomes empty, clear its message history
                        room_messages.pop(room_id, None)
                        # Optionally remove room from DB if it becomes empty and no history needed
            
            # Remove from global clients and username mapping
            clients.pop(conn)
            if username in usernames_to_conns and usernames_to_conns[username] == conn:
                usernames_to_conns.pop(username)
                print(f"Removed {username} from online users.")


def send_message_history(conn, room_code):
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor(buffered=True) # Use buffered cursor
        
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
                # Use the same protocol for history as for live messages
                message_data = ("PUBLIC_MSG_RECV", username, content, time_str, f"[{time_str}] {username}: {content}")
                full_msg = f"{message_data[0]}|{message_data[1]}|{message_data[2]}|{message_data[3]}|{message_data[4]}"
                conn.send((full_msg + '\n').encode())
                
        cursor.close()
        db_conn.close()
    except Exception as e:
        print(f"[DB ERROR] Lỗi khi gửi lịch sử tin nhắn phòng {room_code}: {e}")

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
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn.is_connected():
                conn.close()
        except Exception as e:
            print(f"[DB CLOSING ERROR] {e}")


def save_private_message_to_db(sender_username, receiver_username, content, timestamp):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username = %s", (sender_username,))
        sender_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM users WHERE username = %s", (receiver_username,))
        receiver_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO private_messages (sender_id, receiver_id, content, timestamp)
            VALUES (%s, %s, %s, %s)
        """, (sender_id, receiver_id, content, timestamp))
        conn.commit()
    except Exception as e:
        print(f"[DB ERROR] Lỗi khi lưu tin nhắn riêng: {e}")
    finally:
        try:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn.is_connected():
                conn.close()
        except Exception as e:
            print(f"[DB CLOSING ERROR] {e}")


def send_private_message_history(conn, user1_username, user2_username):
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor(buffered=True)

        cursor.execute("SELECT id FROM users WHERE username = %s", (user1_username,))
        user1_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM users WHERE username = %s", (user2_username,))
        user2_id = cursor.fetchone()[0]

        cursor.execute(f"""
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
            # The client should interpret this as a private message
            # and decide whether to display it based on its current target_username
            # We send original sender to client, client determines if it's "Bạn" or "other user"
            message_data = ("PRIVATE_MSG_RECV", sender_u, content, time_str, f"[{time_str}] {sender_u}: {content}")
            full_msg = f"{message_data[0]}|{message_data[1]}|{message_data[2]}|{message_data[3]}|{message_data[4]}"
            conn.send((full_msg + '\n').encode())
            
        cursor.close()
        db_conn.close()
    except Exception as e:
        print(f"[DB ERROR] Lỗi khi gửi lịch sử tin nhắn riêng giữa {user1_username} và {user2_username}: {e}")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Server đang lắng nghe trên {HOST}:{PORT}")
    print("Chờ kết nối...")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()