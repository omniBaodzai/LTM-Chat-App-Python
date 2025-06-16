import socket
import threading
import json
from server.config import HOST, PORT
from server.database.queries import register_user, login_user, logout_user

def handle_client(conn, addr):
    print(f"📥 New connection from {addr}")

    while True:
        try:
            data = conn.recv(1024).decode()
            if not data:
                print(f"🔌 Client {addr} disconnected.")
                break

            try:
                request = json.loads(data)
                print("📨 Request:", request)

                response = process_request(request)
                print("📤 Response:", response)

                conn.send(json.dumps(response).encode())

            except json.JSONDecodeError:
                print("⚠️ Lỗi định dạng JSON:", data)
                continue

        except Exception as e:
            print(f"❌ Error handling client {addr}: {e}")
            break

    conn.close()
    print(f"🔌 Connection closed from {addr}")

def process_request(request):
    action = request.get("action")

    if action == "register":
        success, message = register_user(
            request["username"], request["password"],
            request["email"], request["phone"]
        )
        return {"success": success, "message": message}

    elif action == "login":
        success, user_id, message = login_user(
            request["identifier"], request["password"]
        )
        return {"success": success, "user_id": user_id, "message": message}

    elif action == "logout":
        success, message = logout_user(request["user_id"])
        return {"success": success, "message": message}

    elif action == "send_message":
        print(f"💬 Tin nhắn từ user {request['user_id']}: {request['message']}")
        return {"success": True, "message": "Tin nhắn đã được gửi (demo)"}

    return {"success": False, "message": "Invalid action"}

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"🚀 Server listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    main()
