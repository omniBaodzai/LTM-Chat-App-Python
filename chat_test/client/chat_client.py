import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox
from datetime import datetime
import atexit
import sys
import signal

HOST = '192.168.1.17'  # IP của máy chủ
PORT = 12345

class ChatClient:
    def __init__(self, master, username=None, room_id=None):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        if not username:
            self.username = simpledialog.askstring("Tên người dùng", "Nhập tên của bạn:")
        if not username:
            messagebox.showwarning("Lỗi", "Bạn phải nhập tên người dùng.")
            master.quit()
            return
        self.username = username.strip()

        if not room_id:
            self.room_id = simpledialog.askstring("Phòng Chat", "Nhập mã phòng:")
        if not room_id:
            messagebox.showwarning("Lỗi", "Bạn phải nhập mã phòng.")
            master.quit()
            return
        self.room_id = room_id.strip()

        self.master.title(f"Mã Chat Room: {self.room_id} - Username: {self.username}")

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((HOST, PORT))
            self.client.send(f"{self.room_id}|{self.username}".encode())
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể kết nối đến server.\n{e}")
            master.quit()
            return

        self.chat_box = scrolledtext.ScrolledText(master, state='disabled', width=60, height=20)
        self.chat_box.pack(padx=10, pady=10)

        input_frame = tk.Frame(master)
        input_frame.pack(pady=(0, 10))

        self.entry_field = tk.Entry(input_frame, width=40)
        self.entry_field.pack(side=tk.LEFT, padx=(0, 10))
        self.entry_field.bind("<Return>", self.send_message)

        self.send_button = tk.Button(input_frame, text="Gửi", width=10, command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=(0, 10))

        self.exit_button = tk.Button(input_frame, text="Thoát", width=10, command=self.on_closing)
        self.exit_button.pack(side=tk.LEFT)

        threading.Thread(target=self.receive_messages, daemon=True).start()

        atexit.register(self.exit_gracefully)
        signal.signal(signal.SIGINT, self.signal_handler)

    def send_message(self, event=None):
        msg = self.entry_field.get()
        if msg:
            try:
                self.client.send(msg.encode())
                self.entry_field.delete(0, tk.END)
            except:
                self.master.quit()

    def receive_messages(self):
        buffer = ""
        while True:
            try:
                data = self.client.recv(1024).decode()
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self.process_message(line.strip())
            except:
                break

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

    def display_message(self, message, align_right=False, is_system=False):
        self.chat_box.config(state='normal')
        self.chat_box.tag_configure('right', justify='right', background='lightblue', font=('Arial', 10))
        self.chat_box.tag_configure('left', justify='left', background='white', font=('Arial', 10))
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

        # Quay về màn hình Start nếu có thể
        try:
            import tkinter as tk
            from client.login_gui import StartScreen
            root = tk.Tk()
            StartScreen(root)
            root.mainloop()
        except Exception as e:
            print("Không thể quay lại màn hình chính:", e)

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
