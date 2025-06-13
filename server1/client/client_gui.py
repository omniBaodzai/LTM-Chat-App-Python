# client_gui.py
import tkinter as tk
from tkinter import messagebox, simpledialog
import mysql.connector
import hashlib
from client import ChatClient

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

class LoginRegisterGUI:
    def __init__(self, master):
        self.master = master
        master.title("Đăng nhập / Đăng ký")

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.room_id_var = tk.StringVar()
        # Thêm biến lưu email
        self.email_var = tk.StringVar()

         # Frame chính chứa toàn bộ form
        form_frame = tk.Frame(master, padx=20, pady=20)
        form_frame.pack()

        # Tên người dùng
        tk.Label(form_frame, text="Tên người dùng:").grid(row=0, column=0, sticky='w', pady=5)
        self.username_entry = tk.Entry(form_frame, textvariable=self.username_var, width=30)
        self.username_entry.grid(row=0, column=1, pady=5)

        # Gmail
        tk.Label(form_frame, text="Gmail:").grid(row=1, column=0, sticky='w', pady=5)
        self.email_entry = tk.Entry(form_frame, textvariable=self.email_var, width=30)
        self.email_entry.grid(row=1, column=1, pady=5)

        # Mật khẩu
        tk.Label(form_frame, text="Mật khẩu:").grid(row=2, column=0, sticky='w', pady=5)
        self.password_entry = tk.Entry(form_frame, show='*', textvariable=self.password_var, width=30)
        self.password_entry.grid(row=2, column=1, pady=5)

        # Mã phòng
        tk.Label(form_frame, text="Mã phòng:").grid(row=3, column=0, sticky='w', pady=5)
        self.room_id_entry = tk.Entry(form_frame, textvariable=self.room_id_var, width=30)
        self.room_id_entry.grid(row=3, column=1, pady=5)

        # Nút chức năng
        button_frame = tk.Frame(master)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Đăng nhập", width=15, command=self.login).pack(side='left', padx=5)
        tk.Button(button_frame, text="Đăng ký", width=15, command=self.register).pack(side='left', padx=5)

    def login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        room_id = self.room_id_var.get().strip()
        hashed = hash_password(password)

        if not room_id:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập mã phòng.")
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Lấy user_id
            cursor.execute("SELECT id FROM users WHERE username = %s AND password = %s", (username, hashed))
            user = cursor.fetchone()
            if not user:
                messagebox.showerror("Lỗi", "Sai tên đăng nhập hoặc mật khẩu.")
                conn.close()
                return
            user_id = user[0]

            # Kiểm tra hoặc tạo mã phòng
            cursor.execute("SELECT * FROM rooms WHERE name = %s", (room_id,))
            room = cursor.fetchone()
            if not room:
                create = messagebox.askyesno("Phòng chưa tồn tại", f"Mã phòng '{room_id}' chưa có. Bạn có muốn tạo mới không?")
                if create:
                    cursor.execute("INSERT INTO rooms (name, created_by) VALUES (%s, %s)", (room_id, user_id))
                    conn.commit()
                else:
                    messagebox.showinfo("Thông báo", "Vui lòng nhập mã phòng hợp lệ.")
                    conn.close()
                    return

            conn.close()
            self.master.destroy()
            self.open_chat_client(username, room_id)

        except Exception as e:
            messagebox.showerror("Lỗi CSDL", str(e))

    def register(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        email = self.email_var.get().strip()  # lấy Gmail
        room_id = self.room_id_var.get().strip()
        
        if not username or not password or not email or not room_id:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng điền đầy đủ thông tin.")
            return

        hashed = hash_password(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password, email)
                VALUES (%s, %s, %s)
            """, (username, hashed, email))
            conn.commit()
            conn.close()
            messagebox.showinfo("Thành công", "Đăng ký thành công! Bạn có thể đăng nhập.")
        except mysql.connector.IntegrityError as err:
            if "Duplicate entry" in str(err) and "username" in str(err):
                messagebox.showerror("Lỗi", "Tên người dùng đã tồn tại.")
            elif "Duplicate entry" in str(err) and "email" in str(err):
                messagebox.showerror("Lỗi", "Email đã được sử dụng.")
            else:
                messagebox.showerror("Lỗi CSDL", str(err))
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", str(e))


    def open_chat_client(self, username, room_id):
        new_root = tk.Tk()
        ChatClient(new_root, username, room_id)
        new_root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = LoginRegisterGUI(root)
    root.mainloop()
