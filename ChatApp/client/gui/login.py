import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from client.network.client_socket import ClientSocket

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatApp - Đăng nhập/Đăng ký")
        self.setFixedSize(400, 300)
        self.client_socket = ClientSocket()
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        title_label = QLabel("ChatApp")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        main_layout.addWidget(title_label)
        
        username_label = QLabel("Username:")
        username_label.setFont(QFont("Arial", 12))
        self.username_input = QLineEdit()
        self.username_input.setFont(QFont("Arial", 12))
        self.username_input.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 5px;")
        main_layout.addWidget(username_label)
        main_layout.addWidget(self.username_input)
        
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Arial", 12))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFont(QFont("Arial", 12))
        self.password_input.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 5px;")
        main_layout.addWidget(password_label)
        main_layout.addWidget(self.password_input)
        
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)
        
        login_button = QPushButton("Đăng nhập")
        login_button.setFont(QFont("Arial", 12))
        login_button.setStyleSheet("""
            background-color: #3498db; 
            color: white; 
            padding: 10px; 
            border-radius: 5px;
            margin: 5px;
        """)
        login_button.clicked.connect(self.handle_login)
        button_layout.addWidget(login_button)
        
        register_button = QPushButton("Đăng ký")
        register_button.setFont(QFont("Arial", 12))
        register_button.setStyleSheet("""
            background-color: #2ecc71; 
            color: white; 
            padding: 10px; 
            border-radius: 5px;
            margin: 5px;
        """)
        register_button.clicked.connect(self.handle_register)
        button_layout.addWidget(register_button)
        
        main_layout.addStretch()

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập username và password!")
            return
        
        if not self.client_socket.connected:
            success, message = self.client_socket.connect()
            if not success:
                QMessageBox.critical(self, "Lỗi", message)
                return
        
        request = {"action": "login", "username": username, "password": password}
        success, response = self.client_socket.send_request(request)
        
        if success and response["success"]:
            QMessageBox.information(self, "Thành công", response["message"])
            # TODO: Chuyển sang giao diện chính (main_window.py)
        else:
            QMessageBox.warning(self, "Lỗi", response["message"] if success else response)

    def handle_register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập username và password!")
            return
        
        if not self.client_socket.connected:
            success, message = self.client_socket.connect()
            if not success:
                QMessageBox.critical(self, "Lỗi", message)
                return
        
        request = {"action": "register", "username": username, "password": password}
        success, response = self.client_socket.send_request(request)
        
        if success and response["success"]:
            QMessageBox.information(self, "Thành công", response["message"])
        else:
            QMessageBox.warning(self, "Lỗi", response["message"] if success else response)

    def closeEvent(self, event):
        self.client_socket.close()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()