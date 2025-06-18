import tkinter as tk
from tkinter import messagebox
import hashlib
import mysql.connector
# CORRECTED: Changed import paths to use relative imports within the 'client' package
from .chat_client import ChatClient
from .config import get_db_connection

# Hàm băm mật khẩu
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Giao diện bắt đầu
class StartScreen:
    def __init__(self, master):
        self.master = master
        master.title("Ứng dụng Chat")
        master.geometry("300x150")

        tk.Label(master, text="Welcome to Chat App", font=("Arial", 16)).pack(pady=20)
        tk.Button(master, text="Bắt đầu", width=15, command=self.goto_login).pack()

    def goto_login(self):
        self.master.destroy()
        root = tk.Tk()
        LoginScreen(root)
        root.mainloop()

# Giao diện Đăng nhập
class LoginScreen:
    def __init__(self, master):
        self.master = master
        master.title("Đăng nhập")

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        form = tk.Frame(master, padx=20, pady=20)
        form.pack()

        tk.Label(form, text="Tên người dùng:").grid(row=0, column=0, sticky='w')
        tk.Entry(form, textvariable=self.username_var, width=30).grid(row=0, column=1)

        tk.Label(form, text="Mật khẩu:").grid(row=1, column=0, sticky='w')
        tk.Entry(form, show='*', textvariable=self.password_var, width=30).grid(row=1, column=1)

        tk.Button(master, text="Đăng nhập", width=15, command=self.login).pack(pady=(5, 0))
        tk.Button(master, text="Chưa có tài khoản? Đăng ký", command=self.goto_register).pack()

    def login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        hashed = hash_password(password)

        if not username or not password:
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

            conn.close()
            self.master.destroy()
            root = tk.Tk()
            MainScreen(root, username) # Pass username to MainScreen
            root.mainloop()

        except Exception as e:
            messagebox.showerror("Lỗi CSDL", str(e))

    def goto_register(self):
        self.master.destroy()
        root = tk.Tk()
        RegisterScreen(root)
        root.mainloop()

# Giao diện Đăng ký
class RegisterScreen:
    def __init__(self, master):
        self.master = master
        master.title("Đăng ký")

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.email_var = tk.StringVar()

        form = tk.Frame(master, padx=20, pady=20)
        form.pack()

        tk.Label(form, text="Tên người dùng:").grid(row=0, column=0, sticky='w')
        tk.Entry(form, textvariable=self.username_var, width=30).grid(row=0, column=1)

        tk.Label(form, text="Email:").grid(row=1, column=0, sticky='w')
        tk.Entry(form, textvariable=self.email_var, width=30).grid(row=1, column=1)

        tk.Label(form, text="Mật khẩu:").grid(row=2, column=0, sticky='w')
        tk.Entry(form, show='*', textvariable=self.password_var, width=30).grid(row=2, column=1)

        tk.Button(master, text="Đăng ký", width=15, command=self.register).pack(pady=(5, 0))
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
            if "Duplicate entry" in str(err) and "username" in str(err):
                messagebox.showerror("Lỗi", "Tên người dùng đã tồn tại.")
            elif "Duplicate entry" in str(err) and "email" in str(err):
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

# Giao diện Chính sau khi đăng nhập
class MainScreen:
    def __init__(self, master, username):
        self.master = master
        self.username = username
        master.title(f"Chào mừng, {self.username}!")
        master.geometry("400x200")

        tk.Label(master, text=f"Xin chào, {self.username}!", font=("Arial", 14)).pack(pady=20)
        tk.Button(master, text="Tham gia Phòng Chat Công khai", width=30, command=self.goto_public_chat).pack(pady=5)
        tk.Button(master, text="Bắt đầu Chat Riêng", width=30, command=self.goto_private_chat).pack(pady=5)
        tk.Button(master, text="Đăng xuất", width=30, command=self.logout).pack(pady=5)

    def goto_public_chat(self):
        self.master.destroy()
        root = tk.Tk()
        # ChatClient will ask for room_id
        ChatClient(root, self.username, chat_mode="public", return_to_main_callback=self.return_to_main)
        root.mainloop()

    def goto_private_chat(self):
        self.master.destroy()
        root = tk.Tk()
        # ChatClient will ask to select a user (initially empty target_username)
        ChatClient(root, self.username, chat_mode="private", target_username=None, return_to_main_callback=self.return_to_main)
        root.mainloop()

    def return_to_main(self):
        # This function is called when ChatClient wants to return to MainScreen
        new_root = tk.Tk()
        MainScreen(new_root, self.username)
        new_root.mainloop()

    def logout(self):
        self.master.destroy()
        root = tk.Tk()
        StartScreen(root) # Go back to the initial start screen
        root.mainloop()

# Điểm khởi chạy chính (nếu gọi file này trực tiếp)
if __name__ == "__main__":
    root = tk.Tk()
    StartScreen(root)
    root.mainloop()