import tkinter as tk
from tkinter import messagebox, PanedWindow, ttk, simpledialog
from client.chat_client import ChatClient
from client.config import get_db_connection
import hashlib
import mysql.connector

def hash_password(password):
    """Hashes a given password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

class AppController(tk.Tk):
    """
    Main application controller managing screen transitions and the overall window.
    """
    def __init__(self):
        super().__init__()
        self.title("Ứng dụng Chat")
        self.geometry("1000x600")
        self.resizable(True, True)

        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TButton', font=('Arial', 10), padding=6)
        style.map('TButton',
                  background=[('active', '#e0e0e0'), ('!active', 'SystemButtonFace')],
                  foreground=[('active', 'black'), ('!active', 'black')])
        style.configure('TEntry', font=('Arial', 10), padding=3)
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TPanedwindow', background='#f0f0f0')

        self.current_screen = None
        self.username = None
        self.user_id = None # Store the user ID here

        self.chat_container_frame = None
        self.main_panel = None
        self.chat_panel = None

        self.switch_screen(StartScreen)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Handles the window closing event, prompting the user for confirmation."""
        if self.chat_panel and self.chat_panel.current_chat_client:
            if getattr(self.chat_panel.current_chat_client, "skip_on_closing", False):
                self.destroy()
                return

            result = messagebox.askyesno("Xác nhận", "Bạn có muốn thoát ứng dụng không?")
            if result:
                self.chat_panel.current_chat_client.running = False
                self.chat_panel.current_chat_client.manually_closed = True
                self.chat_panel.current_chat_client.safe_disconnect()
                self.destroy()
        else:
            result = messagebox.askyesno("Xác nhận", "Bạn có muốn thoát ứng dụng không?")
            if result:
                self.destroy()

    def switch_screen(self, screen_class, **kwargs):
        """
        Switches between different application screens.
        Handles proper cleanup when switching away from MainPanel.
        """
        # If we are switching from MainPanel (or any screen that might have a chat client)
        # to another screen, ensure the existing chat client is safely disconnected.
        if self.chat_panel and self.chat_panel.current_chat_client:
            # We don't want to show a confirmation dialog when just switching screens internally.
            self.chat_panel.current_chat_client.running = False
            self.chat_panel.current_chat_client.manually_closed = True
            self.chat_panel.current_chat_client.safe_disconnect()
            self.chat_panel.clear_chat() # This also destroys the current_chat_client frame

        if self.current_screen:
            self.current_screen.pack_forget()
            self.current_screen.destroy()
            self.current_screen = None

        if self.chat_container_frame:
            self.chat_container_frame.pack_forget()
            self.chat_container_frame.destroy()
            self.chat_container_frame = None
            self.chat_panel = None
            self.main_panel = None

        if screen_class == MainPanel:
            self.username = kwargs.get('username')
            self.user_id = kwargs.get('user_id') # Get user_id from kwargs
            self.setup_chat_interface()
        else:
            self.current_screen = screen_class(self, self, **kwargs)
            self.current_screen.pack(fill="both", expand=True)
            self.title("Ứng dụng Chat") # Reset title when going back to non-chat screens


    def setup_chat_interface(self):
        """Sets up the main chat interface using a ttk.PanedWindow."""
        self.chat_container_frame = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.chat_container_frame.pack(fill=tk.BOTH, expand=True)

        # Pass user_id to MainPanel
        self.main_panel = MainPanel(self.chat_container_frame, self, 
                                     username=self.username, user_id=self.user_id) 
        self.chat_panel = ChatPanel(self.chat_container_frame, self)

        self.chat_container_frame.add(self.main_panel, weight=1)
        self.chat_container_frame.add(self.chat_panel, weight=3)

    def start_chat(self, chat_mode, room_id=None, target_username=None):
        """
        Called from MainPanel when a user selects a room/user to chat with.
        Instructs ChatPanel to load a new ChatClient.
        """
        if self.chat_panel:
            self.chat_panel.load_chat_client(self.username, chat_mode, room_id, target_username)
        else:
            messagebox.showerror("Lỗi", "Chat panel chưa sẵn sàng.")

    def clear_chat_panel(self):
        """
        Called from ChatClient when the user presses "Back to Main Menu".
        Clears the current ChatClient from ChatPanel and shows the welcome label.
        """
        # This method is called when the user clicks "Back to Main Menu" within ChatClient
        # It should only clear the chat panel and not switch the main screen.
        if self.chat_panel:
            self.chat_panel.clear_chat()
            # The title will be reset by switch_screen if the screen changes,
            # or it will remain the main chat title if not leaving the chat interface.


