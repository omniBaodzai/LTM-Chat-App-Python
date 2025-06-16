import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QStackedWidget
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QIcon, QPixmap
from client.network.client_socket import ClientSocket
from client.gui.main_window import MainWindow

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatApp")
        self.setFixedSize(1200, 1300)
        self.client_socket = ClientSocket()
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        central_widget.setStyleSheet("background-color: #f0f4f8;")

        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("client/gui/assets/images/logo.png").scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(logo_label)

        # Title
        title_label = QLabel("ChatApp")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px 0;")
        main_layout.addWidget(title_label)

        # Stacked widget for login/register
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("border-radius: 10px; background-color: white; padding: 20px;")
        main_layout.addWidget(self.stacked_widget)

        # Login page
        self.login_page = QWidget()
        login_layout = QVBoxLayout()
        self.login_page.setLayout(login_layout)

        self.login_identifier_input = QLineEdit()
        self.add_input_field(login_layout, "Email hoặc SĐT", "client/gui/assets/icons/email.png", self.login_identifier_input)
        self.login_password_input = QLineEdit()
        self.add_input_field(login_layout, "Mật khẩu", "client/gui/assets/icons/password.png", self.login_password_input, is_password=True)

        login_button = self.create_button("Đăng nhập", "client/gui/assets/icons/login.png", "#3498db")
        login_button.clicked.connect(self.handle_login)
        login_layout.addWidget(login_button)

        register_link = self.create_link("Chưa có tài khoản? Đăng ký ngay!")
        register_link.mousePressEvent = lambda e: self.switch_to_register()
        login_layout.addWidget(register_link)

        self.stacked_widget.addWidget(self.login_page)

        # Register page
        self.register_page = QWidget()
        register_layout = QVBoxLayout()
        self.register_page.setLayout(register_layout)

        self.register_email_input = QLineEdit()
        self.add_input_field(register_layout, "Email", "client/gui/assets/icons/email.png", self.register_email_input)
        self.register_phone_input = QLineEdit()
        self.add_input_field(register_layout, "Số điện thoại", "client/gui/assets/icons/phone.png", self.register_phone_input)
        self.register_password_input = QLineEdit()
        self.add_input_field(register_layout, "Mật khẩu", "client/gui/assets/icons/password.png", self.register_password_input, is_password=True)
        self.register_re_password_input = QLineEdit()
        self.add_input_field(register_layout, "Xác nhận mật khẩu", "client/gui/assets/icons/re_password.png", self.register_re_password_input, is_password=True)

        next_button = self.create_button("Tiếp tục", "client/gui/assets/icons/register.png", "#2ecc71")
        next_button.clicked.connect(self.handle_register_step1)
        register_layout.addWidget(next_button)

        login_link = self.create_link("Đã có tài khoản? Đăng nhập ngay!")
        login_link.mousePressEvent = lambda e: self.switch_to_login()
        register_layout.addWidget(login_link)

        self.stacked_widget.addWidget(self.register_page)

        # Username page
        self.username_page = QWidget()
        username_layout = QVBoxLayout()
        self.username_page.setLayout(username_layout)

        username_label = QLabel("Chọn tên người dùng")
        username_label.setFont(QFont("Arial", 16))
        username_label.setAlignment(Qt.AlignCenter)
        username_layout.addWidget(username_label)

        self.username_input = QLineEdit()
        self.add_input_field(username_layout, "Tên người dùng", "client/gui/assets/icons/user.png", self.username_input)

        finish_button = self.create_button("Hoàn tất", "client/gui/assets/icons/register.png", "#2ecc71")
        finish_button.clicked.connect(self.handle_register_step2)
        username_layout.addWidget(finish_button)

        self.stacked_widget.addWidget(self.username_page)

        main_layout.addStretch()

    def add_input_field(self, layout, placeholder, icon_path, line_edit, is_password=False):
        input_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(QIcon(icon_path).pixmap(24, 24))
        input_layout.addWidget(icon_label)

        line_edit.setPlaceholderText(placeholder)
        line_edit.setFont(QFont("Arial", 12))
        if is_password:
            line_edit.setEchoMode(QLineEdit.Password)
        line_edit.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: #f5f6fa;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
                background-color: white;
            }
        """)
        input_layout.addWidget(line_edit)
        layout.addLayout(input_layout)

    def create_button(self, text, icon_path, color):
        button = QPushButton(text)
        button.setFont(QFont("Arial", 12))
        button.setIcon(QIcon(icon_path))
        hover_color = self.lighten_color(color)
        pressed_color = self.darken_color(color)
        button.setStyleSheet(
            f"QPushButton {{"
            f"background-color: {color};"
            f"color: white;"
            f"padding: 10px;"
            f"border-radius: 5px;"
            f"margin: 5px;"
            f"}}"
            f"QPushButton:hover {{"
            f"background-color: {hover_color};"
            f"}}"
            f"QPushButton:pressed {{"
            f"background-color: {pressed_color};"
            f"}}"
        )
        return button

    def create_link(self, text):
        link = QLabel(text)
        link.setFont(QFont("Arial", 10))
        link.setStyleSheet(
            "color: #3498db;"
            "margin-top: 10px;"
        )
        link.setAlignment(Qt.AlignCenter)
        link.setCursor(Qt.PointingHandCursor)
        return link

    def lighten_color(self, hex_color):
        color = int(hex_color[1:], 16)
        r = min(255, ((color >> 16) & 255) + 30)
        g = min(255, ((color >> 8) & 255) + 30)
        b = min(255, (color & 255) + 30)
        return f"#{r:02x}{g:02x}{b:02x}"

    def darken_color(self, hex_color):
        color = int(hex_color[1:], 16)
        r = max(0, ((color >> 16) & 255) - 30)
        g = max(0, ((color >> 8) & 255) - 30)
        b = max(0, (color & 255) - 30)
        return f"#{r:02x}{g:02x}{b:02x}"

    def switch_to_register(self):
        anim = QPropertyAnimation(self.stacked_widget, b"pos")
        anim.setDuration(500)
        anim.setStartValue(self.stacked_widget.pos())
        anim.setEndValue(self.stacked_widget.pos())
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self.stacked_widget.setCurrentWidget(self.register_page)

    def switch_to_login(self):
        anim = QPropertyAnimation(self.stacked_widget, b"pos")
        anim.setDuration(500)
        anim.setStartValue(self.stacked_widget.pos())
        anim.setEndValue(self.stacked_widget.pos())
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self.stacked_widget.setCurrentWidget(self.login_page)

    def switch_to_username(self):
        self.stacked_widget.setCurrentWidget(self.username_page)

    def handle_login(self):
        identifier = self.login_identifier_input.text().strip()
        password = self.login_password_input.text().strip()
        
        if not identifier or not password:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin!")
            return
        
        if not self.client_socket.connected:
            success, message = self.client_socket.connect()
            if not success:
                QMessageBox.critical(self, "Lỗi", message)
                return
        
        request = {"action": "login", "identifier": identifier, "password": password}
        success, response = self.client_socket.send_request(request)
        
        if success and response["success"]:
            QMessageBox.information(self, "Thành công", response["message"])
            self.main_window = MainWindow(response["user_id"], self.client_socket)
            self.main_window.show()
            self.close()
        else:
            QMessageBox.warning(self, "Lỗi", response["message"] if success else response)

    def handle_register_step1(self):
        email = self.register_email_input.text().strip()
        phone = self.register_phone_input.text().strip()
        password = self.register_password_input.text().strip()
        re_password = self.register_re_password_input.text().strip()
        
        if not all([email, phone, password, re_password]):
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin!")
            return
        
        if password != re_password:
            QMessageBox.warning(self, "Lỗi", "Mật khẩu xác nhận không khớp!")
            return
        
        self.register_data = {"email": email, "phone": phone, "password": password}
        self.switch_to_username()

    def handle_register_step2(self):
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên người dùng!")
            return
        
        if not self.client_socket.connected:
            success, message = self.client_socket.connect()
            if not success:
                QMessageBox.critical(self, "Lỗi", message)
            return
        
        request = {
            "action": "register",
            "username": username,
            "password": self.register_data["password"],
            "email": self.register_data["email"],
            "phone": self.register_data["phone"]
        }
        success, response = self.client_socket.send_request(request)
        
        if success and response["success"]:
            QMessageBox.information(self, "Thành công", response["message"])
            self.switch_to_login()
        else:
            QMessageBox.warning(self, "Lỗi", response["message"] if success else response)





def main():
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()