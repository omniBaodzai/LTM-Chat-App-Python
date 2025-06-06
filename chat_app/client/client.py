import socket
import threading
from tkinter import Tk, Text, Entry, Button, END, Label, Frame
from config import HOST, PORT

def receive_messages(client, chat_box, online_users_box):
    while True:
        try:
            msg = client.recv(1024).decode()
            if msg.startswith("[SYSTEM] Online users:"):
                # Cập nhật danh sách người dùng online
                online_users = msg.split(":")[1].strip()
                online_users_box.delete(1.0, END)
                online_users_box.insert(END, online_users)
            else:
                # Hiển thị tin nhắn trong khung chat
                chat_box.insert(END, msg + "\n")
        except:
            chat_box.insert(END, "[ERROR] Connection lost.\n")
            client.close()
            break

def send_message(client, input_box):
    msg = input_box.get()
    input_box.delete(0, END)
    if msg.lower() == "/quit":
        client.close()
        exit()
    client.send(msg.encode())

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
        print("[CONNECTED] You are connected to the chat server.")
        username = input("Enter your username: ")
        client.send(username.encode())

        # Giao diện Tkinter
        root = Tk()
        root.title("Chat Client")

        # Khung chính
        main_frame = Frame(root)
        main_frame.pack()

        # Khung hiển thị danh sách người dùng online
        Label(main_frame, text="Online Users").pack()
        online_users_box = Text(main_frame, height=5, width=50)
        online_users_box.pack()

        # Khung hiển thị tin nhắn
        Label(main_frame, text="Chat").pack()
        chat_box = Text(main_frame, height=15, width=50)
        chat_box.pack()

        # Ô nhập tin nhắn
        input_box = Entry(main_frame, width=40)
        input_box.pack()

        # Nút gửi tin nhắn
        send_button = Button(main_frame, text="Send", command=lambda: send_message(client, input_box))
        send_button.pack()

        # Luồng nhận tin nhắn
        threading.Thread(target=receive_messages, args=(client, chat_box, online_users_box), daemon=True).start()

        root.mainloop()
    except ConnectionRefusedError:
        print("[ERROR] Unable to connect to the server.")
    finally:
        client.close()

if __name__ == "__main__":
    main()