from flask import Blueprint, request, jsonify, session, make_response, redirect, url_for
from models.user import User
import logging
import bcrypt
from functools import wraps

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Add admin role check decorator
def admin_required(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        logger.debug(f"Checking admin rights - Current session: {session}")
        if 'user_id' not in session:
            return jsonify({"message": "Authentication required"}), 401
        if not session.get('is_admin', False):
            return jsonify({"message": "Admin privileges required"}), 403
        return view_function(*args, **kwargs)
    return wrapper

# Add check auth status route
@auth_bp.route('/status', methods=['GET'])
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
        
        # Set session
        session.clear()  # Clear any existing session first
        session['username'] = username
        session['user_id'] = user.user_id
        session.permanent = True
        
        logger.debug(f"Session after signup: {session}")
        
        response = jsonify({
            "message": "User registered successfully.", 
            "user": user.to_dict()
        })
        return response, 201
    
    except Exception as e:
        logger.error(f"Error in signup: {str(e)}", exc_info=True)
        return jsonify({
            "message": "An error occurred during signup.", 
            "error": str(e)
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        logger.debug(f"Login attempt - Session before: {session}")
        
        if not request.is_json:
            return jsonify({"message": "Invalid request format. JSON required."}), 400
        
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"message": "Username and password are required."}), 400
        
        user = User.authenticate(username, password)
        if user:
            # Clear any existing session first
            session.clear()
            
            # Set new session
            session['username'] = username
            session['user_id'] = user.user_id
            session['is_admin'] = user.is_admin  # Add admin status to session
            session.permanent = True
            
            logger.debug(f"Login successful - Session after: {session}")
            
            response = jsonify({
                "message": "Login successful.", 
                "user": user.to_dict()
            })
            return response, 200
        
        logger.warning(f"Login failed for username: {username}")
        return jsonify({"message": "Invalid credentials."}), 401
    
    except Exception as e:
        logger.error(f"Error in login: {str(e)}", exc_info=True)
        return jsonify({
            "message": "An error occurred during login.", 
            "error": str(e)
        }), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    try:
        logger.debug(f"Logout attempt - Session before: {session}")
        session.clear()
        logger.debug(f"Logout successful - Session after: {session}")
        
        response = make_response(jsonify({"message": "Logout successful."}))
        response.delete_cookie('session')  # Delete the session cookie
        return response, 200
    
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}", exc_info=True)
        return jsonify({
            "message": "An error occurred during logout.", 
            "error": str(e)
        }), 500

@auth_bp.route('/admin/update-passwords', methods=['POST'])
@admin_required
def admin_update_passwords():
    """Admin route to update plain text passwords with bcrypt hashes"""
    try:
        logger.info("Starting password hash update process")
        updated_count = 0
        skipped_count = 0
        
        # Get all users using the User model
        users = User.get_all_users()
        
        for user in users:
            # Skip already hashed passwords
            if user.password.startswith('$2b$'):
                logger.debug(f"Skipping already hashed password for user: {user.username}")
                skipped_count += 1
                continue
                
            try:
                # Hash the plain text password
                hashed = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
                
                # Update the user's password
                User.update_password(user.user_id, hashed.decode('utf-8'))
                logger.debug(f"Updated password for user: {user.username}")
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error updating password for user {user.username}: {str(e)}")
                continue
        
        logger.info(f"Password update completed. Updated: {updated_count}, Skipped: {skipped_count}")
        
        return jsonify({
            'success': True,
            'message': 'Password update completed',
            'stats': {
                'total_processed': len(users),
                'updated': updated_count,
                'skipped': skipped_count
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in admin password update: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error updating passwords: {str(e)}'
        }), 500

# Add authentication middleware
def login_required(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        logger.debug(f"Checking authentication - Current session: {session}")
        if 'user_id' not in session:
            return jsonify({"message": "Authentication required"}), 401
        return view_function(*args, **kwargs)
    return wrapper