from flask import Blueprint, jsonify
from database.db_config import check_db_connection
import psutil
import time
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Fix the name parameter
health_bp = Blueprint('health', __name__)

@health_bp.route('/metrics')
def metrics():
    """Endpoint for Prometheus metrics"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@health_bp.route('/health')  # Add this endpoint for kubernetes health checks
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

@health_bp.route('/live')
def liveness():
    """Liveness probe endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

@health_bp.route('/ready')
def readiness():
    """Readiness probe endpoint"""
    try:
        db_status = check_db_connection()
        checks = {
            "database": "healthy" if db_status else "unhealthy",
            "memory_usage": psutil.virtual_memory().percent,
            "cpu_usage": psutil.cpu_percent(),
            "disk_usage": psutil.disk_usage('/').percent
        }
        
        is_ready = db_status and checks["memory_usage"] < 90
        return jsonify({
            "status": "ready" if is_ready else "not ready",
            "checks": checks
        }), 200 if is_ready else 503
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "checks": {
                "database": "unhealthy",
                "error": str(e)
            }
        }), 503