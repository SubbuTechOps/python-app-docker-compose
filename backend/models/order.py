from database.db_config import get_db_connection, close_db_connection
from models.product import Product
import logging

logger = logging.getLogger(__name__)

class Order:
    def __init__(self, order_id, user_id, total_amount, status='pending'):
        self.order_id = order_id
        self.user_id = user_id
        self.total_amount = total_amount
        self.status = status
        self.items = []

    def to_dict(self):
        """Convert Order object to dictionary for JSON serialization."""
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "total_amount": float(self.total_amount),
            "status": self.status,
            "items": [item.to_dict() for item in self.items if item]
        }

    @staticmethod
    def create_order(user_id, items):
        """Create a new order with calculated total."""
        connection = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # Calculate total
            total_amount = 0
            for item in items:
                cursor.execute(
                    "SELECT price FROM products WHERE id = %s",
                    (item["product_id"],)
                )
                product = cursor.fetchone()
                if product:
                    total_amount += float(product["price"]) * item["quantity"]

            # Create order
            cursor.execute(
                """INSERT INTO orders (user_id, total_amount, status) 
                   VALUES (%s, %s, 'pending')""",
                (user_id, total_amount)
            )
            order_id = cursor.lastrowid

            # Add items
            for item in items:
                cursor.execute(
                    """INSERT INTO order_items 
                       (order_id, product_id, quantity, price_at_time) 
                       SELECT %s, %s, %s, price
                       FROM products WHERE id = %s""",
                    (order_id, item["product_id"], item["quantity"], 
                     item["product_id"])
                )

            connection.commit()
            logger.info(f"Order {order_id} created for user {user_id}")
            
            return Order(order_id, user_id, total_amount)

        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                close_db_connection(connection)

    @staticmethod
    def get_order_by_id(order_id):
        """Get order details by ID."""
        connection = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """SELECT o.*, oi.product_id, oi.quantity, 
                          oi.price_at_time, p.name
                   FROM orders o
                   JOIN order_items oi ON o.id = oi.order_id
                   JOIN products p ON oi.product_id = p.id
                   WHERE o.id = %s""",
                (order_id,)
            )
            rows = cursor.fetchall()

            if not rows:
                return None

            order = Order(
                order_id=rows[0]["id"],
                user_id=rows[0]["user_id"],
                total_amount=float(rows[0]["total_amount"]),
                status=rows[0]["status"]
            )

            for row in rows:
                product = Product(
                    product_id=row["product_id"],
                    name=row["name"],
                    price=float(row["price_at_time"])
                )
                order.items.append(product)

            return order

        except Exception as e:
            logger.error(f"Error getting order {order_id}: {str(e)}")
            return None
        finally:
            if connection:
                close_db_connection(connection)