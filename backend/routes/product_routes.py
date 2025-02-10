from flask import Blueprint, jsonify, request
from models.product import Product
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Blueprint
product_bp = Blueprint('products', __name__)

@product_bp.route('/products', methods=['GET'])
def get_all_products():
    """
    Fetch all products from the database and return them as JSON.
    Returns:
        - 200: List of products
        - 500: Server error
    """
    try:
        logger.debug("Attempting to fetch all products")
        products = Product.get_all_products()
        logger.info(f"Successfully fetched {len(products)} products")
        return jsonify([product.to_dict() for product in products]), 200
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        return jsonify({
            "message": "Failed to fetch products", 
            "error": str(e)
        }), 500

@product_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """
    Fetch a single product by ID and return it as JSON.
    Args:
        product_id (int): ID of the product
    Returns:
        - 200: Product details
        - 404: Product not found
        - 500: Server error
    """
    try:
        logger.debug(f"Attempting to fetch product with ID: {product_id}")
        product = Product.get_product_by_id(product_id)
        if product:
            logger.info(f"Successfully fetched product: {product.name}")
            return jsonify(product.to_dict()), 200
        logger.warning(f"Product with ID {product_id} not found")
        return jsonify({"message": "Product not found"}), 404
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {str(e)}")
        return jsonify({
            "message": "Failed to fetch product", 
            "error": str(e)
        }), 500

@product_bp.route('/products', methods=['POST'])
def create_product():
    """
    Create a new product in the database.
    Expects JSON with required fields: name, price
    Optional fields: description, category, stock
    Returns:
        - 201: Product created successfully
        - 400: Bad request (missing or invalid fields)
        - 500: Server error
    """
    try:
        data = request.get_json()
        if not data:
            logger.warning("No JSON data received in request")
            return jsonify({"message": "No data provided"}), 400

        # Required fields
        name = data.get('name')
        price = data.get('price')
        
        # Optional fields
        description = data.get('description')
        category = data.get('category')
        stock = data.get('stock', 0)

        if not name or not isinstance(price, (int, float)) or price <= 0:
            logger.warning(f"Invalid product data: name={name}, price={price}")
            return jsonify({
                "message": "Name is required and price must be a positive number"
            }), 400

        logger.debug(f"Creating product: {name} with price {price}")
        product = Product.create_product(name, price, description, category, stock)
        logger.info(f"Successfully created product: {product.name}")
        
        return jsonify({
            "message": "Product created successfully",
            "product": product.to_dict()
        }), 201
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        return jsonify({
            "message": "Failed to create product", 
            "error": str(e)
        }), 500

@product_bp.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    Update an existing product in the database.
    Args:
        product_id (int): ID of the product to update
    Expects JSON with at least one of: name, price, description, category, stock
    Returns:
        - 200: Product updated successfully
        - 400: Bad request (no fields to update or invalid values)
        - 404: Product not found
        - 500: Server error
    """
    try:
        data = request.get_json()
        if not data:
            logger.warning("No JSON data received in request")
            return jsonify({"message": "No data provided"}), 400

        # Get fields to update
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'price' in data:
            if not isinstance(data['price'], (int, float)) or data['price'] <= 0:
                logger.warning(f"Invalid price value: {data['price']}")
                return jsonify({"message": "Price must be a positive number"}), 400
            updates['price'] = data['price']
        if 'description' in data:
            updates['description'] = data['description']
        if 'category' in data:
            updates['category'] = data['category']
        if 'stock' in data:
            if not isinstance(data['stock'], int) or data['stock'] < 0:
                logger.warning(f"Invalid stock value: {data['stock']}")
                return jsonify({"message": "Stock must be a non-negative integer"}), 400
            updates['stock'] = data['stock']

        if not updates:
            logger.warning("No valid fields provided for update")
            return jsonify({
                "message": "At least one valid field (name, price, description, category, stock) is required"
            }), 400

        logger.debug(f"Updating product {product_id} with {updates}")
        updated = Product.update_product(product_id, **updates)
        
        if updated:
            logger.info(f"Successfully updated product {product_id}")
            return jsonify({"message": "Product updated successfully"}), 200
            
        logger.warning(f"Product {product_id} not found")
        return jsonify({"message": "Product not found"}), 404
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {str(e)}")
        return jsonify({
            "message": "Failed to update product", 
            "error": str(e)
        }), 500

@product_bp.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """
    Delete a product from the database.
    Args:
        product_id (int): ID of the product to delete
    Returns:
        - 200: Product deleted successfully
        - 404: Product not found
        - 500: Server error
    """
    try:
        logger.debug(f"Attempting to delete product {product_id}")
        deleted = Product.delete_product(product_id)
        
        if deleted:
            logger.info(f"Successfully deleted product {product_id}")
            return jsonify({"message": "Product deleted successfully"}), 200
            
        logger.warning(f"Product {product_id} not found")
        return jsonify({"message": "Product not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {str(e)}")
        return jsonify({
            "message": "Failed to delete product", 
            "error": str(e)
        }), 500

# Add CORS preflight handling
@product_bp.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({"message": "preflight"})
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 200