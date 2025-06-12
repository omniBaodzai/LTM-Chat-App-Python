import socket
import threading
import time
import mysql.connector
import hashlib
 # Import time để có thể thêm dấu thời gian vào tin nhắn nếu cần

# --- Cấu hình Server ---
SERVER_IP = '0.0.0.0'
SERVER_PORT = 12345
BUFFER_SIZE = 1024

# Danh sách các client đã kết nối, mỗi client là một dictionary: {'socket': conn, 'address': addr, 'username': 'unknown'}
connected_clients = []

def broadcast(message, sender_conn=None):
    """
    Gửi tin nhắn đến tất cả các client đã kết nối, trừ người gửi.
    message: Tin nhắn đã được mã hóa (bytes).
    sender_conn: Socket của người gửi (để không gửi lại cho chính họ).
    """
    for client_info in connected_clients:
        client_socket = client_info['socket']
        if client_socket != sender_conn:
            try:
                client_socket.send(message)
            except Exception as e:
                print(f"Lỗi khi gửi tin nhắn cho client {client_info['username']} ({client_info['address']}): {e}")
                # Nếu không gửi được, client này có thể đã ngắt kết nối
                remove_client(client_info)


def handle_client(conn, addr):
    client_info = {'socket': conn, 'address': addr, 'username': 'unknown'}
    connected_clients.append(client_info)

    try:
        # Nhận yêu cầu từ client (LOGIN: hoặc REGISTER:)
        auth_msg = conn.recv(BUFFER_SIZE).decode('utf-8')

        if auth_msg.startswith("REGISTER:"):
            _, username, password = auth_msg.split(":", 2)
            if register_user(username, password):
                conn.send("[SERVER]: Đăng ký thành công.".encode('utf-8'))
            else:
                conn.send("[SERVER]: Tên đã tồn tại. Đăng ký thất bại.".encode('utf-8'))
                conn.close()
                return

        elif auth_msg.startswith("LOGIN:"):
            _, username, password = auth_msg.split(":", 2)
            if authenticate_user(username, password):
                conn.send("[SERVER]: Đăng nhập thành công.".encode('utf-8'))
                
            else:
                conn.send("[SERVER]: Sai tên hoặc mật khẩu.".encode('utf-8'))
                conn.close()
                return

        else:
            conn.send("[SERVER]: Yêu cầu không hợp lệ.".encode('utf-8'))
            conn.close()
            return

        client_info['username'] = username
        print(f"✅ {username} đã đăng nhập thành công từ {addr}")
        broadcast(f"[SERVER]: {username} đã tham gia chat.".encode('utf-8'))

        while True:
            msg = conn.recv(BUFFER_SIZE)
            if not msg:
                break

            timestamp = time.strftime("%H:%M:%S", time.localtime())
            full_msg = f"[{timestamp}] [{client_info['username']}]: {msg.decode('utf-8')}".encode('utf-8')
            print(f"Nhận từ {client_info['username']} ({addr}): {msg.decode('utf-8')}")
            broadcast(full_msg, conn)

    except ConnectionResetError:
        print(f"❌ Client {client_info['username']} ({addr}) đã ngắt kết nối đột ngột.")
    except Exception as e:
        print(f"Lỗi khi xử lý client {client_info['username']} ({addr}): {e}")
    finally:
        print(f"❌ Client {client_info['username']} ({addr}) đã ngắt kết nối.")
        broadcast(f"[SERVER]: {client_info['username']} đã rời khỏi chat.".encode('utf-8'))
        remove_client(client_info)
        conn.close()
def remove_client(client_info):
    """Hàm loại bỏ client khỏi danh sách."""
    if client_info in connected_clients:
        connected_clients.remove(client_info)

def handle_server_input():
    """Luồng để server có thể nhập tin nhắn và gửi broadcast."""
    while True:
        try:
            msg = input()
            if msg.strip():
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                full_msg = f"[{timestamp}] [SERVER]: {msg}".encode('utf-8')
                broadcast(full_msg)
        except EOFError: # Bắt Ctrl+D / Ctrl+Z
            print("Server input stopped.")
            break
        except Exception as e:
            print(f"Lỗi khi xử lý input của server: {e}")
            break

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((SERVER_IP, SERVER_PORT))
        server.listen()
        print(f"🟢 Server đang lắng nghe tại địa chỉ {SERVER_IP} cổng {SERVER_PORT}...")

        # Bắt đầu luồng xử lý input từ server console
        threading.Thread(target=handle_server_input, daemon=True).start()

        while True:
            conn, addr = server.accept()
            # Bắt đầu luồng riêng để xử lý client mới
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except OSError as e:
        print(f"Lỗi khởi động server: {e}. Có thể cổng {SERVER_PORT} đang bị sử dụng.")
        print("Vui lòng đảm bảo không có ứng dụng nào khác đang chiếm cổng này.")
    except Exception as e:
        print(f"Lỗi không xác định khi khởi động server: {e}")
    finally:
        server.close()
        print("Server đã đóng.")


if __name__ == "__main__":
    start_server()
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="bangbang",
        database="chatapp"
    )

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hash_password(password)))
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        return False
    finally:
        cur.close()
        conn.close()

def authenticate_user(username, password):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
        result = cur.fetchone()
        if result and result[0] == hash_password(password):
            return True
        else:
            return False
    finally:
        cur.close()
        conn.close()