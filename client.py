import socket
import threading
import tkinter as tk
from config import SERVER_HOST, SERVER_PORT

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connected = False
room_id = ""

# GUI setup
root = tk.Tk()
root.title("💬 Client Chat")

tk.Label(root, text="Tên của bạn:").pack()
name_entry = tk.Entry(root)
name_entry.pack()

tk.Label(root, text="Mã phòng (tự tạo nếu chưa có):").pack()
room_entry = tk.Entry(root)
room_entry.pack()

text_area = tk.Text(root, height=20, width=50)
text_area.pack()

message_entry = tk.Entry(root, width=40)
message_entry.pack(side=tk.LEFT, padx=5)

def send_message():
    global connected
    if not connected:
        text_area.insert(tk.END, "❌ Không thể gửi tin vì chưa kết nối đến server!\n")
        return
    msg = f"[{room_id}] {name_entry.get()}: {message_entry.get()}"
    try:
        client.send(msg.encode())
    except OSError:
        text_area.insert(tk.END, "❌ Gửi tin nhắn thất bại. Kết nối bị mất.\n")
        return
    message_entry.delete(0, tk.END)

send_button = tk.Button(root, text="Gửi", command=send_message)
send_button.pack(side=tk.LEFT)

def receive_messages():
    global connected
    while connected:
        try:
            msg = client.recv(1024).decode()
            if msg:
                text_area.insert(tk.END, msg + "\n")
        except:
            text_area.insert(tk.END, "❌ Mất kết nối đến server.\n")
            break

def connect_to_server():
    global connected, room_id
    name = name_entry.get().strip()
    room = room_entry.get().strip()

    if not name or not room:
        text_area.insert(tk.END, "⚠️ Vui lòng nhập tên và mã phòng!\n")
        return

    try:
        client.connect((SERVER_HOST, SERVER_PORT))
        connected = True
        room_id = room
        join_msg = f"[{room_id}] {name} đã tham gia phòng chat!"
        client.send(join_msg.encode())
        text_area.insert(tk.END, f"✅ Đã kết nối tới server và vào phòng [{room_id}].\n")
        threading.Thread(target=receive_messages, daemon=True).start()
    except:
        text_area.insert(tk.END, "❌ Không kết nối được đến server!\n")
        connected = False

connect_button = tk.Button(root, text="Kết nối", command=connect_to_server)
connect_button.pack()

root.mainloop()
