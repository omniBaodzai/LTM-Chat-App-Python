import socket
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

# Tạo 2 client socket riêng biệt
client_a = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client_a.connect((SERVER_IP, SERVER_PORT))
client_b.connect((SERVER_IP, SERVER_PORT))

# Giao diện
root = tk.Tk()
root.title("LAN Chat - 2 Clients")

chat_area = ScrolledText(root, state='disabled', width=60, height=20, font=("Segoe UI", 10))
chat_area.pack(padx=10, pady=5)

# Nhận tin từ server
def receive_messages(client):
    while True:
        try:
            message = client.recv(1024).decode()
            chat_area.config(state='normal')
            chat_area.insert(tk.END, message + '\n')
            chat_area.config(state='disabled')
            chat_area.yview(tk.END)
        except:
            break

# Gửi từ A
def send_from_a():
    msg = entry_a.get()
    if msg.strip():
        full_msg = f"👤 Client A: {msg}"
        client_a.send(full_msg.encode())
        entry_a.delete(0, tk.END)

# Gửi từ B
def send_from_b():
    msg = entry_b.get()
    if msg.strip():
        full_msg = f"👥 Client B: {msg}"
        client_b.send(full_msg.encode())
        entry_b.delete(0, tk.END)

# Giao diện Client A
frame_a = tk.Frame(root)
frame_a.pack(pady=5)

entry_a = tk.Entry(frame_a, width=45)
entry_a.pack(side=tk.LEFT, padx=(10, 5))

button_a = tk.Button(frame_a, text="Gửi A", command=send_from_a)
button_a.pack(side=tk.LEFT)

# Giao diện Client B
frame_b = tk.Frame(root)
frame_b.pack(pady=5)

entry_b = tk.Entry(frame_b, width=45)
entry_b.pack(side=tk.LEFT, padx=(10, 5))

button_b = tk.Button(frame_b, text="Gửi B", command=send_from_b)
button_b.pack(side=tk.LEFT)

# Bắt đầu nhận tin song song
threading.Thread(target=receive_messages, args=(client_a,), daemon=True).start()
threading.Thread(target=receive_messages, args=(client_b,), daemon=True).start()

root.mainloop()
