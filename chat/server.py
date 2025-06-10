import socket
import threading
import sys
import os
import sqlite3
import datetime
import json
import time

# Cấu hình Server
HOST = '0.0.0.0'  # Lắng nghe trên tất cả các địa chỉ IP có sẵn trên máy
PORT = 12345      # Cổng mà server sẽ lắng nghe

# Danh sách các client đang kết nối và thông tin của họ
# {client_socket: {'name': 'username', 'room': 'room_name'}}
clients_info = {} 

# Dictionary để lưu trữ các phòng chat và các socket của client trong mỗi phòng
# {room_name: {socket1, socket2, ...}}
# Khởi tạo sẵn các phòng mặc định
rooms = {
    'General': set(),
    'Phòng 1': set(),
    'Phòng 2': set(),
    'Phòng 3': set()
} 

# Khóa để đồng bộ hóa truy cập vào các biến dùng chung (clients_info, rooms)
data_lock = threading.Lock()

# Cấu hình Database cho Server (để lưu trữ lịch sử chat tổng)
DB_NAME = 'server_chat_history.db'

def init_server_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            sender TEXT,
            message TEXT,
            room_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_server_message(sender, message, room_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO messages (timestamp, sender, message, room_name) VALUES (?, ?, ?, ?)",
                   (timestamp, sender, message, room_name))
    conn.commit()
    conn.close()

def broadcast(message, room_name, sender_socket=None):
    """Gửi tin nhắn đến tất cả các client trong một phòng cụ thể."""
    with data_lock:
        if room_name not in rooms:
            print(f"Lỗi: Phòng '{room_name}' không tồn tại để gửi tin nhắn.")
            return

        # Tạo một bản sao của set để tránh lỗi RuntimeError: Set changed size during iteration
        for client_socket in list(rooms[room_name]): 
            if client_socket != sender_socket:
                try:
                    client_socket.send(message)
                except Exception as e:
                    print(f"Lỗi gửi tin nhắn đến client: {e}. Đang xóa client.")
                    remove_client(client_socket) # Xóa client bị lỗi


def handle_client(client_socket, client_address):
    """Xử lý giao tiếp với từng client cụ thể."""
    print(f"Client {client_address} đã kết nối.")
    client_socket.send("WELCOME_TO_CHAT_SERVER".encode('utf-8')) # Gửi tín hiệu chào mừng ban đầu

    client_name = ""
    current_room = "" # Sẽ được gán sau khi xác thực tên

    try:
        # Nhận tên người dùng
        name_data = client_socket.recv(1024)
        client_name = name_data.decode('utf-8').strip()

        with data_lock:
            # Kiểm tra tên trùng lặp
            existing_names = [info['name'] for info in clients_info.values() if info.get('name')]
            if not client_name or client_name in existing_names:
                client_socket.send("ERROR: Tên không hợp lệ hoặc đã tồn tại. Vui lòng chọn tên khác.\n".encode('utf-8')) # Phản hồi rõ ràng hơn
                client_socket.close()
                print(f"Từ chối kết nối client {client_address}: Tên '{client_name}' không hợp lệ hoặc đã tồn tại.")
                return

            clients_info[client_socket] = {'name': client_name, 'room': ''} # Ban đầu không ở phòng nào

        print(f"Client {client_address} đăng ký với tên: {client_name}")
        
        # Gửi thông báo xác nhận tên. KHÔNG TỰ ĐỘNG THÊM CLIENT VÀO BẤT KỲ PHÒNG NÀO TẠI ĐÂY.
        client_socket.send(f"ACK: Tên '{client_name}' đã được chấp nhận.\n".encode('utf-8'))
        
        print(f"{client_name} đã đăng nhập thành công và chờ chọn phòng.")
        current_room = "" # Đảm bảo phòng hiện tại là rỗng trên server cho đến khi client join

        while True:
            try:
                message_data = client_socket.recv(4096) # Tăng kích thước buffer để tránh mất tin nhắn dài
                if not message_data: # Client ngắt kết nối
                    break
                
                message = message_data.decode('utf-8').strip()
                
                with data_lock:
                    if client_socket in clients_info:
                        client_name_current = clients_info[client_socket]['name']
                        current_room = clients_info[client_socket]['room'] # Cập nhật phòng hiện tại từ info
                    else:
                        break # Client đã bị xóa khỏi danh sách, thoát luồng

                print(f"Nhận được từ {client_name_current} (phòng '{current_room if current_room else 'Lobby'}'): {message}")

                # Xử lý lệnh từ client
                if message.startswith('/join '):
                    new_room_name = message[len('/join '):].strip()
                    if new_room_name:
                        with data_lock:
                            # Rời phòng cũ nếu có
                            if current_room and client_socket in rooms.get(current_room, set()):
                                rooms[current_room].remove(client_socket)
                                # Xóa phòng nếu không còn ai và không phải là phòng mặc định
                                if not rooms[current_room] and current_room not in ['General', 'Phòng 1', 'Phòng 2', 'Phòng 3']:
                                    del rooms[current_room]
                                    print(f"Phòng '{current_room}' trống và đã bị xóa.")
                                leave_msg = f"{client_name_current} đã rời phòng '{current_room}'.".encode('utf-8')
                                broadcast(leave_msg, current_room, client_socket)
                                save_server_message("SERVER", leave_msg.decode('utf-8'), current_room)

                            # Tham gia hoặc tạo phòng mới
                            if new_room_name not in rooms:
                                rooms[new_room_name] = set() # Tạo phòng mới nếu chưa tồn tại
                                print(f"Đã tạo phòng mới: {new_room_name}")

                            rooms[new_room_name].add(client_socket)
                            clients_info[client_socket]['room'] = new_room_name
                            current_room = new_room_name # Cập nhật biến cục bộ
                            
                            client_socket.send(f"Bạn đã tham gia phòng '{new_room_name}'.\n".encode('utf-8'))
                            join_msg = f"{client_name_current} đã tham gia phòng '{new_room_name}'!".encode('utf-8')
                            broadcast(join_msg, new_room_name, client_socket)
                            save_server_message("SERVER", join_msg.decode('utf-8'), new_room_name)
                            print(f"{client_name_current} đã tham gia phòng '{new_room_name}'")
                    else:
                        client_socket.send("Cách dùng: /join <tên_phòng>\n".encode('utf-8'))
                elif message.startswith('/listrooms'):
                    with data_lock:
                        # Gửi danh sách phòng dưới dạng JSON để client dễ phân tích
                        room_list = list(rooms.keys())
                        client_socket.send(f"ROOM_LIST:{json.dumps(room_list)}\n".encode('utf-8'))
                elif message.startswith('/users'): # Lệnh xem người dùng trong phòng
                    with data_lock:
                        if not current_room:
                            client_socket.send("Bạn phải ở trong một phòng để xem danh sách người dùng.\n".encode('utf-8'))
                        else:
                            current_room_clients = rooms.get(current_room, set())
                            user_names_in_room = [clients_info[s]['name'] for s in current_room_clients if s in clients_info]
                            client_socket.send(f"Người dùng trong phòng '{current_room}': {', '.join(user_names_in_room)}\n".encode('utf-8'))
                elif message.startswith('/quit'):
                    break # Client muốn thoát
                else:
                    # Chỉ xử lý tin nhắn nếu client đã ở trong một phòng
                    if current_room:
                        formatted_message = f"[{client_name_current}]: {message}".encode('utf-8')
                        broadcast(formatted_message, current_room, client_socket)
                        save_server_message(client_name_current, message, current_room)
                    else:
                        client_socket.send("Bạn phải tham gia một phòng để gửi tin nhắn. Dùng /join <tên_phòng>.\n".encode('utf-8'))

            except ConnectionResetError:
                print(f"Client {client_name_current} ({client_address}) đóng ứng dụng đột ngột.")
                break # Client đóng ứng dụng đột ngột
            except Exception as e:
                print(f"Lỗi trong vòng lặp giao tiếp client cho {client_address}: {e}")
                break # Thoát vòng lặp nếu có lỗi

    except Exception as e:
        print(f"Lỗi trong quá trình thiết lập kết nối client cho {client_address}: {e}")
    finally:
        # Đảm bảo client được xóa khỏi mọi nơi
        remove_client(client_socket)
        print(f"Client {client_address} đã ngắt kết nối.")

