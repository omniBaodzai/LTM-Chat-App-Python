# No changes to this file's content from the previous response.
# Ensure this file is located at D:\LTM\ck\1\chat_test\client\config.py

import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="uyen893605",
        database="chat_app1",
        autocommit=True
    )