import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox, ttk
from datetime import datetime
import atexit
import sys
import signal

HOST = '192.168.1.16'  # IP của máy chủ
PORT = 12345

class ChatClient:
    def __init__(self, master, username, chat_mode="public", room_id=None, target_username=None, return_to_main_callback=None):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.username = username
        self.chat_mode = chat_mode
        self.room_id = room_id
        self.target_username = target_username # For private chat
        self.online_users = [] # To store online users for private chat selection
        self.return_to_main_callback = return_to_main_callback
        self.private_chat_windows = {} # To keep track of open private chat windows

        if self.chat_mode == "public":
            if not self.room_id:
                self.room_id = simpledialog.askstring("Phòng Chat", "Nhập mã phòng:")
            if not self.room_id:
                messagebox.showwarning("Lỗi", "Bạn phải nhập mã phòng.")
                master.quit()
                return
            self.room_id = self.room_id.strip()
            self.master.title(f"Mã Chat Room: {self.room_id} - Username: {self.username}")
        elif self.chat_mode == "private":
            self.master.title(f"Chat Riêng với: {self.target_username if self.target_username else 'Chọn người dùng'} - Username: {self.username}")

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((HOST, PORT))
            # Send initial connection info based on chat mode
            if self.chat_mode == "public":
                self.client.send(f"PUBLIC_CONNECT|{self.room_id}|{self.username}".encode())
            elif self.chat_mode == "private":
                self.client.send(f"PRIVATE_CONNECT|{self.username}".encode())
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể kết nối đến server.\n{e}")
            master.quit()
            return

        self.create_widgets()
        threading.Thread(target=self.receive_messages, daemon=True).start()

        # Request initial data based on chat mode
        if self.chat_mode == "public":
            self.request_message_history() # Server sends history automatically for public rooms
            self.request_online_users_for_public_room() # Request online users for the public room
        elif self.chat_mode == "private":
            self.request_online_users() # Get all online users for the listbox in private chat
            if self.target_username:
                self.request_private_message_history(self.target_username) # If a target is pre-selected

        atexit.register(self.exit_gracefully)
        signal.signal(signal.SIGINT, self.signal_handler)

    def create_widgets(self):
        # Sử dụng PanedWindow để chia khung
        self.main_pane = tk.PanedWindow(self.master, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Khung chat chính
        chat_frame = tk.Frame(self.main_pane)
        self.main_pane.add(chat_frame, width=500) # Set initial width for chat frame

        self.chat_box = scrolledtext.ScrolledText(chat_frame, state='disabled', width=60, height=20)
        self.chat_box.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        input_frame = tk.Frame(chat_frame)
        input_frame.pack(pady=(0, 5), fill=tk.X)

        self.entry_field = tk.Entry(input_frame, width=40) # Keep width consistent
        self.entry_field.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        self.entry_field.bind("<Return>", self.send_message)

        self.send_button = tk.Button(input_frame, text="Gửi", width=10, command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=(0, 5))

        # Changed the command for the exit_button to go_back_to_main
        self.exit_button = tk.Button(input_frame, text="Thoát", width=10, command=self.go_back_to_main)
        self.exit_button.pack(side=tk.LEFT)

        # Khung danh sách người dùng online (luôn hiển thị cho cả public và private)
        self.users_frame = tk.Frame(self.main_pane)
        self.main_pane.add(self.users_frame, width=150) # Set initial width for users frame

        tk.Label(self.users_frame, text="Người dùng Online", font=("Arial", 10, "bold")).pack(pady=5)
        
        self.user_listbox = tk.Listbox(self.users_frame, height=15, width=20, exportselection=False)
        self.user_listbox.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        self.user_listbox.bind('<<ListboxSelect>>', self.on_user_selected)
        
        # Add a scrollbar to the listbox
        scrollbar = tk.Scrollbar(self.user_listbox, orient="vertical", command=self.user_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.user_listbox.config(yscrollcommand=scrollbar.set)
        
        # Nút quay lại menu chính
        self.back_button = tk.Button(self.master, text="Quay lại Menu", command=self.go_back_to_main)
        self.back_button.pack(pady=(5, 10))

    def on_user_selected(self, event):
        selection = self.user_listbox.curselection()
        if selection:
            index = selection[0]
            selected_user = self.user_listbox.get(index)
            if selected_user and selected_user != self.username:
                if self.chat_mode == "public":
                    # In public chat, selecting a user opens a new private chat window
                    self.start_private_chat_from_public(selected_user)
                elif self.chat_mode == "private":
                    # In private chat, selecting a user changes the current private conversation
                    self.target_username = selected_user
                    self.master.title(f"Chat Riêng với: {self.target_username} - Username: {self.username}")
                    # Clear chatbox for new private conversation context
                    self.chat_box.config(state='normal')
                    self.chat_box.delete('1.0', tk.END)
                    self.chat_box.config(state='disabled')
                    self.request_private_message_history(self.target_username) # Request history here
            else:
                # If the user selects themselves or nothing
                if self.chat_mode == "private":
                    self.target_username = None
                    self.master.title(f"Chat Riêng với: Chọn người dùng - Username: {self.username}")
                    self.chat_box.config(state='normal')
                    self.chat_box.delete('1.0', tk.END)
                    self.chat_box.config(state='disabled')

    def start_private_chat_from_public(self, target_user):
        if target_user in self.private_chat_windows and self.private_chat_windows[target_user].winfo_exists():
            self.private_chat_windows[target_user].lift() # Bring existing window to front
        else:
            private_root = tk.Toplevel(self.master) # Use Toplevel for new window
            private_client = ChatClient(private_root, self.username, chat_mode="private", target_username=target_user, return_to_main_callback=self.master.deiconify)
            self.private_chat_windows[target_user] = private_root # Store reference to the Toplevel window

    def request_private_message_history(self, target_user):
        try:
            self.client.send(f"REQUEST_PRIVATE_HISTORY|{target_user}".encode())
        except Exception as e:
            print(f"Error requesting private message history: {e}")

    def request_online_users(self):
        # This is for fetching all online users for private chat selection
        try:
            self.client.send("/get_online_users".encode())
        except Exception as e:
            print(f"Error requesting all online users: {e}")
    
    def request_online_users_for_public_room(self):
        # This is for fetching online users specifically for the current public room
        try:
            self.client.send(f"GET_ROOM_ONLINE_USERS|{self.room_id}".encode())
        except Exception as e:
            print(f"Error requesting online users for public room: {e}")

    def request_message_history(self):
        try:
            # Server will send history automatically for public rooms
            pass
        except Exception as e:
            print(f"Error requesting message history: {e}")

    def send_message(self, event=None):
        msg = self.entry_field.get()
        if not msg:
            return

        try:
            if self.chat_mode == "public":
                self.client.send(f"PUBLIC_MSG|{self.room_id}|{msg}".encode()) # Include room_id in public message
            elif self.chat_mode == "private":
                if not self.target_username:
                    messagebox.showwarning("Lỗi", "Vui lòng chọn người dùng để chat riêng.")
                    return
                self.client.send(f"PRIVATE_MSG|{self.target_username}|{msg}".encode())
            self.entry_field.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể gửi tin nhắn: {e}")
            self.master.quit()

    def receive_messages(self):
        buffer = ""
        while True:
            try:
                data = self.client.recv(2048).decode()
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self.process_incoming_data(line.strip())
            except Exception as e:
                print(f"Error receiving messages: {e}")
                break
        self.master.after(0, self.on_connection_lost) # Schedule closing on main thread


    def on_connection_lost(self):
        if not self.master.winfo_exists(): # Check if window is still open
            return
        messagebox.showerror("Lỗi", "Mất kết nối đến server.")
        self.on_closing() # Call on_closing to ensure proper cleanup
        if self.return_to_main_callback:
            self.return_to_main_callback()


    def process_incoming_data(self, data):
        # Always process ONLINE_USERS for any chat mode
        if data.startswith("ONLINE_USERS|"):
            users_str = data[len("ONLINE_USERS|"):]
            self.online_users = [u for u in users_str.split(',') if u and u != self.username]
            
            if hasattr(self, 'user_listbox') and self.user_listbox:
                self.user_listbox.delete(0, tk.END)
                for user in self.online_users:
                    self.user_listbox.insert(tk.END, user)
                
                # Cố gắng chọn lại người dùng hiện tại nếu họ vẫn online (chỉ trong chế độ private)
                if self.chat_mode == "private" and self.target_username and self.target_username in self.online_users:
                    try:
                        idx = self.online_users.index(self.target_username)
                        self.user_listbox.selection_set(idx)
                        self.user_listbox.see(idx) # Scroll to the selected item
                    except ValueError:
                        pass # User not found in new list

        elif data.startswith("PUBLIC_MSG_RECV|"):
            parts = data.split('|', 4)
            if len(parts) == 5:
                protocol, sender, content, timestamp, original_msg_for_display = parts
                self.display_message(f"[{timestamp}] {sender}: {content}", align_right=(sender == self.username))
            else:
                self.display_message(data)

        elif data.startswith("PRIVATE_MSG_RECV|"):
            parts = data.split('|', 4)
            if len(parts) == 5:
                protocol, sender, content, timestamp, original_msg_for_display = parts
                # Only display if it's for the current private chat or from current user
                if self.chat_mode == "private" and (sender == self.username or sender == self.target_username):
                    if sender == self.username:
                        self.display_message(f"[{timestamp}] Bạn (tới {self.target_username if self.target_username else 'người khác'}): {content}", align_right=True, is_private=True)
                    else:
                        self.display_message(f"[{timestamp}] {sender} (riêng): {content}", align_right=False, is_private=True)
                elif self.chat_mode == "public":
                    # In public chat, just notify of incoming private message
                    self.display_message(f"[{timestamp}] Tin riêng mới từ {sender}: {content}", is_system=True)
                    # Optionally, you could trigger opening a private chat window here
                    # self.start_private_chat_from_public(sender) # This would open a window every time
                else:
                    # If private message not for current target or current mode
                    self.display_message(f"[{timestamp}] Tin riêng từ {sender}: {content}", is_system=True)
            else:
                self.display_message(data)
        
        elif data.startswith("SYSTEM_MSG_RECV|"):
            parts = data.split('|', 4)
            if len(parts) == 5:
                protocol, sender, content, timestamp, original_msg_for_display = parts
                self.display_message(f"[{timestamp}] {content}", is_system=True)
            else:
                self.display_message(data, is_system=True)

        # Backward compatibility for old simple messages (should ideally not be used with new protocol)
        elif data.startswith("system|"):
            self.process_message(data)
        else:
            self.process_message(data)

    def process_message(self, message):
        parts = message.strip().split('|')
        if len(parts) == 3:
            sender, content, timestamp = parts
            if sender == "system":
                self.display_message(f"[{timestamp}] {content}", is_system=True)
            elif sender == self.username:
                self.display_message(f"[{timestamp}] Bạn: {content}", align_right=True)
            else:
                self.display_message(f"[{timestamp}] {sender}: {content}", align_right=False)
        else:
            self.display_message(message)

    def display_message(self, message, align_right=False, is_system=False, is_private=False):
        self.chat_box.config(state='normal')
        self.chat_box.tag_configure('right', justify='right', background='#DCF8C6', font=('Arial', 10))
        self.chat_box.tag_configure('left', justify='left', background='#E0E0E0', font=('Arial', 10))
        self.chat_box.tag_configure('center', justify='center', foreground='gray', font=('Arial', 9, 'italic'))
        self.chat_box.tag_configure('private', justify='left', background='#FFEBEE', font=('Arial', 10, 'bold'))

        if is_private:
            self.chat_box.insert(tk.END, message + '\n', 'private')
        elif align_right:
            self.chat_box.insert(tk.END, message + '\n', 'right')
        elif is_system:
            self.chat_box.insert(tk.END, message + '\n', 'center')
        else:
            self.chat_box.insert(tk.END, message + '\n', 'left')

        self.chat_box.yview(tk.END)
        self.chat_box.config(state='disabled')

    def go_back_to_main(self):
        self.on_closing()
        if self.return_to_main_callback:
            self.master.after(100, self.return_to_main_callback)


    def on_closing(self):
        try:
            self.client.send("/quit".encode())
        except:
            pass
        try:
            self.client.close()
        except:
            pass
        # Only destroy the current window if it hasn't been destroyed by other means
        if self.master.winfo_exists():
            self.master.destroy()

    def exit_gracefully(self):
        try:
            self.client.send("/quit".encode())
        except:
            pass
        try:
            self.client.close()
        except:
            pass

    def signal_handler(self, sig, frame):
        self.exit_gracefully()
        sys.exit(0)