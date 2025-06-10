# Ứng dụng Chat Client-Server Đa Người Dùng (Python)

## Mô tả
Ứng dụng chat client-server hỗ trợ nhiều người dùng, sử dụng Python và socket programming. Server quản lý kết nối và phát tin nhắn đến tất cả các client.

## Tính năng
- Đăng nhập với tên người dùng.
- Gửi và nhận tin nhắn từ nhiều người dùng.
- Thông báo hệ thống khi người dùng tham gia hoặc rời khỏi phòng chat.
- Xử lý lỗi khi mất kết nối.

## Cách chạy
### Chạy Server
1. Mở terminal và di chuyển đến thư mục `chat_app`:
   ```bash
   cd d:\LTM\app\LTM-Chat-App-Python\chat_app
   ```
2. Chạy server bằng lệnh:
   ```bash
   py -m server.server
   ```

### Chạy Client

1. Mở một terminal khác và di chuyển đến thư mục `chat_app`:
   ```bash
   cd d:\LTM\app\LTM-Chat-App-Python\chat_app
   ```
2. Chạy client bằng lệnh:
   ```bash
   py -m client.client
   ```

### Hướng dẫn sử dụng
- Sau khi kết nối, nhập tên người dùng để tham gia phòng chat.
- Nhập tin nhắn để gửi đến tất cả người dùng trong phòng chat.
- Nhập `/quit` để ngắt kết nối.

## Cấu trúc thư mục
```
chat_app/
    config.py
    client/
        client.py
    server/
        server.py
        client_handler.py
```

## Lưu ý
- Đảm bảo rằng Python đã được cài đặt và thêm vào PATH.
- Nếu gặp lỗi, kiểm tra cấu trúc thư mục và các file `__init__.py` trong thư mục `server` và `client`.
