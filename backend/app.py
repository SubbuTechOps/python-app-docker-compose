import os
import time
import logging
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
        logger.info(f"🔍 Incoming request: {request.method} {request.path}")

    try:
        from database.db_config import check_db_connection, initialize_pool

        logger.info("🔄 Initializing Database Connection Pool...")
        if not initialize_pool():
            logger.error("❌ Database connection pool initialization failed!")
        else:
            logger.info("✅ Database Connection Pool Initialized Successfully!")

        if check_db_connection():
            logger.info("✅ Database connection successful")
            global db_initialized
            db_initialized = True
        else:
            logger.warning("⚠️ Database connection failed!")

    except Exception as e:
        logger.error(f"🚨 Failed to check database connection: {str(e)}")

    @app.route("/api/health")
    def health_check():
        return jsonify({
            "status": "healthy",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": int(time.time() - start_time)
        }), 200

    @app.route("/api/ready")
    def readiness_check():
        try:
            from database.db_config import check_db_connection

            checks = {
                "app": "ready",
                "uptime": int(time.time() - start_time),
                "session_directory": os.access(session_file_dir, os.W_OK)
            }

            db_status = check_db_connection()
            checks["database"] = db_status

            logger.debug(f"🔍 Readiness Check: {checks}")

            is_ready = db_status and checks["session_directory"]
            return jsonify({
                "status": "ready" if is_ready else "not ready",
                "checks": checks
            }), 200 if is_ready else 503

        except Exception as e:
            logger.error(f"🚨 Readiness check failed: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 503

    # Register Blueprints with updated prefixes
    try:
        from routes.auth_routes import auth_bp
        from routes.product_routes import product_bp
        from routes.cart_routes import cart_bp
        from routes.order_routes import order_bp

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(product_bp, url_prefix="/api")
        app.register_blueprint(cart_bp, url_prefix="/api")
        app.register_blueprint(order_bp, url_prefix="/api")  # Updated from "/api/orders"
        logger.info("✅ All blueprints registered successfully!")

    except Exception as e:
        logger.error(f"🚨 Error registering blueprints: {e}")

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