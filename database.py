import mysql.connector
from config import *

def save_message(room_id, sender, message):
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    query = "INSERT INTO messages (room_id, sender, message) VALUES (%s, %s, %s)"
    cursor.execute(query, (room_id, sender, message))
    conn.commit()
    conn.close()