class StartScreen(ttk.Frame):
    """Initial screen with a welcome message and a start button."""
    def __init__(self, master, controller):
        super().__init__(master, padding="20 20 20 20")
        self.controller = controller
        
        ttk.Label(self, text="Chào mừng đến với ứng dụng Chat", font=("Arial", 20, "bold")).pack(pady=40)
        ttk.Button(self, text="Bắt đầu", width=20, command=lambda: controller.switch_screen(LoginScreen)).pack(pady=10)

class LoginScreen(ttk.Frame):
    """Login screen for existing users."""
    def __init__(self, master, controller):
        super().__init__(master, padding="20 20 20 20")
        self.controller = controller
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        ttk.Label(self, text="Đăng Nhập", font=("Arial", 18, "bold")).pack(pady=30)
        
        form = ttk.Frame(self, padding="10 10 10 10")
        form.pack()

        ttk.Label(form, text="Tên người dùng:").grid(row=0, column=0, sticky='e', pady=5, padx=5)
        ttk.Entry(form, textvariable=self.username_var, width=30).grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(form, text="Mật khẩu:").grid(row=1, column=0, sticky='e', pady=5, padx=5)
        ttk.Entry(form, textvariable=self.password_var, show='*', width=30).grid(row=1, column=1, pady=5, padx=5)

        ttk.Button(self, text="Đăng nhập", width=15, command=self.login).pack(pady=20)
        
        style = ttk.Style()
        style.configure('Link.TButton', foreground='blue', background='SystemButtonFace', relief='flat', font=('Arial', 9, 'underline'))
        style.map('Link.TButton', background=[('active', 'SystemButtonFace')]) 
        
        ttk.Button(self, text="Chưa có tài khoản? Đăng ký", command=lambda: controller.switch_screen(RegisterScreen), style='Link.TButton').pack()

    def login(self):
        """Attempts to log in the user with provided credentials."""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        hashed = hash_password(password)

        if not username or not password:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng điền đầy đủ.")
            return

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Fetch both id and username
            cursor.execute("SELECT id, username FROM users WHERE username = %s AND password = %s", (username, hashed))
            user = cursor.fetchone()
            
            if user:
                user_id = user[0] # Get the user ID
                username_from_db = user[1] # Get the username from DB (ensure case consistency if needed)
                self.controller.username = username_from_db # Set username
                self.controller.user_id = user_id # Set user ID
                # Pass both username and user_id to MainPanel
                self.controller.switch_screen(MainPanel, username=username_from_db, user_id=user_id)
            else:
                messagebox.showerror("Lỗi", "Sai tài khoản hoặc mật khẩu.")
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", str(e))
        finally:
            if conn:
                conn.close()

class RegisterScreen(ttk.Frame):
    """Registration screen for new users."""
    def __init__(self, master, controller):
        super().__init__(master, padding="20 20 20 20")
        self.controller = controller
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.email_var = tk.StringVar()

        ttk.Label(self, text="Đăng Ký", font=("Arial", 18, "bold")).pack(pady=30)
        
        form = ttk.Frame(self, padding="10 10 10 10")
        form.pack()

        ttk.Label(form, text="Tên người dùng:").grid(row=0, column=0, sticky='e', pady=5, padx=5)
        ttk.Entry(form, textvariable=self.username_var, width=30).grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(form, text="Email:").grid(row=1, column=0, sticky='e', pady=5, padx=5)
        ttk.Entry(form, textvariable=self.email_var, width=30).grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(form, text="Mật khẩu:").grid(row=2, column=0, sticky='e', pady=5, padx=5)
        ttk.Entry(form, textvariable=self.password_var, show='*', width=30).grid(row=2, column=1, pady=5, padx=5)

        ttk.Button(self, text="Đăng ký", width=15, command=self.register).pack(pady=20)
        
        style = ttk.Style()
        style.configure('Link.TButton', foreground='blue', background='SystemButtonFace', relief='flat', font=('Arial', 9, 'underline'))
        style.map('Link.TButton', background=[('active', 'SystemButtonFace')])

        ttk.Button(self, text="Đã có tài khoản? Đăng nhập", command=lambda: controller.switch_screen(LoginScreen), style='Link.TButton').pack()

    def register(self):
        """Attempts to register a new user."""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        email = self.email_var.get().strip()

        if not username or not password or not email:
            messagebox.showwarning("Thiếu thông tin", "Điền đầy đủ tất cả các trường.")
            return

        hashed = hash_password(password)
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, hashed, email))
            conn.commit()
            messagebox.showinfo("Thành công", "Đăng ký thành công. Vui lòng đăng nhập.")
            self.controller.switch_screen(LoginScreen)
        except mysql.connector.IntegrityError as err:
            if "username" in str(err):
                messagebox.showerror("Lỗi", "Tên người dùng đã tồn tại.")
            elif "email" in str(err):
                messagebox.showerror("Lỗi", "Email đã được sử dụng.")
            else:
                messagebox.showerror("Lỗi", str(err))
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", str(e))
        finally:
            if conn:
                conn.close()

