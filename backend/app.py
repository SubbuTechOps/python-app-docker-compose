import os
import time
import logging
from datetime import timedelta
from flask import Flask, jsonify, send_from_directory, session, request
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
from functools import wraps
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from monitoring.prometheus_metrics import REGISTRY, record_request_metrics
from monitoring.middleware import MonitoringMiddleware
from monitoring.health_routes import health_bp

# Configure logging
log_format = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.DEBUG, format=log_format)
logger = logging.getLogger(__name__)

load_dotenv()

start_time = time.time()
db_initialized = False
FRONTEND_PATH = os.getenv("FRONTEND_PATH", "/app/frontend")

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
    app = Flask(__name__, static_folder=FRONTEND_PATH, static_url_path="")
    app.healthy = False  # Initialize health status

    try:
        # Apply middleware stack with global registry
        app.wsgi_app = MonitoringMiddleware(
            DispatcherMiddleware(app.wsgi_app, {
                '/api/metrics': make_wsgi_app(REGISTRY)
            })
        )
        logger.info("✅ Monitoring middleware configured successfully")
    except Exception as e:
        logger.error(f"🚨 Error configuring monitoring middleware: {e}")

    # Session Configuration
    app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
    session_file_dir = os.getenv('SESSION_FILE_DIR', '/tmp/flask_sessions')
    os.makedirs(session_file_dir, exist_ok=True)

    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'default_secret_key'),
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=session_file_dir,
        SESSION_PERMANENT=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=1),
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        FRONTEND_PATH=FRONTEND_PATH
    )
    Session(app)

    # Updated CORS configuration
    CORS(app, 
         resources={r"/api/*": {"origins": "*"}},
         supports_credentials=True,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "Accept"],
         expose_headers=["Content-Type", "Authorization"])

    @app.before_request
    def log_request():
        # Skip logging for metrics endpoint to avoid noise
        if request.path != '/api/metrics':
            logger.info(f"🔍 Incoming request: {request.method} {request.path}")

    # Initialize Database
    try:
        from database.db_config import check_db_connection, initialize_pool

        logger.info("🔄 Initializing Database Connection Pool...")
        if not initialize_pool():
            logger.error("❌ Database connection pool initialization failed!")
            app.healthy = False
        else:
            logger.info("✅ Database Connection Pool Initialized Successfully!")
            app.healthy = True

        if check_db_connection():
            logger.info("✅ Database connection successful")
            global db_initialized
            db_initialized = True
            app.healthy = True
        else:
            logger.warning("⚠️ Database connection failed!")
            app.healthy = False

    except Exception as e:
        logger.error(f"🚨 Failed to check database connection: {str(e)}")
        app.healthy = False

    @app.after_request
    def after_request(response):
        """Record metrics after each request"""
        return record_request_metrics(response)

    # Register Blueprints
    try:
        # Register health blueprint first
        app.register_blueprint(health_bp, url_prefix="/api/health")

        # Then register other blueprints
        from routes.auth_routes import auth_bp
        from routes.product_routes import product_bp
        from routes.cart_routes import cart_bp
        from routes.order_routes import order_bp

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(product_bp, url_prefix="/api")
        app.register_blueprint(cart_bp, url_prefix="/api")
        app.register_blueprint(order_bp, url_prefix="/api")
        logger.info("✅ All blueprints registered successfully!")

    except Exception as e:
        logger.error(f"🚨 Error registering blueprints: {e}")
        app.healthy = False

    @app.route("/")
    def serve_index():
        logger.info(f"📢 Serving index.html from {FRONTEND_PATH}")
        if os.path.exists(os.path.join(FRONTEND_PATH, "index.html")):
            return send_from_directory(FRONTEND_PATH, "index.html")
        else:
            logger.error("❌ index.html not found in FRONTEND_PATH")
            return jsonify({"message": "Frontend not found"}), 500

    @app.route("/<path:filename>")
    def serve_static_files(filename):
        full_path = os.path.join(FRONTEND_PATH, filename)
        if os.path.exists(full_path):
            return send_from_directory(FRONTEND_PATH, filename)
        else:
            logger.warning(f"⚠️ Requested file {filename} not found in {FRONTEND_PATH}")
            return jsonify({"message": "Resource not found"}), 404

    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"404 - Resource not found: {request.path}")
        return jsonify({"message": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 - Internal server error: {error}")
        return jsonify({"message": "Internal server error"}), 500

    return app

if __name__ == "__main__":
    app = create_app()
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    port = int(os.getenv("PORT", 5000))

    logger.info(f"🚀 Starting Flask app in {'debug' if debug_mode else 'production'} mode on port {port}")
    app.run(debug=debug_mode, host="0.0.0.0", port=port)