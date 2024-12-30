from flask import Blueprint, jsonify, request
from models.product import Product  # Ensure models.product exists and is imported correctly.

# Initialize Blueprint
product_bp = Blueprint('products', __name__)

# Route to get all products
@product_bp.route('/products', methods=['GET'])
def get_all_products():
    """
    Fetch all products from the database and return them as JSON.
    """
    try:
        products = Product.get_all_products()
        # Add debug logging
        print(f"Fetched products: {[product.to_dict() for product in products]}")
        return jsonify([product.to_dict() for product in products]), 200
    except Exception as e:
        print(f"Error fetching products: {str(e)}")  # Debug log
        return jsonify({"message": "Failed to fetch products", "error": str(e)}), 500

# Route to get a specific product by ID
@product_bp.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """
    Fetch a single product by ID and return it as JSON.
    Args:
        product_id (int): ID of the product.
    Returns:
        - 200: Product details.
        - 404: Product not found.
        - 500: Server error.
    """
    try:
        product = Product.get_product_by_id(product_id)
        if product:
            return jsonify(product.to_dict()), 200
        return jsonify({"message": "Product not found"}), 404
    except Exception as e:
        return jsonify({"message": "Failed to fetch product", "error": str(e)}), 500

# Route to create a new product
@product_bp.route('/api/products', methods=['POST'])
def create_product():
    """
    Create a new product in the database.
    Expects JSON with 'name' and 'price'.
    Returns:
        - 201: Product created successfully.
        - 400: Bad request (missing fields).
        - 500: Server error.
    """
    data = request.json
    name = data.get('name')
    price = data.get('price')

    if not name or not price:
        return jsonify({"message": "Both 'name' and 'price' are required"}), 400

    try:
        product = Product.create_product(name, price)
        return jsonify({"message": "Product created successfully", "product": product.to_dict()}), 201
    except Exception as e:
        return jsonify({"message": "Failed to create product", "error": str(e)}), 500

# Route to update an existing product
@product_bp.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    Update an existing product in the database.
    Expects JSON with optional 'name' or 'price'.
    Returns:
        - 200: Product updated successfully.
        - 400: Bad request (no fields provided).
        - 404: Product not found.
        - 500: Server error.
    """
    data = request.json
    name = data.get('name')
    price = data.get('price')

    if not name and not price:
        return jsonify({"message": "At least one field ('name' or 'price') is required"}), 400

    try:
        updated = Product.update_product(product_id, name, price)
        if updated:
            return jsonify({"message": "Product updated successfully"}), 200
        return jsonify({"message": "Product not found"}), 404
    except Exception as e:
        return jsonify({"message": "Failed to update product", "error": str(e)}), 500

# Route to delete a product
@product_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """
    Delete a product from the database.
    Args:
        product_id (int): ID of the product to delete.
    Returns:
        - 200: Product deleted successfully.
        - 404: Product not found.
        - 500: Server error.
    """
    try:
        deleted = Product.delete_product(product_id)
        if deleted:
            return jsonify({"message": "Product deleted successfully"}), 200
        return jsonify({"message": "Product not found"}), 404
    except Exception as e:
        return jsonify({"message": "Failed to delete product", "error": str(e)}), 500
