# login.py
import tkinter as tk
from tkinter import messagebox, simpledialog
import mysql.connector
import hashlib


# Hàm băm mật khẩu
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Kết nối CSDL
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # sửa theo máy bạn
        database="chat_app1"
    )
# Căn giữa màn hình
def center_window(master, width, height):
    screen_width = master.winfo_screenwidth()
    screen_height = master.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    master.geometry(f"{width}x{height}+{x}+{y}")

# ✅ Dùng hàm để gọi lại màn hình login (tránh import vòng)
def show_login_screen():
    root = tk.Tk()
    LoginScreen(root)
    root.mainloop()
    
# Màn hình bắt đầu
class StartScreen:
    def __init__(self, master):
        self.master = master
        master.title("Chào mừng đến Chat App")
        center_window(master, 350, 220)  # 👈 căn giữa

        tk.Label(master, text="💬 Ứng dụng Chat Real-time", font=("Arial", 16, "bold")).pack(pady=30)
        tk.Button(master, text="Bắt đầu", width=20, command=self.goto_login).pack()

    def goto_login(self):
        self.master.destroy()
        root = tk.Tk()
        LoginScreen(root)
        root.mainloop()

# Giao diện đăng nhập
class LoginScreen:
    def __init__(self, master):
        self.master = master
        master.title("Đăng nhập")
        center_window(master, 350, 220)  # 👈 căn giữa

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.room_id_var = tk.StringVar()

        form = tk.Frame(master, padx=20, pady=15)
        form.pack()

        tk.Label(form, text="Tên người dùng:").grid(row=0, column=0, sticky='w', pady=5)
        tk.Entry(form, textvariable=self.username_var, width=30).grid(row=0, column=1)

        tk.Label(form, text="Mật khẩu:").grid(row=1, column=0, sticky='w', pady=5)
        tk.Entry(form, show='*', textvariable=self.password_var, width=30).grid(row=1, column=1)

        tk.Label(form, text="Mã phòng:").grid(row=2, column=0, sticky='w', pady=5)
        tk.Entry(form, textvariable=self.room_id_var, width=30).grid(row=2, column=1)

        tk.Button(master, text="Đăng nhập", width=15, command=self.login).pack(pady=(5, 2))
        tk.Button(master, text="Chưa có tài khoản? Đăng ký", command=self.goto_register).pack()

    def login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        room_id = self.room_id_var.get().strip()
        hashed = hash_password(password)

        if not username or not password or not room_id:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng điền đầy đủ thông tin.")
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM users WHERE username = %s AND password = %s", (username, hashed))
            user = cursor.fetchone()

            if not user:
                messagebox.showerror("Lỗi", "Sai tên đăng nhập hoặc mật khẩu.")
                conn.close()
                return

            user_id = user[0]

            cursor.execute("SELECT * FROM rooms WHERE name = %s", (room_id,))
            room = cursor.fetchone()
            if not room:
                create = messagebox.askyesno("Phòng chưa tồn tại", f"Tạo mới phòng '{room_id}'?")
                if create:
                    # Sau khi tạo phòng xong (room_name, created_by)
                    cursor.execute("INSERT INTO rooms (name, created_by) VALUES (%s, %s)", (room_id, user_id))
                    # Sau đó gán người tạo là admin
                    cursor.execute("INSERT INTO room_members (room_id, user_id, is_admin) VALUES (%s, %s, TRUE)", (room_id, user_id))
                    conn.commit()
                    messagebox.showinfo("Thành công", f"Đã tạo phòng '{room_id}'.")
                else:
                    conn.close()
                    return

            conn.close()
            self.master.destroy()
            new_root = tk.Tk()
            self.ChatClient(new_root, username, room_id)
            new_root.mainloop()

        except Exception as e:
            messagebox.showerror("Lỗi CSDL", str(e))

    def goto_register(self):
        self.master.destroy()
        root = tk.Tk()
        RegisterScreen(root)
        root.mainloop()

# Giao diện đăng ký
class RegisterScreen:
    def __init__(self, master):
        self.master = master
        master.title("Đăng ký")
        center_window(master, 350, 220)  # 👈 căn giữa

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.email_var = tk.StringVar()

        form = tk.Frame(master, padx=20, pady=15)
        form.pack()

        tk.Label(form, text="Tên người dùng:").grid(row=0, column=0, sticky='w', pady=5)
        tk.Entry(form, textvariable=self.username_var, width=30).grid(row=0, column=1)

        tk.Label(form, text="Email:").grid(row=1, column=0, sticky='w', pady=5)
        tk.Entry(form, textvariable=self.email_var, width=30).grid(row=1, column=1)

        tk.Label(form, text="Mật khẩu:").grid(row=2, column=0, sticky='w', pady=5)
        tk.Entry(form, show='*', textvariable=self.password_var, width=30).grid(row=2, column=1)

        tk.Button(master, text="Đăng ký", width=15, command=self.register).pack(pady=(5, 2))
        tk.Button(master, text="Đã có tài khoản? Đăng nhập", command=self.goto_login).pack()

    def register(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        email = self.email_var.get().strip()

        if not username or not password or not email:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng điền đầy đủ thông tin.")
            return

        hashed = hash_password(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, hashed, email))
            conn.commit()
            conn.close()
            messagebox.showinfo("Thành công", "Đăng ký thành công! Vui lòng đăng nhập.")
            self.goto_login()
        except mysql.connector.IntegrityError as err:
            if "username" in str(err):
                messagebox.showerror("Lỗi", "Tên người dùng đã tồn tại.")
            elif "email" in str(err):
                messagebox.showerror("Lỗi", "Email đã được sử dụng.")
            else:
                messagebox.showerror("Lỗi CSDL", str(err))
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", str(e))

    def goto_login(self):
        self.master.destroy()
        root = tk.Tk()
        LoginScreen(root)
        root.mainloop()

# Điểm khởi chạy
if __name__ == "__main__":
    root = tk.Tk()
    StartScreen(root)
    root.mainloop()
