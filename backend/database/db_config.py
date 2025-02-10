import mysql.connector
from mysql.connector import Error, pooling
from dotenv import load_dotenv
import os
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Required environment variables
REQUIRED_ENV_VARS = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]

# Validate environment variables
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        raise EnvironmentError(f"🚨 Environment variable '{var}' is not set! Please check your configuration.")

# Connection pool configuration
POOL_CONFIG = {
    "pool_name": "mypool",
    "pool_size": 5,
    "pool_reset_session": True
}

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "connect_timeout": 10  # ✅ Fixed duplicate issue
}

# Global connection pool
connection_pool = None
MAX_RETRIES = 5
RETRY_DELAY = 2

def create_connection_pool():
    """
    Create a connection pool for MySQL database.
    Returns:
        pool (MySQLConnectionPool): A connection pool if successful, None otherwise.
    """
    global connection_pool
    try:
        connection_pool = mysql.connector.pooling.MySQLConnectionPool(
            **DB_CONFIG,  # ✅ Fixed duplicate `connect_timeout`
            **POOL_CONFIG
        )
        logger.info(f"✅ Created MySQL connection pool for database '{DB_CONFIG['database']}'")
        return True
    except Error as e:
        logger.error(f"🚨 Error creating connection pool: {e}")
        return False

def initialize_pool():
    """
    Initialize the global connection pool with retries.
    """
    global connection_pool
    retries = 0

    while retries < MAX_RETRIES:
        if not connection_pool:
            logger.info(f"🔄 Attempting to initialize MySQL connection pool (Attempt {retries + 1}/{MAX_RETRIES})...")
            if create_connection_pool():
                return True

        retries += 1
        time.sleep(RETRY_DELAY)

    logger.error("🚨 Failed to initialize MySQL connection pool after all retries!")
    return False

def get_db_connection():
    """
    Get a connection from the pool with retry mechanism.
    Returns:
        connection (MySQLConnection): A connection object if successful, None otherwise.
    """
    global connection_pool
    retries = 0

    while retries < MAX_RETRIES:
        try:
            if not connection_pool and not initialize_pool():
                raise Error("Connection pool initialization failed")

            connection = connection_pool.get_connection()
            if connection.is_connected():
                logger.debug("✅ Successfully retrieved a connection from the pool")
                return connection
        except Error as e:
            retries += 1
            logger.warning(f"⚠️ Database connection attempt {retries}/{MAX_RETRIES} failed: {e}")
            time.sleep(RETRY_DELAY)
            if not connection_pool:
                initialize_pool()

    logger.error("🚨 Failed to get a database connection after all retries!")
    return None

def close_db_connection(connection):
    """
    Return the connection to the pool.
    Args:
        connection (MySQLConnection): The connection object to return to the pool.
    """
    try:
        if connection and connection.is_connected():
            connection.close()
            logger.debug("✅ Connection returned to the pool")
    except Error as e:
        logger.error(f"🚨 Error closing connection: {e}")

def check_db_connection():
    """
    Check if database is accessible.
    Returns:
        bool: True if database is accessible, False otherwise.
    """
    connection = get_db_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return True
    except Error as e:
        logger.error(f"🚨 Database check failed: {e}")
        return False
    finally:
        close_db_connection(connection)
