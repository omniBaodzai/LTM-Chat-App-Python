def handle_client(client_socket, broadcast, clients):
    try:
        while True:
            message = client_socket.recv(1024).decode()
            if not message:
                break
            if message.startswith("@"):  # Tin nhắn riêng tư
                target_user, private_msg = message.split(" ", 1)
                target_user = target_user[1:]  # Loại bỏ ký tự "@"
                for sock, user in clients.items():
                    if user == target_user:
                        sock.sendall(f"[PRIVATE] {clients[client_socket]}: {private_msg}".encode())
                        break
            else:
                broadcast(f"{clients[client_socket]}: {message}", client_socket)
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        username = clients.get(client_socket, "Unknown User")
        client_socket.close()
        del clients[client_socket]
        broadcast(f"[SYSTEM] {username} has left the chat.")