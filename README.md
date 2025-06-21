Dưới đây là file `README.md` hoàn chỉnh cho dự án **Chat App Python** của bạn, bao gồm mô tả, cấu trúc thư mục, hướng dẫn cài đặt và sử dụng:

---

```markdown
# 💬 Chat App Python

Ứng dụng chat thời gian thực sử dụng giao thức TCP, có giao diện GUI bằng Tkinter, xác thực người dùng, quản lý phòng chat, và lưu trữ dữ liệu vào MySQL.

---

## 🏗️ Cấu trúc thư mục

```

chat\_app/
├── client/
│   ├── **init**.py
│   ├── chat\_client.py        # Giao diện và xử lý chat
│   ├── login\_gui.py          # Giao diện đăng nhập / đăng ký
│   └── config.py             # Kết nối MySQL
│
├── server/
│   ├── **init**.py
│   └── server.py             # Xử lý TCP socket, luồng client
│
├── main.py                   # Chạy ứng dụng từ GUI (bắt đầu từ màn hình Start)
├── requirements.txt          # Danh sách thư viện cần cài
└── README.md                 # Tài liệu hướng dẫn

````

---

## 🧩 Tính năng chính

- Giao diện đồ họa đơn giản, dễ dùng với Tkinter.
- Đăng nhập / đăng ký tài khoản.
- Quản lý phòng chat bằng mã.
- Chat nhiều người theo phòng (qua TCP socket).
- Lưu toàn bộ tin nhắn, tài khoản và phòng vào MySQL.
- Có thể build thành `.exe` để chạy độc lập trên máy khác.

---

## 🖥️ Cài đặt

### 1. Cài thư viện cần thiết
```bash
pip install -r requirements.txt
````

---

### 2. Khởi tạo CSDL MySQL

**Tạo CSDL và các bảng:**

```sql
CREATE DATABASE chat_app1 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE chat_app1;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);
```

---

### 3. Cấu hình kết nối MySQL

Chỉnh thông tin trong file `client/config.py`:

```python
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="your_mysql_password",
        database="chat_app1",
        autocommit=True
    )
```

---

## 🚀 Chạy ứng dụng

### ✅ Chạy Server:

```bash
python server/server.py
```

### ✅ Chạy Client GUI:

```bash
python main.py
```

---



## 🌐 Kết nối mạng LAN

* Server nên chạy với `HOST = '0.0.0.0'` hoặc IP trong mạng LAN (ví dụ `192.168.1.x`)
* Các client máy khác dùng IP đó để kết nối.
* Mở port `12345` trong firewall nếu bị chặn.

---

## 📌 Ghi chú

* Dữ liệu người dùng và tin nhắn được lưu trên MySQL.
* Không hỗ trợ chat riêng tư (private) ở phiên bản này.
* Có thể mở rộng theo nhóm, thêm emoji, gửi file,...
---