class MainPanel(ttk.Frame):
    """
    The left panel displaying public chat rooms and all registered users for private chat.
    """
    PRIVATE_CHAT_PREFIX = "Chat riêng với: "

    def __init__(self, master, app_controller, username, user_id):
        super().__init__(master, padding="10 10 10 10")
        self.app_controller = app_controller
        self.username = username
        self.user_id = user_id

        ttk.Label(self, text=f"Xin chào, {username}!", font=("Arial", 14, "bold")).pack(pady=15)

        # Public Rooms Section
        public_rooms_section_frame = ttk.Frame(self)
        public_rooms_section_frame.pack(pady=(10, 5), fill=tk.X)

        ttk.Label(public_rooms_section_frame, text="Phòng Chat Công Khai:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, anchor='w')
        
        ttk.Button(public_rooms_section_frame, text="Tạo Phòng Mới", command=self.create_new_room).pack(side=tk.RIGHT, padx=(5,0))

        self.public_rooms_frame = ttk.Frame(self, padding="5 5 5 5")
        self.public_rooms_frame.pack(padx=5, pady=5, fill=tk.X)
        
        # Private Users Section (now also a simple ttk.Frame, no canvas/scrollbar)
        private_users_section_label_frame = ttk.Frame(self) 
        private_users_section_label_frame.pack(pady=(10, 5), fill=tk.X)
        ttk.Label(private_users_section_label_frame, text="Tất cả Người dùng (Chat Riêng):", font=("Arial", 10, "bold")).pack(side=tk.LEFT, anchor='w')

        # This frame will hold the user buttons. It's now a simple ttk.Frame.
        self.private_users_frame = ttk.Frame(self, padding="5 5 5 5") 
        # Make sure this frame also expands to fill vertical space if needed
        self.private_users_frame.pack(padx=5, pady=5, fill=tk.BOTH, expand=True) 

        # Removed the Exit button here
        # ttk.Button(self, text="Thoát", width=25, command=self.exit_application).pack(pady=10) # New Exit button
        
        ttk.Button(self, text="Đăng xuất", width=25,
                   command=self.logout).pack(pady=10) # Adjusted pady back to 10 for original spacing

        self.populate_initial_options() # Populates public rooms
        self.update_all_registered_users_list() # Populates all users for private chat

    def create_new_room(self):
        """Prompts the user for a new room name and attempts to create it in the database."""
        room_name = simpledialog.askstring("Tạo Phòng Mới", "Nhập tên phòng mới:", parent=self)
        if room_name:
            room_name = room_name.strip()
            if not room_name:
                messagebox.showwarning("Cảnh báo", "Tên phòng không được để trống.")
                return

            # Ensure user_id is available before creating a room
            if self.user_id is None:
                messagebox.showerror("Lỗi", "Không thể tạo phòng. Không tìm thấy ID người dùng. Vui lòng thử đăng nhập lại.")
                return

            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                # Pass self.user_id as the created_by value
                cursor.execute("INSERT INTO rooms (name, created_by) VALUES (%s, %s)", (room_name, self.user_id))
                conn.commit()
                messagebox.showinfo("Thành công", f"Phòng '{room_name}' đã được tạo thành công.")
                self.populate_initial_options() # Refresh the list of public rooms
            except mysql.connector.IntegrityError as err:
                messagebox.showerror("Lỗi", f"Tên phòng '{room_name}' đã tồn tại. Vui lòng chọn tên khác.")
            except Exception as e:
                messagebox.showerror("Lỗi CSDL", f"Không thể tạo phòng: {e}")
            finally:
                if conn:
                    conn.close()

    def populate_initial_options(self):
        """Populates the public chat room buttons."""
        for widget in self.public_rooms_frame.winfo_children():
            widget.destroy()

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM rooms ORDER BY name ASC")
            public_rooms = [row[0] for row in cursor.fetchall()]
            
            if not public_rooms:
                ttk.Label(self.public_rooms_frame, text="Chưa có phòng chat công khai nào.").pack(pady=5)
            else:
                for room_name in public_rooms:
                    ttk.Button(self.public_rooms_frame, 
                               text=f"Phòng: {room_name}", 
                               width=35,
                               command=lambda rn=room_name: self.app_controller.start_chat(chat_mode="public", room_id=rn)
                             ).pack(pady=2, padx=5, fill=tk.X)
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải danh sách phòng chat công khai: {e}")
            ttk.Label(self.public_rooms_frame, text="Lỗi khi tải phòng chat.").pack(pady=5)
        finally:
            if conn:
                conn.close()
                
    def update_all_registered_users_list(self):
        """
        Populates the private users frame with buttons for all registered users from the database.
        """
        # Clear existing buttons
        for widget in self.private_users_frame.winfo_children():
            widget.destroy()

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users ORDER BY username ASC")
            all_users = [row[0] for row in cursor.fetchall()]

            if not all_users:
                ttk.Label(self.private_users_frame, text="Chưa có người dùng nào.").pack(pady=5)
            else:
                for user in sorted(all_users):
                    # Exclude the current user from the private chat list
                    if user != self.username: 
                        ttk.Button(self.private_users_frame, 
                                   text=f"{self.PRIVATE_CHAT_PREFIX}{user}", 
                                   width=35, # Set width for consistency with public rooms
                                   command=lambda u=user: self.app_controller.start_chat(chat_mode="private", target_username=u)
                                  ).pack(pady=2, padx=5, fill=tk.X) # Pack with fill=tk.X and padding
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải danh sách người dùng: {e}")
            ttk.Label(self.private_users_frame, text="Lỗi khi tải người dùng.").pack(pady=5)
        finally:
            if conn:
                conn.close()
        
    def logout(self):
        """Logs out the current user and returns to the start screen."""
        # The switch_screen method now handles cleanup of chat_client.
        self.app_controller.username = None
        self.app_controller.user_id = None # Clear user_id on logout
        self.app_controller.switch_screen(StartScreen)

    def exit_application(self):
        """
        Handles the Exit button click, returning to the StartScreen.
        """
        # This will trigger the cleanup logic in AppController's switch_screen
        self.app_controller.switch_screen(StartScreen)


class ChatPanel(ttk.Frame):
    """
    ChatPanel is a dynamic frame containing ChatClient instances.
    """
    def __init__(self, master, app_controller):
        super().__init__(master, padding="10 10 10 10")
        self.app_controller = app_controller
        self.current_chat_client = None

        self.welcome_label = ttk.Label(self, text="Chọn một phòng chat hoặc người dùng để bắt đầu.", font=("Arial", 12, "italic"))
        self.welcome_label.pack(expand=True)

    def load_chat_client(self, username, chat_mode, room_id=None, target_username=None):
        """
        Loads a new ChatClient into the ChatPanel.
        """
        if self.current_chat_client:
            self.current_chat_client.running = False
            self.current_chat_client.manually_closed = True
            self.current_chat_client.safe_disconnect()
            self.current_chat_client.destroy()
            self.current_chat_client = None

        self.welcome_label.pack_forget()

        self.current_chat_client = ChatClient(
            self,
            username=username,
            chat_mode=chat_mode,
            room_id=room_id,
            target_username=target_username,
            return_to_main_callback=self.app_controller.clear_chat_panel,
            update_online_users_callback=None
        )
        self.current_chat_client.pack(fill=tk.BOTH, expand=True)

        if chat_mode == "public":
            self.app_controller.title(f"Phòng Chat: {room_id} - Người dùng: {username}")
        elif chat_mode == "private" and target_username:
            self.app_controller.title(f"Chat Riêng với: {target_username} - Người dùng: {username}")
        elif chat_mode == "private":
            self.app_controller.title(f"Chat Riêng: Chọn người dùng - Người dùng: {username}")

    def clear_chat(self):
        """
        Clears the current ChatClient and shows the welcome label.
        """
        if self.current_chat_client:
            self.current_chat_client.running = False
            self.current_chat_client.manually_closed = True
            self.current_chat_client.safe_disconnect()
            self.current_chat_client.destroy()
            self.current_chat_client = None
            
        self.welcome_label.pack(expand=True)

# Run the application
if __name__ == "__main__":
    app = AppController()
    app.mainloop()