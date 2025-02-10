import psutil
from flask import Blueprint, jsonify
from database.db_config import check_db_connection

health_bp = Blueprint('health', __name__)

@health_bp.route('/health/live')
def liveness():
    return jsonify({
        "status": "healthy",
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent
    })

@health_bp.route('/health/ready')
def readiness():
    db_status = check_db_connection()
    checks = {
        "database": "healthy" if db_status else "unhealthy",
        "disk_usage": psutil.disk_usage('/').percent,
        "memory_available": psutil.virtual_memory().available / (1024 * 1024)  # MB
    }
    return jsonify(checks), 200 if db_status else 503