from functools import wraps
from flask import request, g
import time
from prometheus_client import Counter, Histogram, CollectorRegistry

# Create a global registry
REGISTRY = CollectorRegistry()

# Define metrics with the global registry
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    registry=REGISTRY
)

REQUEST_COUNT = Counter(
    'http_request_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY
)

USER_LOGIN_COUNT = Counter(
    'user_login_total',
    'Total user login attempts',
    ['status'],
    registry=REGISTRY
)

DB_QUERY_LATENCY = Histogram(
    'db_query_duration_seconds',
    'Database query latency in seconds',
    ['query_type'],
    registry=REGISTRY
)

class MonitoringMiddleware:
    def __init__(self, app):
        self.app = app
        
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')
        
        # Skip metrics endpoint to avoid recursion
        if path == '/api/metrics':  # Updated to match your API path
            return self.app(environ, start_response)
            
        start_time = time.time()
        
        def custom_start_response(status, headers, exc_info=None):
            status_code = int(status.split()[0])
            
            # Record request metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status=status_code
            ).inc()
            
            # Record latency
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            
            return start_response(status, headers, exc_info)
            
        return self.app(environ, custom_start_response)

def track_db_query(func):
    """Decorator to track database query metrics"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            query_type = 'select' if func.__name__.startswith('get') else 'other'
            DB_QUERY_LATENCY.labels(query_type=query_type).observe(time.time() - start_time)
            return result
        except Exception as e:
            raise e
    return wrapper

def track_user_action(action_type):
    """Decorator to track user actions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if action_type == 'login':
                    USER_LOGIN_COUNT.labels(
                        status='success' if result[1] == 200 else 'failed'
                    ).inc()
                return result
            except Exception as e:
                if action_type == 'login':
                    USER_LOGIN_COUNT.labels(status='failed').inc()
                raise e
        return wrapper
    return decorator