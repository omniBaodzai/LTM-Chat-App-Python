import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
<<<<<<< HEAD
        host="localhost",
         port=3307,
=======
        host="127.0.0.1",
        port=3307,
>>>>>>> ca328396a3887525adce88c65d35a888066247c1
        user="root",
        password="bangbang",
        database="chat_app1",
        autocommit=True
<<<<<<< HEAD
    )
=======
    )
>>>>>>> ca328396a3887525adce88c65d35a888066247c1
