import socket
import threading
import sys
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
import queue
import sqlite3
import datetime
import re
import time
import os
import json

# Cấu hình Client
# IMPORTANT: Thay đổi SERVER_HOST nếu server chạy trên máy khác!
# Nếu server chạy trên cùng máy tính với client: SERVER_HOST = '127.0.0.1'
# Nếu server chạy trên máy có IP 192.168.1.17: SERVER_HOST = '192.168.1.17'
SERVER_HOST = '127.0.0.1' # Đặt mặc định là localhost cho môi trường thử nghiệm
SERVER_PORT = 12345

# Thư mục lưu trữ database lịch sử chat
DB_DIR = "chat_history_dbs"

class ChatClient:
    def __init__(self, master):
        self.master = master
        
        self.client_socket = None 
        self.name = "" 
        self.message_queue = queue.Queue() 

        self.current_room = "" # Ban đầu client không ở phòng nào
        self.db_name = None 

        self.is_connected = False
        self.connect_thread = None 
        self.receive_thread = None 
        self.room_list = [] # Danh sách các phòng hiện có từ server

        # Event để ra hiệu cho luồng nhận tin nhắn dừng lại
        self.stop_event = threading.Event() 

        # Đảm bảo thư mục DB tồn tại
        os.makedirs(DB_DIR, exist_ok=True)

        self.master.title("Python Chat Client")
        self.master.geometry("600x600")

        # --- Frames cho các màn hình khác nhau ---
        self.home_frame = tk.Frame(master)
        self.chat_frame = tk.Frame(master)

        # Khởi tạo màn hình Home
        self._setup_home_screen()
        # Khởi tạo màn hình Chat (ban đầu ẩn)
        self._setup_chat_screen()

        # Hiển thị màn hình Home trước
        self.show_home_screen() # Hiển thị màn hình home ngay từ đầu, sẽ được cập nhật sau khi kết nối

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Bắt đầu kiểm tra hàng đợi tin nhắn định kỳ trên luồng chính
        self.master.after(100, self.process_queue) 

        # Bắt đầu kết nối đến server trong một luồng riêng
        # Đảm bảo luồng này chỉ khởi tạo một lần
        self.connect_thread = threading.Thread(target=self._initial_connection_setup)
        self.connect_thread.daemon = True 
        self.connect_thread.start()

    def show_home_screen(self):
        self.chat_frame.pack_forget() # Ẩn màn hình chat nếu đang hiển thị
        self.home_frame.pack(fill='both', expand=True, padx=10, pady=10)
        # Cập nhật label tên người dùng
        if self.name:
            self.username_label.config(text=f"Tên của bạn: {self.name}")
            self.master.title(f"Chào mừng, {self.name}!")
        else:
            self.username_label.config(text="Tên của bạn: CHƯA KẾT NỐI")
            self.master.title("Python Chat Client")

        # Chỉ cập nhật danh sách phòng nếu đã kết nối thành công và có tên
        if self.is_connected and self.name:
            self.list_rooms_initial() # Cập nhật danh sách phòng ngay lập tức

    def show_chat_screen(self):
        self.home_frame.pack_forget() # Ẩn màn hình home
        self.chat_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.master.title(f"Python Chat Client - {self.name} (Phòng: {self.current_room})")
        self.load_chat_history(self.current_room) # Tải lịch sử cho phòng mới

    # --- Setup GUI for different screens ---
    def _setup_home_screen(self):
        # Tên người dùng hiện tại
        self.username_label = tk.Label(self.home_frame, text="Tên của bạn: CHƯA KẾT NỐI", font=("Arial", 12, "bold"))
        self.username_label.pack(pady=(10, 20))

        # Khung chứa các nút điều khiển phòng
        room_actions_frame = tk.Frame(self.home_frame)
        room_actions_frame.pack(pady=10)

        self.create_room_button = tk.Button(room_actions_frame, text="Tạo phòng mới", command=self.create_new_room, font=("Arial", 10))
        self.create_room_button.pack(side='left', padx=5)

        self.refresh_rooms_button = tk.Button(room_actions_frame, text="Làm mới danh sách phòng", command=self.list_rooms_initial, font=("Arial", 10))
        self.refresh_rooms_button.pack(side='left', padx=5)

        # Danh sách các phòng
        tk.Label(self.home_frame, text="Các phòng chat hiện có:", font=("Arial", 11, "underline")).pack(pady=(20, 5))
        
        self.room_list_frame = tk.Frame(self.home_frame)
        self.room_list_frame.pack(fill='x', padx=20, pady=5)
        # Sử dụng Canvas và Scrollbar nếu có nhiều phòng
        self.room_canvas = tk.Canvas(self.room_list_frame)
        self.room_canvas.pack(side='left', fill='both', expand=True)

        self.room_scrollbar = tk.Scrollbar(self.room_list_frame, orient='vertical', command=self.room_canvas.yview)
        self.room_scrollbar.pack(side='right', fill='y')

        self.room_canvas.configure(yscrollcommand=self.room_scrollbar.set)
        # Bắt sự kiện thay đổi kích thước của canvas để cập nhật scrollregion
        self.room_canvas.bind('<Configure>', lambda e: self.room_canvas.configure(scrollregion = self.room_canvas.bbox("all")))

        self.rooms_inner_frame = tk.Frame(self.room_canvas)
        self.room_canvas.create_window((0, 0), window=self.rooms_inner_frame, anchor="nw")

        # Bắt sự kiện thay đổi kích thước của inner frame để cập nhật scrollregion
        self.rooms_inner_frame.bind("<Configure>", lambda e: self.room_canvas.configure(scrollregion = self.room_canvas.bbox("all")))
        
        # Initial call to populate room list (will be updated from server)
        self.update_room_list_display([])


    def _setup_chat_screen(self):
        self.room_control_frame = tk.Frame(self.chat_frame)
        self.room_control_frame.pack(padx=10, pady=5, fill='x')

        self.leave_room_button = tk.Button(self.room_control_frame, text="Rời phòng", command=self.leave_current_room)
        self.leave_room_button.pack(side='left', padx=(0, 5))

        self.list_users_button_chat = tk.Button(self.room_control_frame, text="Người dùng trong phòng", command=self.list_users_in_room)
        self.list_users_button_chat.pack(side='left', padx=(0, 5))

        self.current_room_label = tk.Label(self.room_control_frame, text=f"Phòng hiện tại: {self.current_room}", font=("Arial", 10, "bold"))
        self.current_room_label.pack(side='right')

        self.chat_history = scrolledtext.ScrolledText(self.chat_frame, state='disabled', wrap='word', font=("Arial", 10))
        self.chat_history.pack(padx=10, pady=10, fill='both', expand=True)

        self.message_frame = tk.Frame(self.chat_frame)
        self.message_frame.pack(padx=10, pady=5, fill='x')

        self.message_entry = tk.Entry(self.message_frame, width=30, font=("Arial", 10))
        self.message_entry.pack(side='left', fill='x', expand=True)
        self.message_entry.bind("<Return>", self.send_message_event)

        self.send_button = tk.Button(self.message_frame, text="Gửi", command=self.send_message)
        self.send_button.pack(side='right', padx=(5, 0))

    # --- Database Methods ---
    def init_db(self):
        """Khởi tạo database cho người dùng hiện tại."""
        if not self.name:
            print("Chưa có tên người dùng, không thể khởi tạo DB.")
            return False
        
        self.db_name = os.path.join(DB_DIR, f'chat_history_{self.name}.db')
        try:
            conn = sqlite3.connect(self.db_name)
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
            print(f"Đã khởi tạo/mở database: {self.db_name}")
            return True
        except sqlite3.Error as e:
            print(f"Lỗi khi khởi tạo database {self.db_name}: {e}")
            self.add_message_to_queue(f"Lỗi database: Không thể khởi tạo lịch sử chat: {e}")
            return False

    def save_message_to_db(self, sender, message, room_name):
        """Lưu tin nhắn vào database của người dùng."""
        # Chỉ lưu nếu có tên và có DB
        if not self.name or not self.db_name:
            return
        
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            # Sử dụng định dạng紝-MM-DD HH:MM:SS để khớp với server
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
            cursor.execute("INSERT INTO messages (timestamp, sender, message, room_name) VALUES (?, ?, ?, ?)",
                           (timestamp, sender, message, room_name))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Lỗi khi lưu tin nhắn vào DB {self.db_name}: {e}")
            # self.add_message_to_queue(f"Lỗi: Không thể lưu tin nhắn vào lịch sử: {e}") # Tránh spam queue

    def load_chat_history(self, room_name):
        """Tải và hiển thị lịch sử chat cho phòng đã cho."""
        self.chat_history.config(state='normal')
        self.chat_history.delete(1.0, tk.END) 

        if not self.name or not self.db_name:
            self.chat_history.insert(tk.END, "Không thể tải lịch sử chat (chưa có tên người dùng hoặc DB).\n")
            self.chat_history.config(state='disabled')
            return

        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, sender, message FROM messages WHERE room_name = ? ORDER BY timestamp", (room_name,))
            messages = cursor.fetchall()
            conn.close()
            
            for ts, sender, msg in messages:
                self.chat_history.insert(tk.END, f"[{ts}] {sender}: {msg}\n")
            print(f"Đã tải lịch sử chat cho phòng '{room_name}'.")
        except sqlite3.Error as e:
            print(f"Lỗi khi tải lịch sử chat cho phòng '{room_name}': {e}")
            self.chat_history.insert(tk.END, f"Lỗi khi tải lịch sử chat cho phòng '{room_name}': {e}\n")
        
        self.chat_history.config(state='disabled')
        self.chat_history.yview(tk.END)


    # --- Network Connection Methods ---
    def _initial_connection_setup(self):
        """Thiết lập kết nối ban đầu với server (trong luồng riêng)."""
        if self.stop_event.is_set(): 
            print("Đã có tín hiệu dừng, không khởi tạo kết nối.")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(2.0) 
            self.add_message_to_queue(f"Đang cố gắng kết nối tới {SERVER_HOST}:{SERVER_PORT}...")
            self.client_socket.connect((SERVER_HOST, SERVER_PORT))
            self.is_connected = True
            self.add_message_to_queue("Đã kết nối tới máy chủ.")

            initial_server_response = self.client_socket.recv(1024).decode('utf-8').strip()
            print(f"Server chào mừng: '{initial_server_response}'") 
            if initial_server_response != "WELCOME_TO_CHAT_SERVER":
                self.add_message_to_queue(f"Lỗi: Server phản hồi không mong muốn: {initial_server_response}. Ứng dụng sẽ đóng.")
                self._handle_connection_error(fatal=True)
                return

            self.client_socket.settimeout(0.5) 
            self.receive_thread = threading.Thread(target=self._receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()

            self.master.after(0, self._request_username)

        except ConnectionRefusedError:
            self.add_message_to_queue(f"Lỗi kết nối: Không thể kết nối. Đảm bảo máy chủ đang chạy trên {SERVER_HOST}:{SERVER_PORT} và tường lửa đã mở.")
            self._handle_connection_error()
        except socket.timeout:
            self.add_message_to_queue(f"Lỗi kết nối: Thời gian chờ kết nối đã hết.")
            self._handle_connection_error()
        except OSError as e: 
            self.add_message_to_queue(f"Lỗi socket khi kết nối: {e}. Ứng dụng sẽ đóng.")
            self._handle_connection_error()
        except Exception as e:
            self.add_message_to_queue(f"Lỗi không xác định khi kết nối tới máy chủ: {e}. Ứng dụng sẽ đóng.")
            self._handle_connection_error()

    def _request_username(self):
        """Hiển thị hộp thoại yêu cầu tên người dùng trên luồng chính."""
        if self.stop_event.is_set() or not self.is_connected or self.client_socket is None:
            print("Client đang dừng hoặc không kết nối, không thể yêu cầu tên người dùng.")
            if self.master.winfo_exists(): 
                self.master.destroy() 
            return

        while not self.stop_event.is_set() and self.is_connected:
            self.name = simpledialog.askstring("Nhập tên", "Vui lòng nhập tên của bạn:", parent=self.master)
            
            if self.name is None: 
                self.name = "" 
                self.add_message_to_queue("Người dùng đã hủy nhập tên. Ứng dụng sẽ đóng.")
                self._handle_connection_error(fatal=True)
                return
            elif not self.name.strip(): 
                response = messagebox.askretrycancel("Lỗi tên", "Tên không được để trống. Thử lại?", parent=self.master)
                if not response:
                    self.name = "" 
                    self.add_message_to_queue("Người dùng đã hủy nhập tên. Ứng dụng sẽ đóng.")
                    self._handle_connection_error(fatal=True)
                    return
            else:
                try:
                    if self.client_socket is None or not self.is_connected: 
                        self.add_message_to_queue("Socket không tồn tại hoặc đã bị đóng, không thể gửi tên.")
                        self._handle_connection_error(fatal=True)
                        return

                    self.client_socket.send(self.name.encode('utf-8'))
                    
                    server_response_after_name = self.client_socket.recv(1024).decode('utf-8').strip()
                    print(f"Server phản hồi tên: '{server_response_after_name}'") 

                    if server_response_after_name.startswith("ERROR:"): 
                        messagebox.showerror("Lỗi tên", server_response_after_name.strip() + "\nThử lại?", parent=self.master)
                    elif server_response_after_name.startswith("ACK:"): # Server chỉ gửi ACK xác nhận tên
                        self.add_message_to_queue(f"Đăng nhập thành công: {server_response_after_name.strip()}")
                        self.username_label.config(text=f"Tên của bạn: {self.name}") 
                        if self.init_db(): 
                            self.current_room = "" # Đảm bảo không có phòng nào được set
                            self.master.after(0, self.show_home_screen) # Hiển thị màn hình chính
                        break # Thoát vòng lặp yêu cầu tên
                    else: # Phản hồi không mong muốn (ví dụ: vẫn nhận được "Bạn đã tham gia phòng...")
                        self.add_message_to_queue(f"Server phản hồi không mong muốn sau khi gửi tên: '{server_response_after_name}'. Ứng dụng sẽ đóng.")
                        messagebox.showerror("Lỗi Server", f"Server phản hồi không mong muốn sau khi gửi tên: {server_response_after_name}. Ứng dụng sẽ đóng.", parent=self.master)
                        self._handle_connection_error(fatal=True)
                        return

                except socket.timeout:
                    self.add_message_to_queue("Thời gian chờ phản hồi tên đã hết. Ngắt kết nối.")
                    messagebox.showerror("Lỗi", "Thời gian chờ phản hồi tên đã hết. Vui lòng thử lại.", parent=self.master)
                    self._handle_connection_error(fatal=True)
                    return
                except (ConnectionResetError, BrokenPipeError, OSError) as e:
                    self.add_message_to_queue(f"Lỗi mạng khi gửi/nhận tên: {e}. Ngắt kết nối.")
                    messagebox.showerror("Lỗi", f"Lỗi mạng khi xác thực tên người dùng: {e}", parent=self.master)
                    self._handle_connection_error(fatal=True)
                    return
                except Exception as e:
                    self.add_message_to_queue(f"Lỗi không xác định khi gửi/nhận tên: {e}")
                    messagebox.showerror("Lỗi", f"Lỗi khi xác thực tên người dùng: {e}", parent=self.master)
                    self._handle_connection_error(fatal=True)
                    return
        
        # Sau khi có tên, luôn hiển thị màn hình chính để người dùng chọn phòng
        if self.name and self.is_connected and not self.stop_event.is_set() and self.master.winfo_exists():
            self.show_home_screen()

    def _receive_messages(self):
        """Luồng riêng để nhận tin nhắn từ server."""
        while not self.stop_event.is_set(): 
            try:
                if self.client_socket is None or not self.is_connected: 
                    break 

                message = self.client_socket.recv(4096).decode('utf-8') 
                if message:
                    if message.startswith("ROOM_LIST:"):
                        try:
                            json_data = message[len("ROOM_LIST:"):].strip()
                            self.room_list = json.loads(json_data)
                            self.master.after(0, lambda: self.update_room_list_display(self.room_list))
                            self.add_message_to_queue("Đã cập nhật danh sách phòng.")
                        except json.JSONDecodeError as e:
                            self.add_message_to_queue(f"Lỗi phân tích JSON danh sách phòng: {e} - Dữ liệu nhận được: {json_data[:100]}...") 
                        except Exception as e: 
                             self.add_message_to_queue(f"Lỗi không xác định khi xử lý ROOM_LIST: {e}")
                    elif message.startswith("ACK:"): 
                        self.add_message_to_queue(message.strip())
                    elif message.startswith("ERROR:"): 
                        self.add_message_to_queue(f"Lỗi từ server: {message.strip()}")
                    elif message.startswith("Người dùng trong phòng '"): # Xử lý phản hồi từ /users
                        self.add_message_to_queue(message.strip())
                    else: # Tin nhắn chat hoặc thông báo khác từ server
                        self.add_message_to_queue(message.strip())
                        
                        # Kiểm tra nếu tin nhắn là thông báo chuyển phòng từ server (khi dùng lệnh /join)
                        match = re.search(r"Bạn đã tham gia phòng '([^']+)'", message)
                        if match:
                            new_room_from_server = match.group(1)
                            self.master.after(0, lambda: self._set_current_room_and_load_history(new_room_from_server))
                            self.master.after(0, self.show_chat_screen) 
                        
                else: 
                    self.add_message_to_queue("Máy chủ đã ngắt kết nối. Ứng dụng sẽ đóng.")
                    self._handle_connection_error() 
                    break 
            except socket.timeout: 
                continue
            except (ConnectionResetError, BrokenPipeError):
                self.add_message_to_queue("Máy chủ ngắt kết nối đột ngột. Ứng dụng sẽ đóng.")
                self._handle_connection_error()
                break
            except OSError as e: 
                if self.stop_event.is_set():
                    break 
                else:
                    self.add_message_to_queue(f"Lỗi socket khi nhận tin: {e}. Ứng dụng sẽ đóng.")
                    self._handle_connection_error()
                    break
            except Exception as e:
                if self.stop_event.is_set(): 
                    break
                else:
                    self.add_message_to_queue(f"Lỗi nhận tin nhắn không xác định: {e}. Ứng dụng sẽ đóng.")
                    self._handle_connection_error()
                    break 
        
        print("Luồng nhận tin nhắn đã kết thúc.")

    def send_message(self):
        if not self.is_connected or self.client_socket is None or self.stop_event.is_set():
            messagebox.showwarning("Cảnh báo", "Bạn chưa kết nối với máy chủ hoặc ứng dụng đang đóng.")
            return
        if not self.current_room:
            messagebox.showwarning("Cảnh báo", "Bạn phải tham gia một phòng để gửi tin nhắn.")
            return

        message = self.message_entry.get()
        if not message.strip(): 
            return

        try:
            self.client_socket.send(message.encode('utf-8'))
            
            # HIỂN THỊ TIN NHẮN CỦA CHÍNH MÌNH NGAY LẬP TỨC
            # Sử dụng định dạng tương tự server để dễ quản lý trong DB/hiển thị
            formatted_local_message = f"[{self.name}]: {message}" 
            self.add_message_to_queue(formatted_local_message) 
            self.save_message_to_db(self.name, message, self.current_room)

            self.message_entry.delete(0, tk.END) 
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            self.add_message_to_queue(f"Lỗi gửi tin nhắn: {e}")
            messagebox.showerror("Lỗi", "Không thể gửi tin nhắn. Có lẽ đã ngắt kết nối.")
            self._handle_connection_error()
        except Exception as e:
            self.add_message_to_queue(f"Lỗi không xác định khi gửi tin nhắn: {e}")
            messagebox.showerror("Lỗi", "Không thể gửi tin nhắn. Có lẽ đã ngắt kết nối.")
            self._handle_connection_error()
        
    def send_message_event(self, event):
        self.send_message()

    # --- GUI Update and Queue Processing ---
    def add_message_to_queue(self, message):
        self.message_queue.put(message)

    def process_queue(self):
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                self._append_to_chat_internal(message)
        except queue.Empty:
            pass
        finally:
            if not self.stop_event.is_set() and self.master.winfo_exists(): 
                self.master.after(100, self.process_queue)

    def _append_to_chat_internal(self, message):
        """Hàm nội bộ để thêm tin nhắn vào hộp chat (chỉ gọi từ luồng chính)."""
        if not self.master.winfo_exists(): 
            return 
        
        if self.chat_history.winfo_ismapped(): 
            self.chat_history.config(state='normal') 
            self.chat_history.insert(tk.END, message + "\n") 
            self.chat_history.config(state='disabled') 
            self.chat_history.yview(tk.END)

        sender_name_for_db = "SERVER" 
        msg_content_for_db = message
        room_for_db = self.current_room 

        # Phân tích tin nhắn từ server: "[Tên]: Tin nhắn" hoặc "SERVER: Tin nhắn"
        match_chat_msg = re.match(r"^\[([^\]]+)\]: (.*)", message)
        if match_chat_msg:
            sender_name_for_db = match_chat_msg.group(1)
            msg_content_for_db = match_chat_msg.group(2).strip()
            room_for_db = self.current_room # Tin nhắn chat luôn thuộc phòng hiện tại
        elif message.startswith("SERVER:") or message.startswith("ACK:") or message.startswith("ERROR:"):
            sender_name_for_db = "SERVER"
            # Giữ nguyên message cho nội dung, cắt bỏ tiền tố
            msg_content_for_db = message.strip() 
        elif message.startswith("Người dùng trong phòng '"): # Thông báo /users
            sender_name_for_db = "SERVER"
            msg_content_for_db = message.strip()
        
        # Nếu tin nhắn là thông báo tham gia/rời phòng từ server, trích xuất phòng từ đó
        join_leave_match = re.search(r"(?:đã tham gia phòng|đã rời phòng) '([^']+)'", message)
        if join_leave_match:
            room_for_db = join_leave_match.group(1)
            sender_name_for_db = "SERVER" # Người gửi là server cho thông báo này
            msg_content_for_db = message # Giữ nguyên tin nhắn cho DB

        # Chỉ lưu tin nhắn vào DB nếu có nội dung và có phòng hiện tại
        # Các thông báo server chung có thể không thuộc về một phòng cụ thể
        if msg_content_for_db and room_for_db: 
            self.save_message_to_db(sender_name_for_db, msg_content_for_db, room_for_db)


    # --- Room Management Methods (GUI triggered) ---
    def _set_current_room_and_load_history(self, new_room_name):
        """Cập nhật phòng hiển thị, tiêu đề cửa sổ và tải lịch sử mới."""
        if self.current_room != new_room_name: 
            self.current_room = new_room_name
            self.current_room_label.config(text=f"Phòng hiện tại: {self.current_room}")
            self.master.title(f"Python Chat Client - {self.name} (Phòng: {self.current_room})")
            
            self.load_chat_history(self.current_room)
        else:
            self.load_chat_history(self.current_room)

    def create_new_room(self):
        if not self.is_connected or not self.name or self.stop_event.is_set():
            messagebox.showwarning("Cảnh báo", "Bạn chưa kết nối hoặc chưa có tên người dùng.")
            return

        new_room_name = simpledialog.askstring("Tạo phòng mới", "Nhập tên phòng mới:", parent=self.master)
        if new_room_name and new_room_name.strip():
            self.send_command(f"/join {new_room_name.strip()}")
            # Yêu cầu cập nhật danh sách phòng sau khi gửi lệnh join
            self.master.after(100, self.list_rooms_initial) # Đặt sau 100ms để server có thời gian xử lý
        elif new_room_name is not None: 
            messagebox.showwarning("Cảnh báo", "Tên phòng không được để trống.")
    
    def join_room_from_list(self, room_name):
        if not self.is_connected or not self.name or self.stop_event.is_set():
            messagebox.showwarning("Cảnh báo", "Bạn chưa kết nối hoặc chưa có tên người dùng.")
            return
        self.send_command(f"/join {room_name}")


    def list_rooms_initial(self):
        """Gửi lệnh /listrooms khi vào màn hình chính."""
        if not self.is_connected or not self.name or self.stop_event.is_set():
            return
        self.send_command("/listrooms")

    def update_room_list_display(self, rooms_list):
        """Cập nhật giao diện danh sách phòng trên home screen."""
        for widget in self.rooms_inner_frame.winfo_children():
            widget.destroy() 

        if not rooms_list:
            tk.Label(self.rooms_inner_frame, text="Không có phòng nào khả dụng.", font=("Arial", 10, "italic")).pack(pady=5)
            return

        for room in sorted(rooms_list): 
            row_frame = tk.Frame(self.rooms_inner_frame, bd=1, relief="groove")
            row_frame.pack(fill='x', pady=2)
            
            tk.Label(row_frame, text=f"Phòng: {room}", font=("Arial", 10, "bold")).pack(side='left', padx=5, pady=2)
            tk.Button(row_frame, text="Vào phòng", command=lambda r=room: self.join_room_from_list(r), font=("Arial", 9)).pack(side='right', padx=5, pady=2)
        
        self.rooms_inner_frame.update_idletasks()
        self.room_canvas.config(scrollregion=self.room_canvas.bbox("all"))

    def leave_current_room(self):
        if not self.is_connected or not self.name or self.stop_event.is_set():
            messagebox.showwarning("Cảnh báo", "Bạn chưa kết nối hoặc chưa có tên người dùng.")
            return
        if self.current_room:
            # Gửi lệnh join phòng "General" để server biết client đã rời phòng cũ
            # và sau đó chuyển về màn hình chính client-side
            # Chúng ta sẽ không thực sự "join" General mà chỉ gửi lệnh này để server cập nhật trạng thái phòng
            if self.current_room != "General": # Tránh gửi lại nếu đã ở General
                self.send_command("/join General") 
            
            self.current_room = "" # Client reset phòng hiện tại
            self.master.title(f"Python Chat Client - {self.name}")
            self.show_home_screen()
            self.add_message_to_queue("Bạn đã rời phòng chat và quay về màn hình chính.")
            self.list_rooms_initial() 

        else:
            messagebox.showinfo("Thông báo", "Bạn hiện không ở trong phòng nào.")

    def list_users_in_room(self):
        if not self.is_connected or not self.name or self.stop_event.is_set():
            messagebox.showwarning("Cảnh báo", "Bạn chưa kết nối hoặc chưa có tên người dùng.")
            return
        if not self.current_room:
            messagebox.showwarning("Cảnh báo", "Bạn phải ở trong một phòng để xem danh sách người dùng.")
            return
        self.send_command("/users")

    def send_command(self, command):
        """Gửi các lệnh đặc biệt đến server."""
        if self.client_socket is None or not self.is_connected or self.stop_event.is_set(): 
            messagebox.showwarning("Cảnh báo", "Bạn không còn kết nối với máy chủ hoặc ứng dụng đang đóng. Không thể gửi lệnh.")
            return

        try:
            self.client_socket.send(command.encode('utf-8'))
            self.message_entry.delete(0, tk.END) 
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            self.add_message_to_queue(f"Lỗi gửi lệnh: {e}")
            messagebox.showerror("Lỗi", "Không thể gửi lệnh. Có lẽ đã ngắt kết nối.")
            self._handle_connection_error()
        except Exception as e:
            self.add_message_to_queue(f"Lỗi không xác định khi gửi lệnh: {e}")
            messagebox.showerror("Lỗi", "Không thể gửi lệnh. Có lẽ đã ngắt kết nối.")
            self._handle_connection_error()

    def _close_socket(self):
        """Đóng socket một cách an toàn."""
        sock_to_close = self.client_socket
        self.client_socket = None 
        self.is_connected = False 

        if sock_to_close:
            try:
                sock_to_close.settimeout(0.1) 
                sock_to_close.shutdown(socket.SHUT_RDWR) 
                print("Socket shutdown thành công.")
            except OSError as e:
                if e.errno in (9, 107, 10009, 10057): 
                    print(f"Socket đã không còn kết nối hoặc đã đóng trong khi shutdown: {e}")
                else:
                    print(f"Lỗi khi shutdown socket: {e}")
            finally:
                try:
                    sock_to_close.close()
                    print("Socket đã được đóng.")
                except OSError as e:
                    print(f"Lỗi khi đóng socket: {e}")
        else:
            print("Socket đã là None, không cần đóng.")

    def _handle_connection_error(self, fatal=False):
        """Xử lý lỗi kết nối, tắt ứng dụng một cách duyên dáng."""
        if self.stop_event.is_set(): 
            return

        self.stop_event.set() 
        self.is_connected = False 
        
        self._close_socket() 

        if self.receive_thread and self.receive_thread.is_alive():
            print("Đang chờ luồng nhận tin nhắn dừng...")
            self.receive_thread.join(timeout=0.5) 
            if self.receive_thread.is_alive():
                print("Cảnh báo: Luồng nhận tin nhắn không dừng kịp thời.")

        if self.master.winfo_exists():
            self.master.after(500, self.master.destroy)
        else:
            print("Cửa sổ Tkinter đã không còn tồn tại.") 

    def on_closing(self):
        if messagebox.askokcancel("Thoát", "Bạn có chắc muốn thoát ứng dụng chat?"):
            self.stop_event.set() 
            
            current_socket = self.client_socket 
            if current_socket and self.is_connected:
                try:
                    current_socket.send(b"/quit") 
                    time.sleep(0.1) 
                except Exception as e:
                    print(f"Lỗi khi gửi lệnh /quit cho server: {e}")
            
            self._close_socket() 
            
            if self.receive_thread and self.receive_thread.is_alive():
                self.receive_thread.join(timeout=0.5)
            if self.connect_thread and self.connect_thread.is_alive():
                self.connect_thread.join(timeout=0.5)

            if self.master.winfo_exists():
                self.master.destroy() 
            else:
                print("Cửa sổ Tkinter đã không còn tồn tại khi on_closing.") 
        else:
            pass 

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()