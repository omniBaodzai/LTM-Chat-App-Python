import mysql.connector
from mysql.connector import Error
from server.database.db_connection import create_connection, close_connection

def register_user(username, password, email, phone):
    connection = create_connection()
    if not connection:
        return False, "Database connection failed"
    
    try:
        cursor = connection.cursor()
        query = """
        INSERT INTO users (username, password, email, phone, online_status)
        VALUES (%s, %s, %s, %s, 'offline')
        """
        cursor.execute(query, (username, password, email, phone))
        connection.commit()
        return True, "User registered successfully"
    except Error as e:
        if e.errno == 1062:
            return False, "Email or phone already exists"
        return False, f"Error registering user: {e}"
    finally:
        cursor.close()
        close_connection(connection)

def login_user(identifier, password):
    connection = create_connection()
    if not connection:
        return False, None, "Database connection failed"
    
    try:
        cursor = connection.cursor()
        query = """
        SELECT user_id, username FROM users
        WHERE (email = %s OR phone = %s) AND password = %s
        """
        cursor.execute(query, (identifier, identifier, password))
        user = cursor.fetchone()
        
        if user:
            update_query = """
            UPDATE users SET online_status = 'online', last_seen = CURRENT_TIMESTAMP
            WHERE user_id = %s
            """
            cursor.execute(update_query, (user[0],))
            connection.commit()
            return True, user[0], "Login successful"
        else:
            return False, None, "Invalid email/phone or password"
    except Error as e:
        return False, None, f"Error logging in: {e}"
    finally:
        cursor.close()
        close_connection(connection)

def logout_user(user_id):
    connection = create_connection()
    if not connection:
        return False, "Database connection failed"
    
    try:
        cursor = connection.cursor()
        query = """
        UPDATE users SET online_status = 'offline', last_seen = CURRENT_TIMESTAMP
        WHERE user_id = %s
        """
        cursor.execute(query, (user_id,))
        connection.commit()
        return True, "Logout successful"
    except Error as e:
        return False, f"Error logging out: {e}"
    finally:
        cursor.close()
        close_connection(connection)