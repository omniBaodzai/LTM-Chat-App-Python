16/06/2025
chat_app/
│
├── server/                 # Chứa toàn bộ logic phía máy chủ (Server)
│   ├── server.py           # Xử lý chính: socket, rooms, broadcast, lưu tin nhắn
│   ├── main.py             # File khởi chạy server
│   ├── config.py           # Hàm kết nối cơ sở dữ liệu (get_db_connection)
│
├── database/               # Chứa file khởi tạo cấu trúc CSDL
│   └── schema.sql          # ⚠️ Quan trọng! Mình sẽ giải thích bên dưới
│
├── client/                 # Mọi thứ liên quan đến client
│   ├── client.py           # Đăng nhập/đăng ký, kết nối đến server
│   └── client_gui.py       # Giao diện người dùng (Tkinter/PyQt...)
│
├── README.md               # Giới thiệu dự án: cách cài đặt, chạy, tính năng
├── requirements.txt        # Danh sách thư viện Python cần cài

    #Cài đặt cơ sở dữ liệu:
CREATE DATABASE chat_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
Cách 1: Dùng MySQL Workbench
    Mở Workbench → kết nối với MySQL
    Chọn database chat_app vừa tạo
    Mở schema.sql → Nhấn Run All (⚡)

Cách 2: Dùng phpMyAdmin
    Vào phpMyAdmin → chọn database chat_app
    Chọn tab Import
    Chọn file schema.sql → Nhấn Go

✅ Cách 3: Dùng dòng lệnh (Command Line)
    mysql -u root -p chat_app < database/schema.sql

