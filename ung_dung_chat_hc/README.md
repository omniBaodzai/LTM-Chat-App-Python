
# Ứng dụng Chat Client-Server Đa Người Dùng (Python + Tkinter + MySQL)

## Mô tả

Ứng dụng chat thời gian thực được xây dựng bằng **Python**, sử dụng **Tkinter** cho giao diện người dùng và **MySQL** để lưu trữ dữ liệu. Hỗ trợ chat công khai theo phòng và chat riêng tư giữa các người dùng.

---

## Tính năng

- Đăng ký và đăng nhập với mật khẩu được băm bằng SHA-256  
- Chat công khai trong các phòng chat  
- Chat riêng tư giữa hai người dùng  
- Hiển thị trạng thái online/offline của người dùng  
- Lưu trữ toàn bộ tin nhắn (công khai và riêng tư) trong MySQL  
- Giao diện Tkinter thân thiện, dễ sử dụng  
- Hỗ trợ xóa phòng chat (chỉ người tạo phòng có quyền)  
- Cập nhật danh sách phòng và người dùng theo thời gian thực  

---

## Yêu cầu

- Python 3.6+
- MySQL Server
- Thư viện Python:

```bash
pip install tk mysql-connector-python==8.0.33
````

---

## Cài đặt

### 1. Tạo cơ sở dữ liệu

Tạo database `chat_app1` và các bảng cần thiết bằng cách chạy file `chat.sql`:

```bash
mysql -u root -p < chat.sql
```

Các bảng bao gồm:

* `users`: Lưu thông tin người dùng
* `rooms`: Lưu thông tin phòng chat công khai
* `messages`: Lưu tin nhắn công khai
* `private_messages`: Lưu tin nhắn riêng tư

---

### 2. Cấu hình kết nối MySQL

Chỉnh sửa file `client/config.py` để cập nhật thông tin kết nối MySQL:

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

---

### 3. Cấu hình IP server

Cập nhật địa chỉ IP của server trong các file:

**`client/chat_client.py`:**

```python
HOST = 'your_server_ip'  # Ví dụ: '192.168.1.9'
PORT = 12345
```

**`client/gui_manager.py`:**

```python
self.HOST = 'your_server_ip'  # Ví dụ: '192.168.1.9'
self.PORT = 12345
```

---

## Cách chạy ứng dụng

### 1. Chạy server

```bash
python server/server.py
```

Server sẽ lắng nghe tại `0.0.0.0:12345`, cho phép kết nối từ các client trong mạng LAN.

---

### 2. Chạy client

```bash
python main.py
```

Giao diện client sẽ hiển thị lần lượt:

* Màn hình chào mừng
* Đăng nhập hoặc đăng ký
* Giao diện chính với danh sách phòng chat và người dùng

---

## Kết nối mạng LAN

* Đảm bảo server và client ở cùng mạng LAN.
* Cập nhật đúng `HOST` trong `chat_client.py` và `gui_manager.py` thành IP của máy chạy server.
* Mở port `12345` trên firewall của máy chạy server nếu cần.

---

## Cấu trúc thư mục

```bash
chat_app/
├── client/
│   ├── config.py          # Cấu hình kết nối MySQL
│   ├── chat_client.py     # Xử lý giao tiếp socket và giao diện chat
│   └── gui_manager.py     # Quản lý giao diện và điều hướng
├── server/
│   └── server.py          # Server xử lý socket, luồng, và MySQL
├── chat.sql               # Cấu trúc cơ sở dữ liệu MySQL
├── main.py                # Điểm khởi chạy client
├── requirements.txt       # Danh sách thư viện yêu cầu
└── README.md              # Tài liệu hướng dẫn
```

---

## Bảo mật

* Mật khẩu được băm bằng **SHA-256** trước khi lưu trữ
* Khuyến nghị nâng cấp lên **bcrypt** để tăng cường bảo mật
* Tin nhắn được lưu trong **MySQL**, cần bảo vệ cơ sở dữ liệu

---

## Ghi chú kỹ thuật

* Server sử dụng **luồng riêng cho mỗi client** để xử lý kết nối đồng thời
* Danh sách phòng và người dùng được cập nhật **theo thời gian thực**
* Hỗ trợ **nhiều phòng chat và nhiều người dùng cùng lúc**
* Giao diện Tkinter sử dụng chủ đề `'clam'` để đảm bảo tính thẩm mỹ

---

## Hạn chế

* Chưa hỗ trợ mã hóa tin nhắn (khuyến nghị dùng **SSL/TLS**)
* Chưa hỗ trợ gửi file hoặc hình ảnh
* Giao diện cần cải thiện để hỗ trợ tốt hơn cho màn hình độ phân giải cao

```

---


