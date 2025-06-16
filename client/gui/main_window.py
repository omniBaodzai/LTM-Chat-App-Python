from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QLineEdit, QScrollArea
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self, user_id, client_socket):
        super().__init__()
        self.user_id = user_id
        self.client_socket = client_socket
        self.setWindowTitle("ChatApp - Messenger Style")
        self.resize(1000, 900)
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        central_widget.setStyleSheet("background-color: #ecf0f1;")

        # Header
        header_layout = QHBoxLayout()
        welcome_label = QLabel("💬 ChatApp")
        welcome_label.setFont(QFont("Arial", 20, QFont.Bold))
        welcome_label.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(welcome_label)

        logout_button = QPushButton("Đăng xuất")
        logout_button.setFont(QFont("Arial", 12))
        logout_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        logout_button.clicked.connect(self.handle_logout)
        header_layout.addStretch()
        header_layout.addWidget(logout_button)
        main_layout.addLayout(header_layout)

        # Scroll chat
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Input area
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Nhập tin nhắn...")
        self.message_input.setFont(QFont("Arial", 12))
        self.message_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 10px;
            }
        """)

        send_button = QPushButton("Gửi")
        send_button.setFont(QFont("Arial", 12))
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        send_button.clicked.connect(self.send_message)

        input_layout.addWidget(self.message_input, stretch=1)
        input_layout.addWidget(send_button)
        main_layout.addLayout(input_layout)

    def add_message(self, message, is_own=True):
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setFont(QFont("Arial", 12))
        message_label.setStyleSheet(f"""
            background-color: {'#3498db' if is_own else '#bdc3c7'};
            color: white;
            padding: 10px;
            border-radius: 10px;
            max-width: 60%;
        """)
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignRight if is_own else Qt.AlignLeft)
        layout.addWidget(message_label)

        container = QWidget()
        container.setLayout(layout)
        self.scroll_layout.addWidget(container)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def send_message(self):
        message = self.message_input.text().strip()
        if message:
            request = {"action": "send_message", "user_id": self.user_id, "message": message}
            success, response = self.client_socket.send_request(request)

            if success:
                if isinstance(response, dict) and response.get("success", False):
                    self.add_message(message, is_own=True)
                    self.message_input.clear()
                else:
                    QMessageBox.warning(self, "Lỗi", response.get("message", "Không gửi được tin nhắn."))
            else:
                QMessageBox.critical(self, "Lỗi kết nối", str(response))

    def handle_logout(self):
        if self.client_socket.connected:
            request = {"action": "logout", "user_id": self.user_id}
            success, response = self.client_socket.send_request(request)
            if success and isinstance(response, dict) and response.get("success", False):
                QMessageBox.information(self, "Thành công", response["message"])
            else:
                QMessageBox.warning(self, "Lỗi", response.get("message", "Không thể đăng xuất.") if isinstance(response, dict) else str(response))
            self.client_socket.close()
        self.close()
