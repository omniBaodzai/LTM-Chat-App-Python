# server/test_db.py
from server.database.db_connection import create_connection

if __name__ == "__main__":
    conn = create_connection()
    if conn:
        print("[✓] Kết nối OK, bạn có thể thực hiện truy vấn.")
        conn.close()
    else:
        print("[X] Không thể kết nối CSDL.")
