````markdown
# Ứng dụng Chat Client-Server Đa Người Dùng (Python + Tkinter + MySQL)

## Mô tả
Ứng dụng chat thời gian thực sử dụng Python với giao diện GUI (Tkinter), hỗ trợ:
- Chat công khai theo phòng
- Chat riêng tư giữa người dùng
- Lưu trữ đầy đủ bằng MySQL

## Tính năng
- Đăng ký / Đăng nhập bảo mật bằng SHA-256
- Chat công khai (theo phòng)
- Chat riêng tư 1-1
- Hiển thị trạng thái online/offline
- Lưu trữ toàn bộ tin nhắn trong MySQL
- Giao diện GUI Tkinter dễ sử dụng

## Cài đặt

### 1. Cài thư viện cần thiết
```bash
pip install mysql-connector-python
````

### 2. Tạo cơ sở dữ liệu

```bash
mysql -u root -p < chat.sql
```

> Tạo database `chat_app1` gồm các bảng:
>
> * users
> * rooms
> * messages
> * private\_messages

### 3. Cấu hình kết nối MySQL

Sửa file `client/config.py`:

```python
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="your_password",
        database="chat_app1",
        autocommit=True
    )
```

## Cách chạy ứng dụng

### Chạy server

```bash
python server/server.py
```

> Server lắng nghe tại `0.0.0.0:12345` để các client trong mạng LAN kết nối được.

### Chạy client

```bash
python main.py
```

> Giao diện lần lượt qua:
>
> * Màn hình chào
> * Đăng nhập hoặc đăng ký
> * Giao diện chat

## Kết nối mạng LAN

* Đặt `HOST = '0.0.0.0'` trong `server.py` để server nhận kết nối từ IP khác
* Client cần kết nối đúng IP LAN của server trong:

  * `chat_client.py`
  * `gui_manager.py`
* Mở port `12345` trong firewall nếu cần

## Cấu trúc thư mục

```
chat_app/
├── client/
│   ├── config.py             # Cấu hình kết nối MySQL
│   ├── chat_client.py        # Client giao tiếp socket và GUI Tkinter
│   └── gui_manager.py        # Điều hướng giao diện, đăng nhập / đăng ký
│
├── server/
│   └── server.py             # Xử lý server, socket, threading, MySQL
│
├── chat.sql                  # Cấu trúc CSDL MySQL
├── main.py                   # Điểm bắt đầu khởi chạy client
└── README.md                 # Tài liệu hướng dẫn
```

## Bảo mật

* Mật khẩu được băm bằng SHA-256 trước khi gửi đến server
* Có thể nâng cấp dùng bcrypt để tăng độ an toàn

## Ghi chú kỹ thuật

* Mỗi client kết nối là một luồng riêng trên server
* Tin nhắn lưu vào MySQL (cả công khai và riêng tư)
* Ứng dụng hỗ trợ nhiều người dùng và phòng chat đồng thời



