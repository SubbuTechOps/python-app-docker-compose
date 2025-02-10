from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
from database.db_config import get_db_connection, close_db_connection
import logging

logger = logging.getLogger(__name__)
order_bp = Blueprint('orders', __name__)

@order_bp.route('/orders', methods=['OPTIONS'])
@cross_origin(supports_credentials=True)
def handle_options():
    return '', 204

@order_bp.route('/orders', methods=['POST'])
@cross_origin(supports_credentials=True)
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

        cursor.execute("DELETE FROM cart_items WHERE user_id = %s", (user_id,))
        
        connection.commit()
        return jsonify({
            "message": "Order created",
            "order_id": order_id,
            "total_amount": total_amount
        }), 201

    except Exception as e:
        logger.error(f"Order creation failed: {str(e)}")
        if connection:
            connection.rollback()
        return jsonify({"message": str(e)}), 500
    finally:
        if connection:
            close_db_connection(connection)