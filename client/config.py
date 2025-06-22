import mysql.connector

def get_db_connection():
    return mysql.connector.connect(

        host="localhost",
         port=3307,
        user="root",
        password="bangbang",
        database="chat_app1",
        autocommit=True
    )
