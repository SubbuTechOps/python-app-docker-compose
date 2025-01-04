import bcrypt
from database.db_config import get_db_connection, close_db_connection
import logging

logger = logging.getLogger(__name__)

def update_password_hashes():
    """Utility function to update plain text passwords with bcrypt hashes"""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            raise Exception("Database connection failed")
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password FROM users")
        users = cursor.fetchall()
        
        updated_count = 0
        skipped_count = 0
        
        for user in users:
            if user['password'].startswith('$2b$'):
                logger.debug(f"Skipping already hashed password for user: {user['username']}")
                skipped_count += 1
                continue
            
            try:
                hashed = bcrypt.hashpw(user['password'].encode('utf-8'), bcrypt.gensalt())
                cursor.execute(
                    "UPDATE users SET password = %s WHERE id = %s",
                    (hashed.decode('utf-8'), user['id'])
                )
                logger.debug(f"Updated password for user: {user['username']}")
                updated_count += 1
            except Exception as e:
                logger.error(f"Error updating password for user {user['username']}: {e}")
                continue
        
        connection.commit()
        return {
            'success': True,
            'total_processed': len(users),
            'updated': updated_count,
            'skipped': skipped_count
        }
        
    except Exception as e:
        logger.error(f"Error in password update process: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            close_db_connection(connection)