import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox
from datetime import datetime
import atexit
import sys
import signal

HOST = '127.0.0.1'
PORT = 12345

class ChatClient:
    def __init__(self, master):
        self.master = master

        # Xử lý đóng cửa sổ an toàn
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Nhập tên người dùng
        self.username = simpledialog.askstring("Tên người dùng", "Nhập tên của bạn:")
        if not self.username:
            messagebox.showwarning("Lỗi", "Bạn phải nhập tên người dùng.")
            master.quit()
            return

        # Nhập mã phòng
        self.room_id = simpledialog.askstring("Phòng Chat", "Nhập mã phòng:")
        if not self.room_id:
            messagebox.showwarning("Lỗi", "Bạn phải nhập mã phòng.")
            master.quit()
            return
        #Đổi tiêu đề khung giao diện
        self.master.title(f"Mã Chat Room: {self.room_id} - Username: {self.username}")

        # Kết nối tới server
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((HOST, PORT))
            self.client.send(f"{self.room_id}|{self.username}".encode())
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể kết nối đến server.\n{e}")
            master.quit()
            return

        # GUI
        self.chat_box = scrolledtext.ScrolledText(master, state='disabled', width=60, height=20)
        self.chat_box.pack(padx=10, pady=10)

        self.entry_field = tk.Entry(master, width=40)
        self.entry_field.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10))
        self.entry_field.bind("<Return>", self.send_message)

        self.send_button = tk.Button(master, text="Gửi", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=10, pady=(0, 10))

        # Bắt đầu nhận tin
        threading.Thread(target=self.receive_messages, daemon=True).start()

        # Đăng ký thoát an toàn
        atexit.register(self.exit_gracefully)
        signal.signal(signal.SIGINT, self.signal_handler)

    def send_message(self, event=None):
        msg = self.entry_field.get()
        if msg:
            try:
                self.client.send(msg.encode())
                self.entry_field.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("Lỗi", "Không thể gửi tin nhắn.")
                print(f"[!] Gửi thất bại: {e}")
                self.master.quit()

    def receive_messages(self):
        while True:
            try:
                message = self.client.recv(1024).decode()
                if not message:
                    break

                parts = message.split('|')
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
            except Exception as e:
                print(f"[!] Lỗi khi nhận tin nhắn: {e}")
                break

    def display_message(self, message, align_right=False, is_system=False):
        self.chat_box.config(state='normal')
        self.chat_box.tag_configure('right', justify='right', background='lightblue', font=('Arial', 10), lmargin1=150, lmargin2=150)
        self.chat_box.tag_configure('left', justify='left', background='white', font=('Arial', 10), lmargin1=5, lmargin2=5)
        self.chat_box.tag_configure('center', justify='center', foreground='gray', font=('Arial', 9, 'italic'))

        if align_right:
            self.chat_box.insert(tk.END, message + '\n', 'right')
        elif is_system:
            self.chat_box.insert(tk.END, message + '\n', 'center')
        else:
            self.chat_box.insert(tk.END, message + '\n', 'left')

        self.chat_box.yview(tk.END)
        self.chat_box.config(state='disabled')

    def on_closing(self):
        try:
            self.client.send("/quit".encode())
        except:
            pass
        try:
            self.client.close()
        except:
            pass
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
        # Ctrl+C trong terminal cũng gọi hàm thoát
        self.exit_gracefully()
        sys.exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()
