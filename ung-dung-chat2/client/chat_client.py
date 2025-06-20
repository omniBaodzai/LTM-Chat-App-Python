import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox, ttk
from datetime import datetime
import atexit
import sys
import signal

# Assuming HOST and PORT are defined elsewhere or for testing purposes:
HOST = '192.168.1.16'
PORT = 12345

class ChatClient(ttk.Frame):
    def __init__(self, master, username, chat_mode="public", room_id=None, target_username=None, return_to_main_callback=None, update_online_users_callback=None):
        super().__init__(master, padding="5 5 5 5")
        self.master = master
        
        self.username = username
        self.chat_mode = chat_mode
        self.room_id = room_id
        self.target_username = target_username
        self.online_users = [] 
        self.return_to_main_callback = return_to_main_callback
        self.update_online_users_callback = update_online_users_callback
        
        self.running = True
        self.manually_closed = False
        self.socket_closed = False 

        self.room_name = ""
        self.room_creator = ""
        self.room_creation_date = ""
        
        self.user_list_visible = False 

        if self.chat_mode == "public":
            if not self.room_id:
                messagebox.showerror("Lỗi", "Thiếu mã phòng. Không thể mở phòng chat.")
                if self.return_to_main_callback:
                    self.master.after(0, self.return_to_main_callback)
                return

            self.room_id = self.room_id.strip()

        elif self.chat_mode == "private":
            pass

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((HOST, PORT))
            if self.chat_mode == "public":
                self.client.send(f"PUBLIC_CONNECT|{self.room_id}|{self.username}".encode())
            elif self.chat_mode == "private":
                self.client.send(f"PRIVATE_CONNECT|{self.username}".encode())
            print(f"Client connected to {HOST}:{PORT} with username {self.username} in {self.chat_mode} mode.") 
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể kết nối đến server.\n{e}")
            print(f"Connection error: {e}") 
            if self.return_to_main_callback:
                self.master.after(0, self.return_to_main_callback)
            return

        self.create_widgets()
        threading.Thread(target=self.receive_messages, daemon=True).start()

        if self.chat_mode == "public":
            self.request_online_users_for_public_room()
        elif self.chat_mode == "private":
            self.request_online_users()
            if self.target_username:
                self.request_private_message_history(self.target_username)

        atexit.register(self.exit_gracefully)
        signal.signal(signal.SIGINT, self.signal_handler)

    def create_widgets(self):
        ttk.Style().theme_use('clam') 

        s = ttk.Style()
        s.configure('Toggle.TButton', 
                            font=('Segoe UI Symbol', 12, 'bold'), 
                            background='#4CAF50', 
                            foreground='white',  
                            relief='flat',        
                            borderwidth=0,        
                            padding=(5, 0))      
        s.map('Toggle.TButton',
              background=[('active', '#66BB6A')], 
              foreground=[('active', 'white')])

        s.configure('Danger.TButton',
                            font=('Segoe UI', 10, 'bold'),
                            background='#FF6347', # Tomato
                            foreground='white',
                            relief='flat',
                            borderwidth=0,
                            padding=(5, 5))
        s.map('Danger.TButton',
              background=[('active', '#FF7F50'), ('disabled', '#D3D3D3')],
              foreground=[('disabled', '#A9A9A9')])


        content_frame = ttk.Frame(self, padding="5 5 5 5")
        content_frame.pack(fill=tk.BOTH, expand=True)

        self.main_pane = ttk.PanedWindow(content_frame, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        chat_frame = ttk.Frame(self.main_pane) 
        self.main_pane.add(chat_frame, weight=3)

        self.chat_box = scrolledtext.ScrolledText(chat_frame, state='disabled', wrap=tk.WORD, 
                                                     font=('Segoe UI', 10),
                                                     relief=tk.FLAT, borderwidth=1)
        self.chat_box.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(pady=(0, 5), fill=tk.X)

        self.entry_field = ttk.Entry(input_frame, font=('Segoe UI', 10))
        self.entry_field.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        self.entry_field.bind("<Return>", self.send_message)

        self.send_button = ttk.Button(input_frame, text="Gửi", width=10, command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=(0, 5))

        self.users_info_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.users_info_frame, weight=1)

        self.avatar_canvas = tk.Canvas(self.users_info_frame, width=80, height=80, bg="#F0F0F0", highlightthickness=0) 
        self.avatar_canvas.create_oval(10, 10, 70, 70, fill="#ADD8E6", outline="#ADD8C6")
        self.avatar_canvas.pack(pady=(10, 15))

        # --- Logic để hiển thị tên người dùng hoặc thông tin phòng ---
        if self.chat_mode == "public":
            self.room_name_label_dynamic = ttk.Label(self.users_info_frame, text="", font=("Arial", 9, "bold"))
            self.room_name_label_dynamic.pack(pady=(5, 5))

            date_frame = ttk.Frame(self.users_info_frame)
            date_frame.pack(pady=(5, 0), anchor=tk.W, padx=15)

            self.room_creation_label_static = ttk.Label(date_frame, text="Ngày tạo:", font=("Arial", 9))
            self.room_creation_label_static.pack(side=tk.LEFT)
            self.room_creation_label_dynamic = ttk.Label(date_frame, text="", font=("Arial", 9, "bold"))
            self.room_creation_label_dynamic.pack(side=tk.LEFT, padx=(5,0))

            creator_frame = ttk.Frame(self.users_info_frame)
            creator_frame.pack(pady=(5, 10), anchor=tk.W, padx=15)

            self.room_creator_label_static = ttk.Label(creator_frame, text="Người tạo:", font=("Arial", 9))
            self.room_creator_label_static.pack(side=tk.LEFT)
            self.room_creator_label_dynamic = ttk.Label(creator_frame, text="", font=("Arial", 9, "bold"))
            self.room_creator_label_dynamic.pack(side=tk.LEFT, padx=(5,0))
            
            # --- Khung chứa số người dùng online và nút toggle (chỉ cho public) ---
            self.online_users_count_frame = ttk.Frame(self.users_info_frame)
            self.online_users_count_frame.pack(pady=(5, 5), anchor=tk.W, padx=15)
            
            self.online_users_count_label = ttk.Label(self.online_users_count_frame, text="Người dùng onl: 0", font=("Arial", 10, "bold"))
            self.online_users_count_label.pack(side=tk.LEFT)
            
            self.toggle_users_button = ttk.Button(self.online_users_count_frame, text="▼", 
                                                     command=self.toggle_online_users_inline,
                                                     style='Toggle.TButton',
                                                     width=3) 
            self.toggle_users_button.pack(side=tk.LEFT, padx=(5,0))
            # -----------------------------------------------------------------------

            # Create online_users_buttons_frame only for public chat
            self.online_users_buttons_frame = ttk.Frame(self.users_info_frame, relief='solid', borderwidth=1)

            # Add Delete Room Button (for public chat only)
            self.delete_room_button = ttk.Button(self.users_info_frame, text="Xóa phòng", 
                                                     command=self.delete_room,
                                                     style='Danger.TButton',
                                                     state=tk.DISABLED) # Initially disabled
            self.delete_room_button.pack(pady=(10, 5), padx=15, fill=tk.X)


        elif self.chat_mode == "private":
            # Chỉ hiển thị tên người dùng đích (target_username) và trạng thái
            self.target_username_label = ttk.Label(self.users_info_frame, text=self.target_username, font=("Arial", 12, "bold"))
            self.target_username_label.pack(pady=(5, 5))

            # Label để hiển thị trạng thái Online/Offline
            self.private_chat_status_label = ttk.Label(self.users_info_frame, text="Trạng thái: Đang kết nối...", font=("Arial", 9, "italic"), foreground="gray")
            self.private_chat_status_label.pack(pady=(0, 10))

            # Ẩn khung chứa số người dùng online và nút toggle trong chế độ private
            # Vì chúng ta không tạo self.online_users_count_frame trong chế độ private, 
            # không cần pack_forget() ở đây.
            pass # Không làm gì với online_users_count_frame ở đây

        # -----------------------------------------------------------------
        
    def toggle_online_users_inline(self):
        """Toggles the visibility of the inline user buttons frame."""
        # Logic này chỉ áp dụng cho chế độ Public chat, nơi chúng ta có thể muốn xem danh sách người dùng online
        if self.chat_mode == "public":
            if self.user_list_visible:
                self.online_users_buttons_frame.pack_forget()
                self.toggle_users_button.config(text="▼") 
            else:
                self.update_user_buttons_content() 
                self.online_users_buttons_frame.pack(padx=15, pady=(0, 5), fill=tk.BOTH, expand=True)
                self.toggle_users_button.config(text="▲") 
            self.user_list_visible = not self.user_list_visible
        else:
            # Trong chế độ chat riêng, nút này có thể không cần thiết, hoặc có chức năng khác
            # Ví dụ: bạn có thể muốn nút này hiển thị danh sách tất cả người dùng online để chuyển đổi chat
            # Nhưng theo yêu cầu, chúng ta đang loại bỏ nó.
            pass


    def update_user_buttons_content(self):
        """Updates the content of the inline user buttons frame."""
        # Logic này vẫn được giữ để cập nhật danh sách người dùng online
        # (ngay cả trong chat riêng nếu bạn muốn dùng nút "v" để xem ai đang online)
        # nhưng chỉ hiển thị khi `self.user_list_visible` là True.
        for widget in self.online_users_buttons_frame.winfo_children():
            widget.destroy()

        s = ttk.Style()
        s.configure('User.TButton', 
                            font=('Segoe UI', 10),
                            background='#E0E0E0', 
                            foreground='black',  
                            relief='flat',        
                            borderwidth=1,
                            bordercolor='#C0C0C0', 
                            padding=(5, 3))      
        s.map('User.TButton',
              background=[('active', '#C5E1A5'), 
                          ('pressed', '#9CCC65')], 
              foreground=[('active', 'black')])

        for user in sorted(self.online_users, key=lambda x: (x != self.username, x)): 
            user_button = ttk.Button(self.online_users_buttons_frame, text=user, 
                                         command=lambda u=user: self.on_user_selected_button(u),
                                         style='User.TButton') 
            user_button.pack(fill=tk.X, pady=1) 
        print(f"Updated user buttons with: {self.online_users}") 

    def on_user_selected_button(self, selected_user):
        """Handles user selection from the custom buttons."""
        
        if selected_user == self.username:
            messagebox.showinfo("Thông báo", "Bạn không thể chat riêng với chính mình.")
            return

        print(f"Selected user for chat: {selected_user}") 

        if self.chat_mode == "public":
            # Nếu đang ở public chat và chọn người để chat riêng, thì chuyển sang private chat
            self.skip_on_closing = True
            self.running = False
            self.manually_closed = True
            self.safe_disconnect()
            
            if self.return_to_main_callback:
                self.master.after(0, self.return_to_main_callback)
                if hasattr(self.master, 'app_controller'):
                    self.master.after(100, lambda: self.master.app_controller.start_chat(chat_mode="private", target_username=selected_user))
                    
        elif self.chat_mode == "private":
            # Nếu đang ở private chat, và chọn người khác để chat riêng, thì chuyển private chat đó
            if self.target_username != selected_user: # Chỉ cập nhật nếu người dùng khác được chọn
                self.target_username = selected_user
                if hasattr(self.master, 'app_controller'):
                    self.master.app_controller.title(f"Chat Riêng với: {self.target_username} - Người dùng: {self.username}")
                
                self.chat_box.config(state='normal')
                self.chat_box.delete('1.0', tk.END)
                self.chat_box.config(state='disabled')
                self.request_private_message_history(self.target_username)
                
                self.toggle_online_users_inline() # Ẩn danh sách sau khi chọn (nếu nó đang hiện)
                self.update_private_chat_status() # Cập nhật trạng thái của người dùng mới chọn

    def request_private_message_history(self, target_user):
        try:
            self.client.send(f"REQUEST_PRIVATE_HISTORY|{target_user}".encode())
            print(f"Requested private history for {target_user}") 
        except Exception as e:
            print(f"Error requesting private message history: {e}")

    def request_online_users(self):
        try:
            self.client.send("/get_online_users".encode())
            print("Requested all online users.") 
        except Exception as e:
            print(f"Error requesting all online users: {e}")

    def request_online_users_for_public_room(self):
        try:
            self.client.send(f"GET_ROOM_INFO_AND_USERS|{self.room_id}".encode())
            print(f"Requested room info and users for room ID: {self.room_id}") 
        except Exception as e:
            print(f"Error requesting online users and room info for public room: {e}")

    def send_message(self, event=None):
        msg = self.entry_field.get()
        if not msg:
            return
        try:
            if self.chat_mode == "public":
                self.client.send(f"PUBLIC_MSG|{self.room_id}|{msg}".encode())
                print(f"Sent public message to room {self.room_id}: {msg}") 
            elif self.chat_mode == "private":
                if not self.target_username:
                    messagebox.showwarning("Lỗi", "Vui lòng chọn người dùng để chat riêng.")
                    return
                self.client.send(f"PRIVATE_MSG|{self.target_username}|{msg}".encode())
                print(f"Sent private message to {self.target_username}: {msg}") 
            self.entry_field.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể gửi tin nhắn: {e}")
            print(f"Error sending message: {e}") 
            self.on_connection_lost()

    def receive_messages(self):
        buffer = ""
        while self.running:
            try:
                data = self.client.recv(2048).decode()
                if not data:
                    print("Server closed connection.") 
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self.process_incoming_data(line.strip())
            except Exception as e:
                if self.running:
                    print(f"Error in receive_messages loop: {e}") 
                break
        if self.running and self.master.winfo_exists():
            self.master.after(0, self.on_connection_lost)

    def on_connection_lost(self):
        if not self.master.winfo_exists():
            print("Master window does not exist, skipping on_connection_lost actions.") 
            return
        if not hasattr(self.master, 'app_controller') or not self.master.app_controller.winfo_exists():
            print("App controller does not exist, skipping on_connection_lost actions.") 
            return

        if not self.manually_closed:
            messagebox.showerror("Lỗi", "Mất kết nối đến server.")
            print("Connection lost due to unexpected error.") 
        else:
            print("Connection lost, but it was a manual/graceful closure.") 
        
        self.safe_disconnect()
        if self.return_to_main_callback:
            self.master.after(0, self.return_to_main_callback)

    def process_incoming_data(self, data):
        print(f"Received raw data: {data}") 
        if data.startswith("ONLINE_USERS|"):
            users_str = data[len("ONLINE_USERS|"):]
            received_online_users = [u for u in users_str.split(',') if u]
            
            print(f"Parsed ONLINE_USERS: {received_online_users}, Count: {len(received_online_users)}") 
            
            self.online_users = received_online_users
            
            if self.chat_mode == "public":
                self.online_users_count_label.config(text=f"Người dùng Online: {len(received_online_users)}")
                if self.user_list_visible:
                    self.update_user_buttons_content() 
            elif self.chat_mode == "private":
                self.update_private_chat_status() # Cập nhật trạng thái của người dùng đang chat riêng

            if self.update_online_users_callback:
                self.update_online_users_callback(received_online_users)

        elif data.startswith("ROOM_INFO_AND_USERS|"):
            parts = data.split('|', 4)
            if len(parts) == 5:
                _, room_name, creator, creation_date, users_str = parts
                self.room_name = room_name
                self.room_creator = creator
                self.room_creation_date = creation_date
                self.display_room_info()
                
                # Enable/Disable Delete Room button based on creator
                if self.chat_mode == "public" and self.username == self.room_creator:
                    self.delete_room_button.config(state=tk.NORMAL)
                else:
                    self.delete_room_button.config(state=tk.DISABLED)

                received_online_users = [u for u in users_str.split(',') if u]
                
                print(f"Parsed ROOM_INFO_AND_USERS: Room='{room_name}', Creator='{creator}', Date='{creation_date}', Users={received_online_users}, Count: {len(received_online_users)}")
                
                self.online_users = received_online_users
                # Cập nhật số lượng online users chỉ khi ở chế độ public
                if self.chat_mode == "public":
                    self.online_users_count_label.config(text=f"Người dùng onl: {len(received_online_users)}")
                
                if self.user_list_visible:
                    self.update_user_buttons_content() 
                
                if self.update_online_users_callback:
                    self.update_online_users_callback(received_online_users)
            else:
                print(f"Warning: Unexpected ROOM_INFO_AND_USERS format: {data}")

        elif data.startswith("PRIVATE_MSG_RECV|") or data.startswith("PUBLIC_MSG_RECV|"):
            parts = data.split('|', 4)
            if len(parts) == 5:
                _, sender, content, timestamp, _ = parts
                try:
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
                except ValueError:
                    pass
                is_private_msg_received = data.startswith("PRIVATE_MSG_RECV|")
                
                # NEW LOGIC: Only display private messages if in private chat mode and it's for the current target
                # or display public messages if in public chat mode.
                if (is_private_msg_received and self.chat_mode == "private" and 
                    (sender == self.target_username or sender == self.username)) or \
                   (not is_private_msg_received and self.chat_mode == "public"):
                    self.display_message(f"[{timestamp}] {sender}: {content}", align_right=(sender == self.username), is_private=is_private_msg_received)
                else:
                    print(f"Skipping display of message in current chat mode. Mode: {self.chat_mode}, Is Private: {is_private_msg_received}, Sender: {sender}, Target: {self.target_username}")
            else:
                self.display_message(data)

        elif data.startswith("SYSTEM_MSG_RECV|"):
            parts = data.split('|', 4)
            if len(parts) == 5:
                _, _, content, timestamp, _ = parts
                try:
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
                except ValueError:
                    pass
                self.display_message(f"[{timestamp}] {content}", is_system=True)
                # Check if the system message indicates room deletion
                if "đã bị người tạo xóa" in content and self.chat_mode == "public" and self.room_id in content:
                    messagebox.showinfo("Thông báo", f"Phòng chat '{self.room_id}' đã bị người tạo xóa. Bạn sẽ được đưa về màn hình chính.")
                    self.go_back_to_main()
                elif "đã được xóa thành công" in content and self.chat_mode == "public" and self.room_id in content and self.username == self.room_creator:
                    messagebox.showinfo("Thông báo", f"Phòng chat '{self.room_id}' của bạn đã được xóa thành công. Bạn sẽ được đưa về màn hình chính.")
                    self.go_back_to_main()

            else:
                self.display_message(data, is_system=True)

    def display_room_info(self):
        """Updates the room name, creation date, and creator labels."""
        if self.chat_mode == "public":
            self.room_name_label_dynamic.config(text=self.room_name)
            self.room_creation_label_dynamic.config(text=self.room_creation_date)
            self.room_creator_label_dynamic.config(text=self.room_creator)
            print(f"Displayed room info: Name='{self.room_name}', Creator='{self.room_creator}', Date='{self.room_creation_date}'") 

    def update_private_chat_status(self):
        """Cập nhật trạng thái Online/Offline của người dùng chat riêng."""
        if self.chat_mode == "private" and hasattr(self, 'private_chat_status_label') and self.target_username:
            if self.target_username in self.online_users:
                self.private_chat_status_label.config(text="Trạng thái: Online", foreground="green")
            else:
                self.private_chat_status_label.config(text="Trạng thái: Offline", foreground="red")
            print(f"Updated status for {self.target_username}: {self.private_chat_status_label['text']}") # Debug print


    def display_message(self, message, align_right=False, is_system=False, is_private=False):
        self.chat_box.config(state='normal')
        self.chat_box.tag_configure('right', justify='right', background='#DCF8C6', font=('Segoe UI', 10), 
                                         lmargin1=10, lmargin2=10, rmargin=10, wrap='word')
        self.chat_box.tag_configure('left', justify='left', background='#EAEAEA', font=('Segoe UI', 10), 
                                         lmargin1=10, lmargin2=10, rmargin=10, wrap='word')
        self.chat_box.tag_configure('center', justify='center', foreground='#616161', font=('Segoe UI', 9, 'italic'), 
                                         lmargin1=10, lmargin2=10, rmargin=10, wrap='word')
        self.chat_box.tag_configure('private_other', justify='left', background='#FFF3E0', font=('Segoe UI', 10), 
                                         lmargin1=10, lmargin2=10, rmargin=10, wrap='word')

        if is_private:
            tag = 'right' if align_right else 'private_other'
        elif align_right:
            tag = 'right'
        elif is_system:
            tag = 'center'
        else:
            tag = 'left'

        self.chat_box.insert(tk.END, message + '\n', tag)
        self.chat_box.yview(tk.END)
        self.chat_box.config(state='disabled')
        print(f"Displayed message: '{message}' with tag '{tag}'") 

    def go_back_to_main(self):
        self.skip_on_closing = True
        self.running = False
        self.manually_closed = True
        self.safe_disconnect()
        print("Go back to main triggered.") 

        if self.return_to_main_callback:
            self.master.after(0, self.return_to_main_callback)

    def exit_gracefully(self):
        if self.running:
            self.running = False
            self.manually_closed = True
            self.safe_disconnect()
            print("exit_gracefully triggered.") 

    def signal_handler(self, sig, frame):
        self.exit_gracefully()
        sys.exit(0)

    def safe_disconnect(self):
        """Closes the socket connection safely."""
        if not self.socket_closed:
            print("Attempting to safely disconnect socket...") 
            try:
                # Kiểm tra nếu socket còn đang hoạt động trước khi gửi
                if self.client.fileno() != -1: 
                    self.client.send("/quit".encode())
                    print("Sent /quit to server.") 
            except OSError as e: # Bắt lỗi cụ thể cho các vấn đề về socket (ví dụ: socket đã đóng)
                print(f"Warning: Could not send /quit (socket already closed or invalid): {e}")
            except Exception as e: # Bắt các lỗi khác
                print(f"Error sending /quit to server: {e}")
            
            try:
                # Kiểm tra lại trước khi shutdown/close
                if self.client.fileno() != -1: 
                    self.client.shutdown(socket.SHUT_RDWR)
                    print("Socket shutdown (SHUT_RDWR).") 
                self.client.close()
                self.socket_closed = True 
                print("Socket closed successfully.") 
            except OSError as e:
                print(f"Warning: Error during socket shutdown/close (likely already closed): {e}")
            except Exception as e:
                print(f"Error during socket shutdown/close: {e}") 

    def delete_room(self):
        """Gửi yêu cầu đến server để xóa phòng chat công khai hiện tại."""
        if self.chat_mode != "public" or not self.room_id:
            messagebox.showwarning("Cảnh báo", "Bạn chỉ có thể xóa phòng chat công khai.")
            return

        if self.username != self.room_creator:
            messagebox.showwarning("Cảnh báo", "Bạn không phải là người tạo phòng này. Bạn không thể xóa nó.")
            return

        confirm = messagebox.askyesno("Xác nhận xóa phòng", 
                                     f"Bạn có chắc chắn muốn xóa phòng '{self.room_id}' không?\n"
                                     "Tất cả lịch sử tin nhắn trong phòng này cũng sẽ bị xóa. Hành động này không thể hoàn tác.")
        if confirm:
            try:
                print(f"Attempting to send DELETE_ROOM command for room: {self.room_id}")
                self.client.send(f"DELETE_ROOM|{self.room_id}".encode())
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể gửi yêu cầu xóa phòng: {e}")
                print(f"Error sending delete room request: {e}")
                # If there's an error sending the request, assume connection might be lost
                # and call the connection lost handler.
                self.on_connection_lost()