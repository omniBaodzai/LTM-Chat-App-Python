import tkinter as tk
from tkinter import messagebox, PanedWindow, ttk, simpledialog
from client.chat_client import ChatClient
import hashlib
import socket
import os
from PIL import Image, ImageTk  # Nếu dùng ảnh JPG hoặc muốn resize icon
import ttkbootstrap as tb

def hash_password(password):
    """Hashes a given password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_scrollable_frame(parent):
    canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)

    scrollable_frame = ttk.Frame(canvas)
    window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    scrollable_frame.bind("<Configure>", on_frame_configure)

    def on_canvas_resize(event):
        canvas.itemconfig(window_id, width=event.width)

    canvas.bind("<Configure>", on_canvas_resize)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel(event):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _unbind_mousewheel(event):
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", _bind_mousewheel)
    canvas.bind("<Leave>", _unbind_mousewheel)

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    return canvas, scrollbar, scrollable_frame

def add_placeholder(entry, placeholder, is_password=False, color='grey'):
    def on_focus_in(event):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(foreground='black')
            if is_password:
                entry.config(show='*')
    def on_focus_out(event):
        if not entry.get():
            entry.insert(0, placeholder)
            entry.config(foreground=color)
            if is_password:
                entry.config(show='')
    entry.insert(0, placeholder)
    entry.config(foreground=color)
    if is_password:
        entry.config(show='')
    entry.bind('<FocusIn>', on_focus_in)
    entry.bind('<FocusOut>', on_focus_out)

class AppController(tb.Window):
    """
    Main application controller managing screen transitions and the overall window.
    """
    def __init__(self):
        super().__init__(themename="flatly")
        self.title("Ứng dụng Chat")

        # Thêm background cho toàn bộ cửa sổ
        bg_path = os.path.join('images', 'background.jpg')
        if os.path.exists(bg_path):
            self.bg_img = ImageTk.PhotoImage(Image.open(bg_path).resize((500, 400)))
            self.bg_label = tk.Label(self, image=self.bg_img)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Đổi icon cửa sổ thành logo của bạn (logo.ico)
        icon_path = os.path.join('images', 'logo.ico')
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # Define geometries for different modes
        self.AUTH_GEOMETRY = "500x400"  # Smaller size for login/register
        self.CHAT_GEOMETRY = "1000x600" # Larger size for the main chat interface

        self.geometry(self.AUTH_GEOMETRY)
        self.resizable(True, True)

        # Set a consistent background color for the root window directly
        self.configure(bg='#F0F0F0')

        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TButton', font=('Arial', 10), padding=6)
        style.map('TButton',
                  background=[('active', '#e0e0e0'), ('!active', '#F0F0F0')], 
                  foreground=[('active', 'black'), ('!active', 'black')])
        style.configure('TEntry', font=('Arial', 10), padding=3)
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TPanedwindow', background='#f0f0f0')

        # Store the default background color
        self.default_bg_color = '#e0e0e0'

        self.current_screen = None
        self.username = None
        self.user_id = None

        self.chat_container_frame = None
        self.main_panel = None
        self.chat_panel = None

        # Server connection details
        self.HOST = '192.168.1.9'  # Match with chat_client.py
        self.PORT = 12345

        self.switch_screen(StartScreen)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def send_server_request(self, request, timeout=5):
        """
        Sends a request to the server and receives a response.
        request: String request following protocol (e.g., "LOGIN|username|password")
        timeout: Response timeout in seconds
        Returns: Server response or None if error
        """
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.settimeout(timeout)
            client.connect((self.HOST, self.PORT))
            client.send(request.encode())
            response = client.recv(4096).decode().strip()
            return response
        except Exception as e:
            print(f"Error sending server request: {e}")
            return None
        finally:
            try:
                client.close()
            except:
                pass

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
            self.resizable(True, True)
            self.title("Ứng dụng Chat")

    def setup_chat_interface(self):
        """Sets up the main chat interface using a ttk.PanedWindow."""
        self.chat_container_frame = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.chat_container_frame.pack(fill=tk.BOTH, expand=True)

        self.main_panel = MainPanel(self.chat_container_frame, self, 
                                     username=self.username, user_id=self.user_id) 
        self.chat_panel = ChatPanel(self.chat_container_frame, self)

        self.chat_container_frame.add(self.main_panel, weight=1)
        self.chat_container_frame.add(self.chat_panel, weight=5)

    def start_chat(self, chat_mode, room_id=None, target_username=None):
        """
        Called from MainPanel when a user selects a room/user to chat with.
        Instructs ChatPanel to load a new ChatClient.
        """
        self.main_panel = self.main_panel  # Ensure main_panel is retained
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
        
        if self.main_panel:
            self.main_panel.populate_initial_options()
            self.main_panel.update_all_registered_users_list()

class StartScreen(tb.Frame):
    """Initial screen with a welcome message and a start button."""
    def __init__(self, master, controller, default_bg=None):
        super().__init__(master)
        self.controller = controller
        self.default_bg = default_bg
        content_frame = tb.Frame(self, width=420)
        content_frame.place(relx=0.5, rely=0.5, anchor='center')
        logo_path = os.path.join('images', 'logo.png')
        if os.path.exists(logo_path):
            self.logo_img = ImageTk.PhotoImage(Image.open(logo_path).resize((80, 80)))
            tb.Label(content_frame, image=self.logo_img).pack(pady=(0, 24))
        tb.Label(
            content_frame,
            text="Chào mừng bạn đến với ứng dụng chat!",
            font=("Segoe UI", 22, "bold"),
            bootstyle="primary",
            wraplength=400,
            justify='center'
        ).pack(pady=(0, 24))
        tb.Button(content_frame, text="Bắt đầu", width=20, bootstyle="success", command=lambda: controller.switch_screen(LoginScreen)).pack(pady=(24, 0))

class LoginScreen(tb.Frame):
    """Login screen for existing users."""
    def __init__(self, master, controller, default_bg=None):
        super().__init__(master)
        self.controller = controller
        self.default_bg = default_bg
        self.username_var = tb.StringVar()
        self.password_var = tb.StringVar()
        content_frame = tb.Frame(self, width=380)
        content_frame.place(relx=0.5, rely=0.5, anchor='center')
        tb.Label(content_frame, text="ĐĂNG NHẬP", font=("Segoe UI", 22, "bold"), bootstyle="primary").pack(pady=(0, 24))
        form = tb.Frame(content_frame)
        form.pack()
        user_icon_path = os.path.join('images', 'user_icon.png')
        password_icon_path = os.path.join('images', 'password_icon.png')
        self.user_icon = ImageTk.PhotoImage(Image.open(user_icon_path).resize((22, 22))) if os.path.exists(user_icon_path) else None
        self.password_icon = ImageTk.PhotoImage(Image.open(password_icon_path).resize((22, 22))) if os.path.exists(password_icon_path) else None
        tb.Label(form, image=self.user_icon).grid(row=0, column=0, padx=(0, 10), pady=8, sticky='e')
        username_entry = tb.Entry(form, textvariable=self.username_var, width=28, font=("Segoe UI", 12))
        username_entry.grid(row=0, column=1, pady=8, sticky='ew')
        add_placeholder(username_entry, "Tên người dùng")
        tb.Label(form, image=self.password_icon).grid(row=1, column=0, padx=(0, 10), pady=8, sticky='e')
        password_entry = tb.Entry(form, textvariable=self.password_var, width=28, font=("Segoe UI", 12))
        password_entry.grid(row=1, column=1, pady=8, sticky='ew')
        add_placeholder(password_entry, "Mật khẩu", is_password=True)
        tb.Button(content_frame, text="Đăng nhập", width=20, bootstyle="success", command=self.login).pack(pady=(24, 8))
        tb.Button(content_frame, text="Chưa có tài khoản? Đăng ký", bootstyle="link", command=lambda: controller.switch_screen(RegisterScreen)).pack()

    def login(self):
        """Sends login request to the server."""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        hashed = hash_password(password)

        if not username or not password:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng điền đầy đủ.")
            return

        request = f"LOGIN|{username}|{hashed}"
        response = self.controller.send_server_request(request)

        if response:
            parts = response.split("|")
            if parts[0] == "LOGIN_SUCCESS":
                if len(parts) == 3:
                    user_id, username_from_server = parts[1], parts[2]
                    self.controller.username = username_from_server
                    self.controller.user_id = int(user_id)
                    self.controller.switch_screen(MainPanel, username=username_from_server, user_id=user_id)
                else:
                    messagebox.showerror("Lỗi", "Phản hồi từ server không hợp lệ.")
            elif parts[0] == "LOGIN_FAILED":
                messagebox.showerror("Lỗi", "Sai tài khoản hoặc mật khẩu.")
            else:
                messagebox.showerror("Lỗi", f"Lỗi server: {response}")
        else:
            messagebox.showerror("Lỗi", "Không thể kết nối đến server.")

class RegisterScreen(tb.Frame):
    """Registration screen for new users."""
    def __init__(self, master, controller, default_bg=None):
        super().__init__(master)
        self.controller = controller
        self.default_bg = default_bg
        self.username_var = tb.StringVar()
        self.password_var = tb.StringVar()
        self.email_var = tb.StringVar()
        content_frame = tb.Frame(self, width=380)
        content_frame.place(relx=0.5, rely=0.5, anchor='center')
        tb.Label(content_frame, text="ĐĂNG KÝ", font=("Segoe UI", 22, "bold"), bootstyle="primary").pack(pady=(0, 24))
        form = tb.Frame(content_frame)
        form.pack()
        user_icon_path = os.path.join('images', 'user_icon.png')
        password_icon_path = os.path.join('images', 'password_icon.png')
        email_icon_path = os.path.join('images', 'email_icon.png')
        self.user_icon = ImageTk.PhotoImage(Image.open(user_icon_path).resize((22, 22))) if os.path.exists(user_icon_path) else None
        self.password_icon = ImageTk.PhotoImage(Image.open(password_icon_path).resize((22, 22))) if os.path.exists(password_icon_path) else None
        self.email_icon = ImageTk.PhotoImage(Image.open(email_icon_path).resize((22, 22))) if os.path.exists(email_icon_path) else None
        tb.Label(form, image=self.user_icon).grid(row=0, column=0, padx=(0, 10), pady=8, sticky='e')
        username_entry = tb.Entry(form, textvariable=self.username_var, width=28, font=("Segoe UI", 12))
        username_entry.grid(row=0, column=1, pady=8, sticky='ew')
        add_placeholder(username_entry, "Tên người dùng")
        tb.Label(form, image=self.email_icon).grid(row=1, column=0, padx=(0, 10), pady=8, sticky='e')
        email_entry = tb.Entry(form, textvariable=self.email_var, width=28, font=("Segoe UI", 12))
        email_entry.grid(row=1, column=1, pady=8, sticky='ew')
        add_placeholder(email_entry, "Email")
        tb.Label(form, image=self.password_icon).grid(row=2, column=0, padx=(0, 10), pady=8, sticky='e')
        password_entry = tb.Entry(form, textvariable=self.password_var, width=28, font=("Segoe UI", 12))
        password_entry.grid(row=2, column=1, pady=8, sticky='ew')
        add_placeholder(password_entry, "Mật khẩu", is_password=True)
        tb.Button(content_frame, text="Đăng ký", width=20, bootstyle="success", command=self.register).pack(pady=(24, 8))
        tb.Button(content_frame, text="Đã có tài khoản? Đăng nhập", bootstyle="link", command=lambda: controller.switch_screen(LoginScreen)).pack()

    def register(self):
        """Sends registration request to the server."""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        email = self.email_var.get().strip()

        if not username or not password or not email:
            messagebox.showwarning("Thiếu thông tin", "Điền đầy đủ tất cả các trường.")
            return

        hashed = hash_password(password)
        request = f"REGISTER|{username}|{hashed}|{email}"
        response = self.controller.send_server_request(request)

        if response:
            parts = response.split("|")
            if parts[0] == "REGISTER_SUCCESS":
                messagebox.showinfo("Thành công", "Đăng ký thành công. Vui lòng đăng nhập.")
                self.controller.switch_screen(LoginScreen)
            elif parts[0] == "REGISTER_FAILED":
                if "username" in response.lower():
                    messagebox.showerror("Lỗi", "Tên người dùng đã tồn tại.")
                elif "email" in response.lower():
                    messagebox.showerror("Lỗi", "Email đã được sử dụng.")
                else:
                    messagebox.showerror("Lỗi", parts[1] if len(parts) > 1 else "Lỗi không xác định.")
            else:
                messagebox.showerror("Lỗi", f"Lỗi server: {response}")
        else:
            messagebox.showerror("Lỗi", "Không thể kết nối đến server.")

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
        self.public_rooms = []  # Store public rooms list
        self.all_users = []     # Store all registered users list

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(4, weight=1)

        ttk.Label(self, text=f"Xin chào, {username}!", font=("Arial", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=15, sticky="n"
        )

        public_rooms_header_frame = ttk.Frame(self)
        public_rooms_header_frame.grid(row=1, column=0, columnspan=2, pady=(10, 5), sticky="ew")
        public_rooms_header_frame.columnconfigure(0, weight=1)
        public_rooms_header_frame.columnconfigure(1, weight=0)

        ttk.Label(public_rooms_header_frame, text="Phòng Chat Công Khai:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky='w'
        )
        ttk.Button(public_rooms_header_frame, text="Tạo Phòng", command=self.create_new_room).grid(
            row=0, column=1, padx=(5, 0), sticky='e'
        )

        # Scrollable public rooms
        public_rooms_canvas_frame = ttk.Frame(self)
        public_rooms_canvas_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        public_rooms_canvas_frame.columnconfigure(0, weight=1)
        public_rooms_canvas_frame.rowconfigure(0, weight=1)
        _, _, self.public_rooms_frame = create_scrollable_frame(public_rooms_canvas_frame)

        # Label for private chats
        private_users_section_label_frame = ttk.Frame(self)
        private_users_section_label_frame.grid(row=3, column=0, columnspan=2, pady=(10, 5), sticky="ew")
        private_users_section_label_frame.columnconfigure(0, weight=1)
        ttk.Label(private_users_section_label_frame, text="Tất cả Người dùng (Chat Riêng):", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky='w'
        )

        # Scrollable private users
        private_users_canvas_frame = ttk.Frame(self)
        private_users_canvas_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        private_users_canvas_frame.columnconfigure(0, weight=1)
        private_users_canvas_frame.rowconfigure(0, weight=1)
        _, _, self.private_users_frame = create_scrollable_frame(private_users_canvas_frame)

        ttk.Button(self, text="Đăng xuất", command=self.logout).grid(row=5, column=0, columnspan=2, pady=10, sticky="s")

        self.populate_initial_options()
        self.update_all_registered_users_list()

    def create_new_room(self):
        room_name = simpledialog.askstring("Tạo Phòng Mới", "Nhập tên phòng mới:", parent=self)
        if room_name:
            room_name = room_name.strip()
            if not room_name:
                messagebox.showwarning("Cảnh báo", "Tên phòng không được để trống.")
                return

            request = f"CREATE_ROOM|{room_name}|{self.user_id}"
            response = self.app_controller.send_server_request(request)

            if response:
                parts = response.split("|")
                if parts[0] == "CREATE_ROOM_SUCCESS":
                    messagebox.showinfo("Thành công", f"Phòng '{room_name}' đã được tạo thành công.")
                    self.populate_initial_options()
                elif parts[0] == "CREATE_ROOM_FAILED":
                    if "exists" in response.lower():
                        messagebox.showerror("Lỗi", f"Tên phòng '{room_name}' đã tồn tại.")
                    else:
                        messagebox.showerror("Lỗi", parts[1] if len(parts) > 1 else "Lỗi không xác định.")
                else:
                    messagebox.showerror("Lỗi", f"Lỗi server: {response}")
            else:
                messagebox.showerror("Lỗi", "Không thể kết nối đến server.")

    def populate_initial_options(self):
        for widget in self.public_rooms_frame.winfo_children():
            widget.destroy()

        request = "GET_PUBLIC_ROOMS"
        response = self.app_controller.send_server_request(request)

        if response:
            parts = response.split("|")
            if parts[0] == "PUBLIC_ROOMS":
                self.public_rooms = parts[1].split(",") if parts[1] else []
                if not self.public_rooms or self.public_rooms == ['']:
                    ttk.Label(self.public_rooms_frame, text="Chưa có phòng chat công khai nào.").pack(pady=5)
                else:
                    for room_name in self.public_rooms:
                        ttk.Button(self.public_rooms_frame, 
                                   text=f"Phòng: {room_name}", 
                                   command=lambda rn=room_name: self.app_controller.start_chat(chat_mode="public", room_id=rn)
                                  ).pack(pady=4, padx=(0, 0), fill='x', anchor='n')
            else:
                messagebox.showerror("Lỗi", f"Lỗi server: {response}")
                ttk.Label(self.public_rooms_frame, text="Lỗi khi tải phòng chat.").pack(pady=5)
        else:
            messagebox.showerror("Lỗi", "Không thể kết nối đến server.")
            ttk.Label(self.public_rooms_frame, text="Lỗi khi tải phòng chat.").pack(pady=5)

    def update_all_registered_users_list(self):
        for widget in self.private_users_frame.winfo_children():
            widget.destroy()

        request = "GET_ALL_USERS"
        response = self.app_controller.send_server_request(request)

        if response:
            parts = response.split("|")
            if parts[0] == "ALL_USERS":
                self.all_users = parts[1].split(",") if parts[1] else []
                if not self.all_users or self.all_users == ['']:
                    ttk.Label(self.private_users_frame, text="Chưa có người dùng nào").pack(pady=5)
                else:
                    for user in sorted(self.all_users):
                        if user != self.username: 
                            ttk.Button(self.private_users_frame, 
                                       text=f"{self.PRIVATE_CHAT_PREFIX}{user}", 
                                       command=lambda u=user: self.app_controller.start_chat(chat_mode="private", target_username=u)
                                      ).pack(pady=4, padx=(0, 0), fill='x', anchor='n')
            else:
                messagebox.showerror("Lỗi", f"Lỗi server: {response}")
                ttk.Label(self.private_users_frame, text="Lỗi khi tải người dùng.").pack(pady=5)
        else:
            messagebox.showerror("Lỗi", "Không thể kết nối đến server.")
            ttk.Label(self.private_users_frame, text="Lỗi khi tải người dùng.").pack(pady=5)

    def update_lists(self, items, is_rooms=False, is_users=False):
        """Updates public rooms or users list based on callback data."""
        if is_rooms:
            self.public_rooms = items
            for widget in self.public_rooms_frame.winfo_children():
                widget.destroy()
            if not self.public_rooms or self.public_rooms == ['']:
                ttk.Label(self.public_rooms_frame, text="Chưa có phòng chat công khai nào.").pack(pady=5)
            else:
                for room_name in sorted(self.public_rooms):
                    ttk.Button(self.public_rooms_frame, 
                               text=f"Phòng: {room_name}", 
                               command=lambda rn=room_name: self.app_controller.start_chat(chat_mode="public", room_id=rn)
                              ).pack(pady=4, padx=(0, 0), fill='x', anchor='n')
        elif is_users:
            self.all_users = items
            for widget in self.private_users_frame.winfo_children():
                widget.destroy()
            if not self.all_users or self.all_users == ['']:
                ttk.Label(self.private_users_frame, text="Chưa có người dùng nào").pack(pady=5)
            else:
                for user in sorted(self.all_users):
                    if user != self.username:
                        ttk.Button(self.private_users_frame, 
                                   text=f"{self.PRIVATE_CHAT_PREFIX}{user}", 
                                   command=lambda u=user: self.app_controller.start_chat(chat_mode="private", target_username=u)
                                  ).pack(pady=4, padx=(0, 0), fill='x', anchor='n')
        
    def logout(self):
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
            update_online_users_callback=self.app_controller.main_panel.update_lists  # Pass callback
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