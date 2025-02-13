from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
from database.db_config import get_db_connection, close_db_connection
from monitoring.prometheus_metrics import ORDER_COUNT, CART_OPERATIONS, track_order
import logging

logger = logging.getLogger(__name__)
order_bp = Blueprint('orders', __name__)

@order_bp.route('/orders', methods=['OPTIONS'])
@cross_origin(supports_credentials=True)
def handle_options():
    return '', 204

@order_bp.route('/orders', methods=['POST'])
@cross_origin(supports_credentials=True)
@track_order  # Add the metrics decorator
def create_order():
    connection = None
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"message": "User not authenticated"}), 401

        data = request.get_json()
        if not data or 'items' not in data:
            return jsonify({"message": "Invalid request data"}), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Calculate total and store current prices
        total_amount = 0
        order_items = []
        for item in data['items']:
            cursor.execute("SELECT price FROM products WHERE id = %s", (item['product_id'],))
            product = cursor.fetchone()
            if product:
                price = float(product['price'])
                quantity = item['quantity']
                total_amount += price * quantity
                order_items.append({
                    'product_id': item['product_id'],
                    'quantity': quantity,
                    'price_at_time': price
                })

        cursor.execute(
            "INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, %s)",
            (user_id, total_amount, 'pending')
        )
        order_id = cursor.lastrowid

        for item in order_items:
            cursor.execute(
                """INSERT INTO order_items
                    (order_id, product_id, quantity, price_at_time)
                    VALUES (%s, %s, %s, %s)""",
                (order_id, item['product_id'], item['quantity'], item['price_at_time'])
            )

        # Clear cart after successful order
        cursor.execute("DELETE FROM cart_items WHERE user_id = %s", (user_id,))
        CART_OPERATIONS.labels(operation='checkout').inc()  # Track cart checkout

        connection.commit()

        # Increment successful order count
        ORDER_COUNT.labels(status='success').inc()

        return jsonify({
            "message": "Order created",
            "order_id": order_id,
            "total_amount": total_amount
        }), 201

    except Exception as e:
        logger.error(f"Order creation failed: {str(e)}")
        if connection:
            connection.rollback()
        
        # Increment failed order count
        ORDER_COUNT.labels(status='failed').inc()
        
        return jsonify({"message": str(e)}), 500
    finally:
        if connection:
            close_db_connection(connection)


@order_bp.route('/orders', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_user_orders():
    connection = None
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"message": "User not authenticated"}), 401

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get orders with their items
        cursor.execute("""
            SELECT o.*, 
                   oi.product_id,
                   oi.quantity,
                   oi.price_at_time,
                   p.name as product_name
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE o.user_id = %s
            ORDER BY o.created_at DESC
        """, (user_id,))

        orders_data = cursor.fetchall()

        # Process and format orders
        orders = {}
        for row in orders_data:
            order_id = row['id']
            if order_id not in orders:
                orders[order_id] = {
                    'id': order_id,
                    'total_amount': float(row['total_amount']),
                    'status': row['status'],
                    'created_at': row['created_at'].isoformat(),
                    'items': []
                }
            
            if row['product_id']:  # Check if there are items
                orders[order_id]['items'].append({
                    'product_id': row['product_id'],
                    'product_name': row['product_name'],
                    'quantity': row['quantity'],
                    'price_at_time': float(row['price_at_time'])
                })

        return jsonify(list(orders.values())), 200

    except Exception as e:
        logger.error(f"Failed to fetch orders: {str(e)}")
        return jsonify({"message": str(e)}), 500
    finally:
        if connection:
            close_db_connection(connection)