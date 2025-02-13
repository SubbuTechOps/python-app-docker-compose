from flask import Blueprint, jsonify
from database.db_config import check_db_connection
import psutil
import time

# Create Blueprint with the EXACT name 'health'
health_bp = Blueprint('health', __name__)

@health_bp.route('/health')  # This becomes /api/health/health
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

@health_bp.route('/live')  # This becomes /api/health/live
def liveness():
    """Liveness probe endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

@health_bp.route('/ready')  # This becomes /api/health/ready
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