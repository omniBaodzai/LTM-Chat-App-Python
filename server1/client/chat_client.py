#chat_client.py
import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox
from datetime import datetime
import atexit
import sys
import signal
import json
from login import show_login_screen  # ✅ Tránh import class trực tiếp (để tránh vòng lặp)

HOST = '127.0.0.1'
PORT = 12345

class ChatClient:
    def __init__(self, master, username=None, room_id=None):
        self.master = master

        # Xử lý đóng cửa sổ an toàn
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.username = username.strip()
        self.room_id = room_id.strip()
        self.kicked = False  # ✅ Cờ kiểm tra bị kick

        if not self.username or not self.room_id:
            messagebox.showwarning("Lỗi", "Thiếu tên hoặc mã phòng.")
            master.quit()
            return
        # Đặt kích thước cửa sổ
        self.master.geometry("600x400")
        self.master.resizable(False, False)
        
        # Đổi tiêu đề khung giao diện
        self.master.title(f"{self.username} @ {self.room_id}")

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
        if self.kicked:
            return  # ✅ Không cho gửi nếu đã bị kick
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
        self.in_history = False
        buffer = ''
        while True:
            try:
                data = self.client.recv(4096).decode()
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self.process_message(line.strip())
            except Exception as e:
                print(f"[!] Lỗi khi nhận tin nhắn: {e}")
                break
    
    def process_message(self, message):
        if message == "__history_start__":
            self.in_history = True
            return
        elif message == "__history_end__":
            self.in_history = False
            self.display_message("— Hết lịch sử tin nhắn —", is_system=True)
            return

        try:
            msg_data = json.loads(message)
            sender = msg_data['sender']
            content = msg_data['content']
            timestamp = msg_data['timestamp']
        except json.JSONDecodeError as e:
            print(f"[⚠️ JSON lỗi]: {e} | Dòng bị lỗi: {message}")
            self.display_message(f"[⚠️ JSON lỗi]: {message}", is_system=True)
            return
        
        # ✅ Nếu bị kick
        if "bị kick khỏi phòng" in content or "🚫 Bạn đã bị kick" in content:
            self.kicked = True  # ➤ Gắn cờ bị kick
            self.display_message(f"[{timestamp}] {content}", is_system=True)

            try:
                self.client.close()
            except:
                pass

            messagebox.showerror("🚫 Bạn bị kick!", f"{content}\n\nBạn sẽ trở lại màn hình chính.")
            self.master.destroy()
            show_login_screen()  # ✅ Gọi lại màn hình login
            return

        if sender == "system":
            self.display_message(f"[{timestamp}] {content}", is_system=True)
        elif sender == self.username:
            self.display_message(f"[{timestamp}] Bạn: {content}", align_right=True, is_history=self.in_history)
        else:
            self.display_message(f"[{timestamp}] {sender}: {content}", align_right=False, is_history=self.in_history)

    def display_message(self, message, align_right=False, is_system=False, is_history=False):
        self.chat_box.config(state='normal')

        self.chat_box.tag_configure('right', justify='right', background='lightblue',
                                    font=('Arial', 10), lmargin1=150, lmargin2=150)
        self.chat_box.tag_configure('left', justify='left', background='white',
                                    font=('Arial', 10), lmargin1=5, lmargin2=5)
        self.chat_box.tag_configure('center', justify='center', foreground='gray',
                                    font=('Arial', 9, 'italic'))

        # ✅ Thêm định dạng riêng cho lịch sử
        self.chat_box.tag_configure('history-left', justify='left', background='#eeeeee',
                                    font=('Arial', 10), lmargin1=5, lmargin2=5)
        self.chat_box.tag_configure('history-right', justify='right', background='#dddddd',
                                    font=('Arial', 10), lmargin1=150, lmargin2=150)

        if is_system:
            self.chat_box.insert(tk.END, message + '\n', 'center')
        elif is_history:
            tag = 'history-right' if align_right else 'history-left'
            self.chat_box.insert(tk.END, message + '\n', tag)
        else:
            tag = 'right' if align_right else 'left'
            self.chat_box.insert(tk.END, message + '\n', tag)

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
