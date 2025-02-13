from flask import Blueprint, request, jsonify, session
from database.db_config import get_db_connection, close_db_connection
from monitoring.prometheus_metrics import (
    CART_OPERATIONS,
    track_auth_metrics,
    record_request_metrics,
    track_user_action
)

cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/cart', methods=['GET'])
@track_auth_metrics
def get_cart():
    """
    Fetch all items in the cart for a given user.
    Uses session user_id instead of query parameter.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "User not authenticated"}), 401

    connection = get_db_connection()
    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT c.product_id, c.quantity, p.name, p.price
            FROM cart_items c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """
        cursor.execute(query, (user_id,))
        cart_items = cursor.fetchall()

        if not cart_items:
            return jsonify({"message": "Cart is empty", "cart_items": []}), 200

        response = [
            {
                "product_id": item["product_id"],
                "name": item["name"],
                "price": float(item["price"]),
                "quantity": item["quantity"],
                "total_price": round(item["quantity"] * float(item["price"]), 2),
            }
            for item in cart_items
        ]

        return jsonify({"message": "Cart items retrieved successfully", "cart_items": response}), 200
    except Exception as e:
        return jsonify({"message": "Failed to retrieve cart items", "error": str(e)}), 500
    finally:
        close_db_connection(connection)

@cart_bp.route('/cart', methods=['POST'])
@track_user_action('cart_add')
def add_to_cart():
    """
    Add a product to the cart for the logged-in user.
    Expects JSON payload: { product_id, quantity }.
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"message": "User not authenticated"}), 401

        data = request.json
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        if not product_id:
            return jsonify({"message": "'product_id' is required"}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({"message": "Database connection failed"}), 500

        cursor = connection.cursor(dictionary=True)
        check_query = """
            SELECT quantity FROM cart_items WHERE user_id = %s AND product_id = %s
        """
        cursor.execute(check_query, (user_id, product_id))
        existing_item = cursor.fetchone()

        if existing_item:
            new_quantity = existing_item["quantity"] + quantity
            update_query = """
                UPDATE cart_items SET quantity = %s WHERE user_id = %s AND product_id = %s
            """
            cursor.execute(update_query, (new_quantity, user_id, product_id))
        else:
            insert_query = """
                INSERT INTO cart_items (user_id, product_id, quantity) VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (user_id, product_id, quantity))

        connection.commit()
        CART_OPERATIONS.labels(operation='add').inc()
        return jsonify({"message": "Product added to cart successfully"}), 201
    except Exception as e:
        return jsonify({"message": "Failed to add product to cart", "error": str(e)}), 500
    finally:
        close_db_connection(connection)

@cart_bp.route('/cart', methods=['DELETE'])
@track_user_action('cart_remove')
def remove_from_cart():
    """
    Remove a product from the cart for the logged-in user.
    Expects JSON payload: { product_id }.
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"message": "User not authenticated"}), 401

        data = request.json
        product_id = data.get('product_id')

        if not product_id:
            return jsonify({"message": "'product_id' is required"}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({"message": "Database connection failed"}), 500

        cursor = connection.cursor()
        delete_query = """
            DELETE FROM cart_items WHERE user_id = %s AND product_id = %s
        """
        cursor.execute(delete_query, (user_id, product_id))

        if cursor.rowcount == 0:
            return jsonify({"message": "Product not found in cart"}), 404

        connection.commit()
        CART_OPERATIONS.labels(operation='remove').inc()
        return jsonify({"message": "Product removed from cart successfully"}), 200
    except Exception as e:
        return jsonify({"message": "Failed to remove product from cart", "error": str(e)}), 500
    finally:
        close_db_connection(connection)