from database.db_config import get_db_connection, close_db_connection
import bcrypt  # For password hashing
import logging

logger = logging.getLogger(__name__)

class User:
    def __init__(self, user_id, username, password, is_admin=False):
        self.user_id = user_id
        self.username = username
        self.password = password  # This should store the hashed password
        self.is_admin = is_admin

    def to_dict(self):
        """Convert User object to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "is_admin": self.is_admin
        }

    @staticmethod
    def get_user_by_id(user_id):
        """
        Fetch a user by their ID from the database.
        Returns:
            User object if found, else None.
        """
        connection = get_db_connection()
        if not connection:
            raise Exception("Database connection failed")
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                return None
            return User(user['id'], user['username'], user['password'], user.get('is_admin', False))
        finally:
            close_db_connection(connection)

    @staticmethod
    def get_user_by_username(username):
        """
        Fetch a user by their username from the database.
        Returns:
            User object if found, else None.
        """
        connection = get_db_connection()
        if not connection:
            raise Exception("Database connection failed")
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if not user:
                return None
            return User(user['id'], user['username'], user['password'], user.get('is_admin', False))
        finally:
            close_db_connection(connection)

    @staticmethod
    def create_user(username, password, is_admin=False):
        """
        Insert a new user into the database with a hashed password.
        Args:
            username (str): The username of the user.
            password (str): The plain-text password to hash and store.
            is_admin (bool): Whether the user has admin privileges.
        Returns:
            User: The created User object.
        """
        connection = get_db_connection()
        if not connection:
            raise Exception("Database connection failed")
        try:
            # Hash the password before storing
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)", 
                (username, hashed_password, is_admin)
            )
            connection.commit()
            user_id = cursor.lastrowid
            return User(user_id, username, hashed_password, is_admin)
        except Exception as e:
            connection.rollback()
            raise Exception(f"Error creating user: {e}")
        finally:
            close_db_connection(connection)

    @staticmethod
    def authenticate(username, password):
        """
        Authenticate a user with their username and password.
        Args:
            username (str): The username of the user.
            password (str): The plain-text password to validate.
        Returns:
            User: The authenticated User object if successful, else None.
        """
        user = User.get_user_by_username(username)
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return user
        return None

    @staticmethod
    def get_all_users():
        """
        Fetch all users from the database.
        Returns:
            list: List of User objects.
        """
        connection = get_db_connection()
        if not connection:
            raise Exception("Database connection failed")
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            return [User(
                user['id'], 
                user['username'], 
                user['password'], 
                user.get('is_admin', False)
            ) for user in users]
        finally:
            close_db_connection(connection)

    @staticmethod
    def update_password(user_id, new_password):
        """
        Update a user's password in the database.
        Args:
            user_id (int): The ID of the user.
            new_password (str): The new password (already hashed).
        Returns:
            bool: True if successful, False otherwise.
        """
        connection = get_db_connection()
        if not connection:
            raise Exception("Database connection failed")
        try:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE users SET password = %s WHERE id = %s",
                (new_password, user_id)
            )
            connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            logger.error(f"Error updating password for user {user_id}: {e}")
            raise Exception(f"Error updating password: {e}")
        finally:
            close_db_connection(connection)

    @staticmethod
    def set_admin_status(user_id, is_admin):
        """
        Set or remove admin privileges for a user.
        Args:
            user_id (int): The ID of the user.
            is_admin (bool): Whether to grant or revoke admin privileges.
        Returns:
            bool: True if successful, False otherwise.
        """
        connection = get_db_connection()
        if not connection:
            raise Exception("Database connection failed")
        try:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE users SET is_admin = %s WHERE id = %s",
                (is_admin, user_id)
            )
            connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            logger.error(f"Error updating admin status for user {user_id}: {e}")
            raise Exception(f"Error updating admin status: {e}")
        finally:
            close_db_connection(connection)