def remove_client(client_socket):
    """Xóa client khỏi danh sách và phòng khi họ ngắt kết nối."""
    with data_lock:
        if client_socket in clients_info:
            client_name = clients_info[client_socket]['name']
            client_room = clients_info[client_socket]['room']

            # Xóa khỏi phòng hiện tại nếu đang ở trong phòng
            if client_room and client_room in rooms and client_socket in rooms[client_room]:
                rooms[client_room].remove(client_socket)
                # Xóa phòng nếu không còn client nào và không phải là phòng mặc định
                if not rooms[client_room] and client_room not in ['General', 'Phòng 1', 'Phòng 2', 'Phòng 3']:
                    del rooms[client_room]
                    print(f"Phòng '{client_room}' trống và đã bị xóa.")
                else:
                    # Thông báo mọi người trong phòng rằng client đã rời đi
                    leave_msg = f"{client_name} đã rời phòng '{client_room}'.".encode('utf-8')
                    broadcast(leave_msg, client_room)
                    save_server_message("SERVER", leave_msg.decode('utf-8'), client_room)

            # Xóa khỏi danh sách clients_info
            del clients_info[client_socket]
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except OSError as e:
                print(f"Lỗi khi shutdown socket cho {client_name}: {e}")
            finally:
                client_socket.close()
            print(f"Đã xóa {client_name} khỏi danh sách client hoạt động.")
        else:
            try: # Đảm bảo socket được đóng nếu nó chưa bị đóng
                client_socket.close()
            except:
                pass


def start_server():
    """Khởi động server và lắng nghe kết nối."""
    init_server_db() # Khởi tạo database server

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Cho phép tái sử dụng địa chỉ

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5) # Cho phép tối đa 5 kết nối đang chờ
        print(f"Máy chủ đã khởi động trên {HOST}:{PORT}")
        print("Đang chờ kết nối...")

        while True:
            client_socket, client_address = server_socket.accept() # Chấp nhận kết nối mới
            # Tạo một luồng riêng để xử lý client này
            client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_handler.daemon = True # Đặt luồng là daemon để nó tự đóng khi chương trình chính thoát
            client_handler.start()
    except Exception as e:
        print(f"Lỗi khi khởi động máy chủ: {e}")
    finally:
        print("Máy chủ đang tắt.")
        server_socket.close()
        # Đảm bảo đóng tất cả client sockets còn lại khi server tắt
        with data_lock:
            for client_socket in list(clients_info.keys()): # Lặp trên một bản sao để tránh lỗi thay đổi trong khi lặp
                remove_client(client_socket)

if __name__ == "__main__":
    start_server()