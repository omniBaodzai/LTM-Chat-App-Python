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
        
        # Define geometries for different modes
        self.AUTH_GEOMETRY = "500x400"  # Smaller size for login/register
        self.CHAT_GEOMETRY = "1000x600" # Larger size for the main chat interface

        self.geometry(self.AUTH_GEOMETRY)
        self.resizable(False, False)

        # Set a consistent background color for the root window directly
        # This will also be the default for ttk.Frames inside it.
        self.configure(bg='#F0F0F0') # A common light gray that works well

        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TButton', font=('Arial', 10), padding=6)
        style.map('TButton',
                  background=[('active', '#e0e0e0'), ('!active', '#F0F0F0')], 
                  foreground=[('active', 'black'), ('!active', 'black')])
        style.configure('TEntry', font=('Arial', 10), padding=3)
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TPanedwindow', background='#f0f0f0')

        # Store the default background color of the Tkinter window for use by tk.Button
        # Now it's guaranteed to be a hex code
        self.default_bg_color = '#e0e0e0'

        self.current_screen = None
        self.username = None
        self.user_id = None

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
        if self.chat_panel and self.chat_panel.current_chat_client:
            self.chat_panel.current_chat_client.running = False
            self.chat_panel.current_chat_client.manually_closed = True
            self.chat_panel.current_chat_client.safe_disconnect()
            self.chat_panel.clear_chat()

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
            self.user_id = kwargs.get('user_id')
            self.setup_chat_interface()
            self.geometry(self.CHAT_GEOMETRY)
            self.resizable(True, True)
            self.title(f"Ứng dụng Chat - Đã đăng nhập: {self.username}")
        else:
            self.current_screen = screen_class(self, self, default_bg=self.default_bg_color, **kwargs)
            self.current_screen.pack(fill="both", expand=True)
            self.geometry(self.AUTH_GEOMETRY)
            self.resizable(False, False)
            self.title("Ứng dụng Chat")


    def setup_chat_interface(self):
        """Sets up the main chat interface using a ttk.PanedWindow."""
        self.chat_container_frame = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.chat_container_frame.pack(fill=tk.BOTH, expand=True)

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
        Refreshes the MainPanel's room and user lists.
        """
        if self.chat_panel:
            self.chat_panel.clear_chat()
            self.title(f"Ứng dụng Chat - Đã đăng nhập: {self.username}")
        
        # Added lines to refresh MainPanel when returning from chat
        if self.main_panel:
            self.main_panel.populate_initial_options()
            self.main_panel.update_all_registered_users_list()


class StartScreen(ttk.Frame):
    """Initial screen with a welcome message and a start button."""
    def __init__(self, master, controller, default_bg=None):
        super().__init__(master, padding="20 20 20 20")
        self.controller = controller
        self.default_bg = default_bg 

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(2, weight=1) 

        content_frame = ttk.Frame(self)
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=1) 

        ttk.Label(content_frame, text="Chào mừng đến ứng dụng Chat", font=("Arial", 20, "bold")).pack(pady=40)
        ttk.Button(content_frame, text="Bắt đầu", width=20, command=lambda: controller.switch_screen(LoginScreen)).pack(pady=10)


class LoginScreen(ttk.Frame):
    """Login screen for existing users."""
    def __init__(self, master, controller, default_bg=None):
        super().__init__(master, padding="20 20 20 20")
        self.controller = controller
        self.default_bg = default_bg
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self.back_arrow_image = tk.PhotoImage(width=20, height=20)
        
        # Use the passed default_bg, which is now guaranteed to be a hex code
        fill_color = self.default_bg if self.default_bg else '#F0F0F0'
        
        self.back_arrow_image.put(fill_color, (0, 0, 20, 20))
        self.back_arrow_image.put("black", (5, 9, 15, 11))
        self.back_arrow_image.put("black", (5, 9, 7, 10))
        self.back_arrow_image.put("black", (5, 10, 7, 11))


        self.back_button = tk.Button(self, image=self.back_arrow_image, command=lambda: controller.switch_screen(StartScreen),
                                      bg=self.default_bg,
                                      activebackground=self.default_bg,
                                      relief='flat', bd=0, highlightthickness=0)
        self.back_button.place(x=10, y=10)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(4, weight=1) 

        content_frame = ttk.Frame(self)
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=1) 

        ttk.Label(content_frame, text="Đăng Nhập", font=("Arial", 18, "bold")).pack(pady=30)
        
        form = ttk.Frame(content_frame, padding="10 10 10 10")
        form.pack()

        # Adjustments for left-alignment
        form.columnconfigure(1, weight=1) # Give weight to the column containing entries
        ttk.Label(form, text="Tên người dùng:").grid(row=0, column=0, sticky='w', pady=5, padx=5) 
        ttk.Entry(form, textvariable=self.username_var, width=30).grid(row=0, column=1, sticky='ew', pady=5, padx=5) 

        ttk.Label(form, text="Mật khẩu:").grid(row=1, column=0, sticky='w', pady=5, padx=5) 
        ttk.Entry(form, textvariable=self.password_var, show='*', width=30).grid(row=1, column=1, sticky='ew', pady=5, padx=5) 

        ttk.Button(content_frame, text="Đăng nhập", width=15, command=self.login).pack(pady=20)
        
        # --- MODIFIED PART FOR LINK BUTTON ---
        tk.Button(
            content_frame,
            text="Chưa có tài khoản? Đăng ký",
            command=lambda: controller.switch_screen(RegisterScreen),
            foreground='blue',
            background=self.default_bg,  # Use the exact background color of the frame
            activebackground=self.default_bg, # Match active background
            relief='flat',
            font=('Arial', 9, 'underline'),
            borderwidth=0,  # Ensure no border
            highlightthickness=0 # Remove highlight border
        ).pack()

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
            cursor.execute("SELECT id, username FROM users WHERE username = %s AND password = %s", (username, hashed))
            user = cursor.fetchone()
            
            if user:
                user_id = user[0]
                username_from_db = user[1]
                self.controller.username = username_from_db
                self.controller.user_id = user_id
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
    def __init__(self, master, controller, default_bg=None):
        super().__init__(master, padding="20 20 20 20")
        self.controller = controller
        self.default_bg = default_bg
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.email_var = tk.StringVar()

        self.back_arrow_image = tk.PhotoImage(width=20, height=20)
        
        # Use the passed default_bg, which is now guaranteed to be a hex code
        fill_color = self.default_bg if self.default_bg else '#F0F0F0'
        
        self.back_arrow_image.put(fill_color, (0, 0, 20, 20))
        self.back_arrow_image.put("black", (5, 9, 15, 11))
        self.back_arrow_image.put("black", (5, 9, 7, 10))
        self.back_arrow_image.put("black", (5, 10, 7, 11))

        self.back_button = tk.Button(self, image=self.back_arrow_image, command=lambda: controller.switch_screen(StartScreen),
                                      bg=self.default_bg,
                                      activebackground=self.default_bg,
                                      relief='flat', bd=0, highlightthickness=0)
        self.back_button.place(x=10, y=10)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(4, weight=1) 

        content_frame = ttk.Frame(self)
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=1) 

        ttk.Label(content_frame, text="Đăng Ký", font=("Arial", 18, "bold")).pack(pady=30)
        
        form = ttk.Frame(content_frame, padding="10 10 10 10")
        form.pack()

        # Adjustments for left-alignment
        form.columnconfigure(1, weight=1) # Give weight to the column containing entries
        ttk.Label(form, text="Tên người dùng:").grid(row=0, column=0, sticky='w', pady=5, padx=5) 
        ttk.Entry(form, textvariable=self.username_var, width=30).grid(row=0, column=1, sticky='ew', pady=5, padx=5) 

        ttk.Label(form, text="Email:").grid(row=1, column=0, sticky='w', pady=5, padx=5) 
        ttk.Entry(form, textvariable=self.email_var, width=30).grid(row=1, column=1, sticky='ew', pady=5, padx=5) 

        ttk.Label(form, text="Mật khẩu:").grid(row=2, column=0, sticky='w', pady=5, padx=5) 
        ttk.Entry(form, textvariable=self.password_var, show='*', width=30).grid(row=2, column=1, sticky='ew', pady=5, padx=5) 

        ttk.Button(content_frame, text="Đăng ký", width=15, command=self.register).pack(pady=20)
        
        # --- MODIFIED PART FOR LINK BUTTON ---
        tk.Button(
            content_frame,
            text="Đã có tài khoản? Đăng nhập",
            command=lambda: controller.switch_screen(LoginScreen),
            foreground='blue',
            background=self.default_bg,  # Use the exact background color of the frame
            activebackground=self.default_bg, # Match active background
            relief='flat',
            font=('Arial', 9, 'underline'),
            borderwidth=0,  # Ensure no border
            highlightthickness=0 # Remove highlight border
        ).pack()

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

        # Configure grid for MainPanel
        self.columnconfigure(0, weight=1) # Allow column 0 to expand
        self.rowconfigure(3, weight=1)    # Allow the private_users_frame row to expand vertically

        # Row 0: Welcome message
        ttk.Label(self, text=f"Xin chào, {username}!", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=15, sticky="n")

        # Row 1: Public Rooms Section Label and Button (in a sub-frame for alignment)
        public_rooms_header_frame = ttk.Frame(self)
        public_rooms_header_frame.grid(row=1, column=0, columnspan=2, pady=(10, 5), sticky="ew")
        public_rooms_header_frame.columnconfigure(0, weight=1) # Label can expand
        public_rooms_header_frame.columnconfigure(1, weight=0) # Button fixed size

        ttk.Label(public_rooms_header_frame, text="Phòng Chat Công Khai:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky='w')
        ttk.Button(public_rooms_header_frame, text="Tạo Phòng", command=self.create_new_room).grid(row=0, column=1, padx=(5,0), sticky='e')

        # Row 2: Public Rooms Frame
        self.public_rooms_frame = ttk.Frame(self, padding="5 5 5 5", relief="groove", borderwidth=1) # Added relief for visual separation
        self.public_rooms_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        # Ensure buttons within public_rooms_frame fill horizontally
        self.public_rooms_frame.columnconfigure(0, weight=1)


        # Row 3: Private Users Section Label
        private_users_section_label_frame = ttk.Frame(self) 
        private_users_section_label_frame.grid(row=3, column=0, columnspan=2, pady=(10, 5), sticky="ew") # Changed row to 3
        private_users_section_label_frame.columnconfigure(0, weight=1)
        ttk.Label(private_users_section_label_frame, text="Tất cả Người dùng (Chat Riêng):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky='w')

        # Row 4: Private Users Frame (will expand vertically)
        self.private_users_frame = ttk.Frame(self, padding="5 5 5 5", relief="groove", borderwidth=1) # Added relief
        self.private_users_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew") # Changed row to 4, added 'ns' for vertical expand
        # This is important for scrollability if you add a canvas/scrollbar later, or just for button expansion.
        self.private_users_frame.columnconfigure(0, weight=1) # Allow buttons inside to expand horizontally
        self.rowconfigure(4, weight=1) # Make this row take up extra vertical space


        # Row 5: Logout Button
        ttk.Button(self, text="Đăng xuất", 
                   command=self.logout).grid(row=5, column=0, columnspan=2, pady=10, sticky="s") # Changed row to 5, sticky to bottom

        self.populate_initial_options()
        self.update_all_registered_users_list()

    def create_new_room(self):
        """Prompts the user for a new room name and attempts to create it in the database."""
        room_name = simpledialog.askstring("Tạo Phòng Mới", "Nhập tên phòng mới:", parent=self)
        if room_name:
            room_name = room_name.strip()
            if not room_name:
                messagebox.showwarning("Cảnh báo", "Tên phòng không được để trống.")
                return

            if self.user_id is None:
                messagebox.showerror("Lỗi", "Không thể tạo phòng. Không tìm thấy ID người dùng. Vui lòng thử đăng nhập lại.")
                return

            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO rooms (name, created_by) VALUES (%s, %s)", (room_name, self.user_id))
                conn.commit()
                messagebox.showinfo("Thành công", f"Phòng '{room_name}' đã được tạo thành công.")
                self.populate_initial_options()
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
                               # Removed width, will expand with fill=tk.X
                               command=lambda rn=room_name: self.app_controller.start_chat(chat_mode="public", room_id=rn)
                              ).pack(pady=2, padx=5, fill=tk.X) # Changed to pack with fill=tk.X
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
                    if user != self.username: 
                        ttk.Button(self.private_users_frame, 
                                   text=f"{self.PRIVATE_CHAT_PREFIX}{user}", 
                                   # Removed width, will expand with fill=tk.X
                                   command=lambda u=user: self.app_controller.start_chat(chat_mode="private", target_username=u)
                                  ).pack(pady=2, padx=5, fill=tk.X) # Changed to pack with fill=tk.X
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải danh sách người dùng: {e}")
            ttk.Label(self.private_users_frame, text="Lỗi khi tải người dùng.").pack(pady=5)
        finally:
            if conn:
                conn.close()
        
    def logout(self):
        """Logs out the current user and returns to the start screen."""
        self.app_controller.username = None
        self.app_controller.user_id = None
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

if __name__ == "__main__":
    app = AppController()
    app.mainloop()
