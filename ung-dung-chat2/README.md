

```markdown
# Chat App Python

Ứng dụng chat thời gian thực được xây dựng bằng Python, giao diện GUI với Tkinter, hỗ trợ chat công khai (theo phòng), chat riêng tư giữa các người dùng, và lưu trữ toàn bộ dữ liệu bằng MySQL.

---

## Cấu trúc thư mục

```

chat\_app/
├── client/
│   ├── config.py             # Cấu hình kết nối MySQL
│   ├── chat\_client.py        # Giao diện và xử lý client chat (GUI Tkinter)
│   └── gui\_manager.py        # Giao diện điều hướng, đăng nhập / đăng ký
│
├── server.py                 # Xử lý logic server, socket, threading, MySQL
├── chat.sql                  # Cấu trúc CSDL MySQL
├── main.py                   # Điểm bắt đầu chạy ứng dụng GUI
└── README.md                 # Tài liệu hướng dẫn

````

---

## Tính năng chính

- ✅ **Đăng ký / Đăng nhập** có bảo mật bằng SHA-256 (bạn có thể nâng cấp lên bcrypt).
- ✅ **Chat công khai** theo phòng (người tạo có quyền xóa phòng).
- ✅ **Chat riêng tư** giữa 2 người dùng.
- ✅ **Hiển thị trạng thái online/offline** của người dùng.
- ✅ **Lưu trữ toàn bộ dữ liệu chat** vào MySQL (tin nhắn công khai + riêng tư).
- ✅ Giao diện GUI hiện đại bằng Tkinter với nhiều tương tác trực quan.

---

## Cài đặt

### 1. Cài thư viện cần thiết

```bash
pip install mysql-connector-python
````

---

### 2. Khởi tạo cơ sở dữ liệu

Chạy file SQL `chat.sql`:

```bash
mysql -u root -p < chat.sql
```

> CSDL tên là `chat_app1`, bao gồm 4 bảng: `users`, `rooms`, `messages`, `private_messages`.

---

### 3. Cấu hình kết nối MySQL

Chỉnh lại file `client/config.py`:

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

## Cách chạy ứng dụng

### Chạy Server:

```bash
python server.py
```

> Server sẽ lắng nghe tại `0.0.0.0:12345` (mọi IP trong LAN đều kết nối được).

---

### Chạy Client:

```bash
python main.py
```

> Giao diện sẽ khởi động từ màn hình chào → đăng nhập / đăng ký → chọn phòng / người dùng để chat.

---

## Kết nối mạng LAN

* Server đặt `HOST = '0.0.0.0'` để cho phép nhận kết nối từ IP khác.
* Client phải kết nối tới đúng địa chỉ IP LAN của server (đặt tại `HOST` trong `chat_client.py` và `gui_manager.py`).
* Mở port `12345` trong firewall nếu bị chặn.

---

## Bảo mật

* Mật khẩu được **băm SHA256**, không lưu plain text.
* Có thể nâng cấp lên `bcrypt` để tăng độ bảo mật hơn.

---

## Tùy chọn nâng cao (Gợi ý mở rộng)

* Gửi file, ảnh, emoji,...
* Tìm kiếm tin nhắn.
* Chat nhóm có quyền quản trị.
* Thông báo đẩy khi có tin mới.

---

## Ghi chú

* Dữ liệu đầy đủ lưu vào MySQL.
* Mỗi kết nối là một thread server xử lý riêng.
* Server có thể xử lý đa luồng, nhiều phòng và người dùng đồng thời.

---

