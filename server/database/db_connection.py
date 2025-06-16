import mysql.connector
from mysql.connector import Error
from server.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

def create_connection():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
           port=DB_PORT


        )
        if connection.is_connected():
            print("[✓] Đã kết nối MySQL thành công!")
            return connection
    except Error as e:
        print("[X] Lỗi kết nối MySQL:", e)
        return None

def close_connection(connection):
    if connection and connection.is_connected():
        connection.close()