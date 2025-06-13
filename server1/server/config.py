import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",     # Hoặc IP MySQL server
        user="root",          # Tài khoản MySQL
        password="",          # Mật khẩu (nếu có)
        database="chat_app1",    # Tên CSDL
        autocommit=True       # Tự động lưu
    )
