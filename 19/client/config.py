import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="uyen893605",
        database="chat_app1",
        autocommit=True
    )