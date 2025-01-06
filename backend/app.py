import os
import time
import logging
import sys
from datetime import timedelta
from flask import Flask, jsonify, send_from_directory, session, request
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
from functools import wraps


# Configure logging
log_format = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.DEBUG, format=log_format)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Track uptime for health check
start_time = time.time()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"Session state in decorator: {session}")
        if 'user_id' not in session:
            logger.warning("User not authenticated, redirecting to login")
            return jsonify({"message": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def create_app():
    app = Flask(__name__)

    # Enhanced session configuration
    app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
    session_file_dir = os.getenv('SESSION_FILE_DIR', '/tmp/flask_sessions')
    os.makedirs(session_file_dir, exist_ok=True)

    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'default_secret_key'),
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=session_file_dir,
        SESSION_PERMANENT=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=1),
        SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax'
    )
    Session(app)

    # Updated CORS configuration
    CORS(app,
         resources={r"/*": {
             "origins": ["*"],  # Allow all origins in development
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Type", "Authorization"]
         }},
         supports_credentials=True)

    # Debug middleware
    @app.before_request
    def before_request():
        logger.debug(f"Incoming request: {request.method} {request.path}")
        logger.debug(f"Session contents: {session}")
        logger.debug(f"Request cookies: {request.cookies}")

    @app.after_request
    def after_request(response):
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response cookies: {response.headers.get('Set-Cookie')}")
        return response

    # Frontend paths handling
    frontend_paths = [
        "/app/frontend",  # Docker container path
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend")),  # Local development path
    ]

    def get_frontend_path():
        for path in frontend_paths:
            if os.path.exists(path):
                logger.info(f"Using frontend path: {path}")
                return path
        logger.warning("No frontend directory found, API-only mode")
        return None

    frontend_path = get_frontend_path()

    @app.route("/<path:filename>")
    def serve_static(filename):
        logger.debug(f"Serving static file: {filename}")
        if frontend_path:
            file_path = os.path.join(frontend_path, filename)
            if os.path.isfile(file_path):
                return send_from_directory(frontend_path, filename)
        return jsonify({"message": "File not found"}), 404

    @app.route("/")
    def serve_index():
        logger.debug("Serving index.html")
        if frontend_path and os.path.isfile(os.path.join(frontend_path, "index.html")):
            return send_from_directory(frontend_path, "index.html")
        return jsonify({"message": "API Server Running"}), 200

    @app.route("/api/health", methods=["GET"])
    def health_check():
        uptime = time.time() - start_time
        session_data = {
            "username": session.get("username", "Not set"),
            "user_id": session.get("user_id", "Not set")
        }
        logger.debug(f"Health check - Session data: {session_data}")
        return jsonify({
            "status": "healthy",
            "uptime": f"{uptime:.2f} seconds",
            "session_active": "username" in session,
            "session_data": session_data,
            "frontend_path": frontend_path
        }), 200

    # Register Blueprints
    from routes.auth_routes import auth_bp
    from routes.product_routes import product_bp
    from routes.cart_routes import cart_bp
    from routes.order_routes import order_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(product_bp, url_prefix="/api")
    app.register_blueprint(cart_bp, url_prefix="/api")
    app.register_blueprint(order_bp, url_prefix="/api/orders")

    # Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"Resource not found: {request.path}")
        return jsonify({"message": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"message": "Internal server error"}), 500

    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"Bad request: {error}")
        return jsonify({"message": "Bad request"}), 400

    return app

if __name__ == "__main__":
    app = create_app()
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    logger.info(f"Starting Flask app in {'debug' if debug_mode else 'production'} mode")
    app.run(debug=debug_mode, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))