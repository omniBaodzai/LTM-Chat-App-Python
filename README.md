Dưới đây là nội dung đề xuất cho file `README.md` của ứng dụng WebSocket có khả năng chịu tải cao với FastAPI và Redis:

---

# 🧠 FastAPI WebSocket High Load Chat

Ứng dụng WebSocket Chat sử dụng FastAPI + Redis với khả năng chịu tải cao (tối ưu RAM/CPU), cho phép nhiều người dùng giao tiếp trong thời gian thực.

## 🚀 Tính năng chính

* Kết nối WebSocket thời gian thực.
* Broadcast tin nhắn cho tất cả client đã kết nối.
* Giao diện thân thiện, responsive.
* Quản lý kết nối tối ưu với hàng đợi nội bộ.
* Redis Pub/Sub để chia sẻ trạng thái/tin nhắn nếu mở rộng đa tiến trình/đa máy chủ.
* Heartbeat (ping) để kiểm tra kết nối sống/chết.
* Log và giám sát kết nối.

## 📁 Cấu trúc thư mục

```
.
├── app/
│   ├── main.py                  # Điểm bắt đầu của ứng dụng FastAPI
│   ├── websocket.py             # WebSocket endpoint
│   ├── websocket_client.py      # Giao diện WebSocket client (HTML)
│   └── services/
│       └── connection_manager.py # Quản lý kết nối WebSocket + Redis
├── requirements.txt             # Thư viện cần cài
└── README.md                    # Tài liệu này
```

## ⚙️ Cài đặt

### 1. Cài môi trường ảo

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 2. Cài thư viện

```bash
pip install -r requirements.txt
```

### 3. Khởi chạy Redis

Đảm bảo Redis đang chạy ở `localhost:6379`. Nếu chưa có:

```bash
docker run -d -p 6379:6379 redis
```

### 4. Khởi chạy ứng dụng

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Mở trình duyệt: [http://localhost:8000/ws-client](http://localhost:8000/ws-client)

## 📡 Endpoint chính

| Method | Đường dẫn      | Mô tả                     |
| ------ | -------------- | ------------------------- |
| GET    | `/ws-client`   | Trả về trang HTML chat    |
| WS     | `/ws?name=...` | Kết nối WebSocket với tên |

## 🛠️ Kỹ thuật sử dụng

* **FastAPI**: Web framework hiệu năng cao.
* **WebSocket**: Kết nối thời gian thực 2 chiều.
* **Redis Pub/Sub**: Giao tiếp đa tiến trình hoặc đa server.
* **AsyncIO Queue**: Hàng đợi để xử lý tin nhắn tối ưu CPU.
* **orjson**: Thư viện JSON nhanh.
* **Logging & Heartbeat**: Theo dõi và duy trì kết nối sống.

## ⚡ Hiệu năng & Chịu tải

* Giới hạn 500 kết nối đồng thời (tùy cấu hình RAM/CPU).
* Tối đa 1000 tin nhắn chờ trong hàng đợi.
* Tự động ngắt kết nối client không phản hồi ping.

## 📌 Mở rộng

* Triển khai Redis Cluster cho khả năng chịu tải cao hơn.
* Kết hợp Celery nếu cần xử lý message nặng nền.
* Gắn JWT hoặc xác thực bảo vệ endpoint `/ws`.

## 👨‍💻 Tác giả

> **Tác giả**: \[Tên bạn]
> **Github**: [https://github.com/yourprofile](https://github.com/yourprofile)

---

Nếu bạn muốn, mình có thể tạo luôn `requirements.txt` tương ứng. Bạn cần không?
