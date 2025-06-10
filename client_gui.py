import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import queue # Để truyền tin nhắn từ luồng mạng sang luồng GUI

# --- Cấu hình ---
SERVER_IP = '127.0.0.1' # Thường dùng 127.0.0.1 để test trên cùng máy, sau đó đổi thành IP của server trong LAN
SERVER_PORT = 12345
BUFFER_SIZE = 1024

MY_USERNAME = ""
client_socket = None # Socket client toàn cục
receive_running = True # Biến cờ để kiểm soát luồng nhận

# --- Hàng đợi để giao tiếp giữa luồng mạng và luồng GUI ---
message_queue = queue.Queue()

class ChatClientApp:
    def __init__(self, master):
        self.master = master
        master.title("LAN Chat Client") # Tên mặc định, sẽ cập nhật sau
        master.geometry("500x450")
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.create_widgets()
        self.master.after(100, self.process_queue) # Bắt đầu kiểm tra hàng đợi tin nhắn

        # Yêu cầu tên người dùng khi khởi động
        self.get_initial_username()

        # Cố gắng kết nối tới server
        self.connect_to_server()

    def create_widgets(self):
        # Khung hiển thị tin nhắn
        self.chat_history = scrolledtext.ScrolledText(self.master, wrap=tk.WORD, state='disabled', font=("Arial", 10))
        self.chat_history.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.chat_history.tag_config('self_message', foreground='blue') # Màu xanh cho tin nhắn của mình

        # Khung nhập tin nhắn
        self.message_frame = tk.Frame(self.master)
        self.message_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

        self.message_entry = tk.Entry(self.message_frame, font=("Arial", 10))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind("<Return>", self.send_message_event)

        self.send_button = tk.Button(self.message_frame, text="Gửi", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=5)

    def get_initial_username(self):
        global MY_USERNAME
        MY_USERNAME = simpledialog.askstring("Chào mừng!", "Nhập tên của bạn:")
        while not MY_USERNAME or not MY_USERNAME.strip():
            messagebox.showwarning("Lỗi", "Tên không được để trống!")
            MY_USERNAME = simpledialog.askstring("Chào mừng!", "Nhập tên của bạn:")
        MY_USERNAME = MY_USERNAME.strip()
        self.master.title(f"LAN Chat Client - {MY_USERNAME}")

    def connect_to_server(self):
        global client_socket
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_IP, SERVER_PORT))
            print(f"Đã kết nối tới server {SERVER_IP}:{SERVER_PORT}")
            # Gửi tên người dùng cho server ngay sau khi kết nối
            client_socket.send(f"USERNAME:{MY_USERNAME}".encode('utf-8'))

            # Bắt đầu luồng nhận tin nhắn từ server
            threading.Thread(target=self.receive_messages_from_server, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Lỗi kết nối", f"Không thể kết nối tới server: {e}\nĐảm bảo server đang chạy!")
            self.master.destroy() # Đóng ứng dụng nếu không kết nối được

    def receive_messages_from_server(self):
        """Hàm nhận tin nhắn từ server, chạy trong luồng riêng."""
        global receive_running
        while receive_running:
            try:
                message = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if not message: # Server đóng kết nối
                    message_queue.put("[SYSTEM]:Server đã đóng kết nối.")
                    break
                message_queue.put(message)
            except OSError as e: # Socket đã bị đóng
                if receive_running: # Chỉ in lỗi nếu chưa cố ý đóng
                    print(f"Lỗi nhận tin nhắn (có thể do socket đóng): {e}")
                break
            except Exception as e:
                print(f"Lỗi không xác định khi nhận: {e}")
                break
        print("Luồng nhận tin nhắn đã dừng.")
        client_socket.close() # Đóng socket khi luồng dừng

    def send_message_event(self, event=None):
        self.send_message()

    def send_message(self):
        msg_content = self.message_entry.get()
        if msg_content.strip():
            # Hiển thị tin nhắn của chính mình ngay lập tức
            self.display_message(f"[{MY_USERNAME}]: {msg_content}", is_self=True)
            try:
                # Gửi tin nhắn đến server (không cần thêm username vào đây, server sẽ biết)
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
        """Kiểm tra hàng đợi tin nhắn và hiển thị lên GUI."""
        try:
            while True:
                message = message_queue.get_nowait()
                # Server sẽ gửi lại tin nhắn đã định dạng đầy đủ bao gồm tên người gửi
                # Nên không cần MY_USERNAME in message ở đây
                self.display_message(message)
        except queue.Empty:
            pass
        finally:
            self.master.after(100, self.process_queue)

    def on_closing(self):
        """Xử lý khi đóng cửa sổ GUI."""
        global receive_running
        if messagebox.askokcancel("Thoát ứng dụng", "Bạn có muốn thoát ứng dụng chat không?"):
            receive_running = False # Dừng luồng nhận
            try:
                if client_socket:
                    # Gửi một tin nhắn đặc biệt hoặc đóng socket để báo server client ngắt kết nối
                    client_socket.shutdown(socket.SHUT_RDWR) # Tắt cả gửi và nhận
                    client_socket.close()
            except OSError as e:
                print(f"Lỗi khi đóng socket: {e}")
            
            self.master.destroy() # Đóng cửa sổ GUI

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientApp(root)
    root.mainloop()