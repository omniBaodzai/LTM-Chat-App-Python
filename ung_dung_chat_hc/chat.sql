-- Tạo cơ sở dữ liệu (nếu chưa tồn tại)
CREATE DATABASE IF NOT EXISTS chat_app1 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Chọn cơ sở dữ liệu để sử dụng
USE chat_app1;

-- Bảng users: Lưu trữ thông tin người dùng
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL, -- Sẽ lưu mật khẩu đã băm (bcrypt)
    username VARCHAR(100) UNIQUE NOT NULL, -- Tên người dùng duy nhất
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng rooms: Lưu trữ thông tin phòng chat/nhóm
CREATE TABLE rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL, -- Tên phòng/mã phòng duy nhất
    created_by INT NOT NULL, -- ID của người dùng đã tạo phòng này
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Bảng messages: Lưu trữ CHỈ tin nhắn công khai (trong phòng chat)
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT NOT NULL,           -- ID của phòng chat (Bắt buộc cho tin nhắn công khai)
    user_id INT NOT NULL,           -- ID của người gửi tin nhắn
    content TEXT NOT NULL,          -- Nội dung tin nhắn
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, -- Thời gian gửi tin nhắn
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

-- Bảng private_messages: Lưu trữ CHỈ tin nhắn riêng tư
CREATE TABLE private_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE, -- Thêm ON DELETE CASCADE
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE -- Thêm ON DELETE CASCADE
);

-- Gợi ý: Thêm chỉ mục để tối ưu hóa truy vấn
CREATE INDEX idx_messages_room_id ON messages (room_id);
CREATE INDEX idx_messages_user_id ON messages (user_id);
CREATE INDEX idx_messages_timestamp ON messages (timestamp);

-- Chỉ mục cho bảng private_messages
CREATE INDEX idx_private_messages_sender_id ON private_messages (sender_id);
CREATE INDEX idx_private_messages_receiver_id ON private_messages (receiver_id);
CREATE INDEX idx_private_messages_timestamp ON private_messages (timestamp);

-- CREATE FULLTEXT INDEX ft_messages_content ON messages (content); -- Nếu bạn muốn tìm kiếm toàn văn bản (có thể cần cấu hình MySQL)

