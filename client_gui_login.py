
import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import queue # Để truyền tin nhắn từ luồng mạng sang luồng GUI

# --- Cấu hình ---
SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345
BUFFER_SIZE = 1024

MY_USERNAME = "chataap"
user_action = "REGISTER"  # LOGIN hoặc REGISTER
password = "bangbang"     # Lưu mật khẩu người dùng nhập

client_socket = None
receive_running = True
message_queue = queue.Queue()

def get_user_credentials():
    global MY_USERNAME, user_action, password

    def submit():
        nonlocal login_win
        uname = username_entry.get().strip()
        pwd = password_entry.get().strip()
        act = action_var.get()

        if not uname or not pwd:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đầy đủ tên và mật khẩu.")
            return

        MY_USERNAME = uname
        password = pwd
        user_action = act
        login_win.destroy()

    login_win = tk.Toplevel()
    login_win.title("Đăng nhập / Đăng ký")
    login_win.geometry("300x200")
    login_win.grab_set()

    tk.Label(login_win, text="Tên người dùng:").pack(pady=5)
    username_entry = tk.Entry(login_win)
    username_entry.pack()

    tk.Label(login_win, text="Mật khẩu:").pack(pady=5)
    password_entry = tk.Entry(login_win, show='*')
    password_entry.pack()

    action_var = tk.StringVar(value="REGISTER")
    tk.Radiobutton(login_win, text="Đăng nhập", variable=action_var, value="LOGIN").pack()
    tk.Radiobutton(login_win, text="Đăng ký", variable=action_var, value="REGISTER").pack()

    tk.Button(login_win, text="Xác nhận", command=submit).pack(pady=10)

    login_win.wait_window()

    if not MY_USERNAME:
        messagebox.showerror("Hủy", "Bạn chưa đăng nhập/đăng ký.")
        exit()

class ChatClientApp:
    def __init__(self, master):
        self.master = master
        master.title("LAN Chat Client")
        master.geometry("500x450")
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.create_widgets()
        self.master.after(100, self.process_queue)

        get_user_credentials()
        self.connect_to_server()

    def create_widgets(self):
        self.chat_history = scrolledtext.ScrolledText(self.master, wrap=tk.WORD, state='disabled', font=("Arial", 10))
        self.chat_history.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.chat_history.tag_config('self_message', foreground='blue')

        self.message_frame = tk.Frame(self.master)
        self.message_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

        self.message_entry = tk.Entry(self.message_frame, font=("Arial", 10))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind("<Return>", self.send_message_event)

        self.send_button = tk.Button(self.message_frame, text="Gửi", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=5)

    def connect_to_server(self):
        global client_socket, user_action, password, MY_USERNAME
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_IP, SERVER_PORT))
            print(f"Đã kết nối tới server {SERVER_IP}:{SERVER_PORT}")

            msg_to_send = f"{user_action}:{MY_USERNAME}:{password}"
            print(f"[DEBUG] Gửi tới server: {msg_to_send}")
            client_socket.send(msg_to_send.encode("utf-8"))

            threading.Thread(target=self.receive_messages_from_server, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Lỗi kết nối", f"Không thể kết nối tới server: {e}\nĐảm bảo server đang chạy!")
            self.master.destroy()

    def receive_messages_from_server(self):
        global receive_running
        while receive_running:
            try:
                message = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if not message:
                    message_queue.put("[SYSTEM]:Server đã đóng kết nối.")
                    break
                message_queue.put(message)
            except OSError as e:
                if receive_running:
                    print(f"Lỗi nhận tin nhắn (có thể do socket đóng): {e}")
                break
            except Exception as e:
                print(f"Lỗi không xác định khi nhận: {e}")
                break
        print("Luồng nhận tin nhắn đã dừng.")
        client_socket.close()

    def send_message_event(self, event=None):
        self.send_message()

    def send_message(self):
        msg_content = self.message_entry.get()
        if msg_content.strip():
            self.display_message(f"[{MY_USERNAME}]: {msg_content}", is_self=True)
            try:
                client_socket.send(msg_content.encode('utf-8'))
            except Exception as e:
                messagebox.showerror("Lỗi gửi tin", f"Không thể gửi tin nhắn: {e}")
                print(f"Lỗi gửi tin: {e}")
            self.message_entry.delete(0, tk.END)

    def display_message(self, message, is_self=False):
        self.chat_history.config(state='normal')
        if is_self:
            self.chat_history.insert(tk.END, message + "\n", 'self_message')
        else:
            self.chat_history.insert(tk.END, message + "\n")
        self.chat_history.config(state='disabled')
        self.chat_history.yview(tk.END)

    def process_queue(self):
        try:
            while True:
                message = message_queue.get_nowait()
                self.display_message(message)
        except queue.Empty:
            pass
        finally:
            self.master.after(100, self.process_queue)

    def on_closing(self):
        global receive_running
        if messagebox.askokcancel("Thoát ứng dụng", "Bạn có muốn thoát ứng dụng chat không?"):
            receive_running = False
            try:
                if client_socket:
                    client_socket.shutdown(socket.SHUT_RDWR)
                    client_socket.close()
            except OSError as e:
                print(f"Lỗi khi đóng socket: {e}")
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientApp(root)
    root.mainloop()
