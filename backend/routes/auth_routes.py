from flask import Blueprint, request, jsonify, session, make_response
from models.user import User
import logging
import bcrypt
from functools import wraps
from monitoring.prometheus_metrics import (
    USER_LOGIN_COUNT,
    USER_SESSION_COUNT,
    REQUEST_LATENCY,
    REQUEST_COUNT
)
import time

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

def track_auth_metrics(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        endpoint = request.endpoint
        method = request.method
        
        try:
            response = func(*args, **kwargs)
            status_code = response[1] if isinstance(response, tuple) else 200
            
            # Track request metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()
            
            # Track latency
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint
            ).observe(time.time() - start_time)
            
            return response
        except Exception as e:
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=500
            ).inc()
            raise e
    return wrapper

@auth_bp.route('/status', methods=['GET'])
@track_auth_metrics
def check_auth_status():
    """Check if user is authenticated"""
    logger.debug(f"Current session: {session}")
    if 'user_id' in session:
        return jsonify({
            "authenticated": True,
            "user": {
                "username": session.get('username'),
                "user_id": session.get('user_id')
            }
        }), 200
    return jsonify({"authenticated": False}), 401

@auth_bp.route('/signup', methods=['POST'])
@track_auth_metrics
def signup():
    try:
        if not request.is_json:
            return jsonify({"message": "Invalid request format. JSON required."}), 400
        
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"message": "Username and password are required."}), 400
        
        if User.get_user_by_username(username):
            return jsonify({"message": "Username already exists."}), 400
        
        user = User.create_user(username, password)
        
        session.clear()
        session['username'] = username
        session['user_id'] = user.user_id
        session.permanent = True
        
        USER_SESSION_COUNT.inc()
        
        return jsonify({
            "message": "User registered successfully.", 
            "user": user.to_dict()
        }), 201
    
    except Exception as e:
        logger.error(f"Error in signup: {str(e)}", exc_info=True)
        return jsonify({
            "message": "An error occurred during signup.",
            "error": str(e)
        }), 500

@auth_bp.route('/login', methods=['POST'])
@track_auth_metrics
def login():
    try:
        if not request.is_json:
            return jsonify({"message": "Invalid request format. JSON required."}), 400
        
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            USER_LOGIN_COUNT.labels(status='failed').inc()
            return jsonify({"message": "Username and password are required."}), 400
        
        user = User.authenticate(username, password)
        if user:
            session.clear()
            session['username'] = username
            session['user_id'] = user.user_id
            session['is_admin'] = user.is_admin
            session.permanent = True
            
            USER_LOGIN_COUNT.labels(status='success').inc()
            USER_SESSION_COUNT.inc()
            
            return jsonify({
                "message": "Login successful.",
                "user": user.to_dict()
            }), 200
        
        USER_LOGIN_COUNT.labels(status='failed').inc()
        return jsonify({"message": "Invalid credentials."}), 401
    
    except Exception as e:
        USER_LOGIN_COUNT.labels(status='failed').inc()
        logger.error(f"Error in login: {str(e)}", exc_info=True)
        return jsonify({
            "message": "An error occurred during login.",
            "error": str(e)
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@track_auth_metrics
def logout():
    try:
        if 'user_id' in session:
            USER_SESSION_COUNT.dec()
        session.clear()
        
        response = make_response(jsonify({"message": "Logout successful."}))
        response.delete_cookie('session')
        return response, 200
    
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}", exc_info=True)
        return jsonify({
            "message": "An error occurred during logout.",
            "error": str(e)
        }), 500