import socket
import threading

HOST = '127.0.0.1'
PORT = 12345

def receive_messages(client):
    while True:
        try:
            message = client.recv(1024).decode()
            print("\nNgười khác:", message)
        except:
            print("[-] Mất kết nối với server")
            client.close()
            break

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    print("[+] Kết nối đến server!")

    threading.Thread(target=receive_messages, args=(client,), daemon=True).start()

    while True:
        msg = input("Bạn: ")
        if msg.lower() == "exit":
            break
        client.send(msg.encode())

    client.close()

if __name__ == "__main__":
    main()
