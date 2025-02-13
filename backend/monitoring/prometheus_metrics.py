from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from functools import wraps
from flask import request
import time

# Create a global registry
REGISTRY = CollectorRegistry()

# HTTP Request Metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    registry=REGISTRY
)

# Business Metrics
ORDER_COUNT = Counter(
    'orders_total',
    'Total orders placed',
    ['status'],  # success, failed
    registry=REGISTRY
)

CART_OPERATIONS = Counter(
    'cart_operations_total',
    'Cart operations count',
    ['operation'],  # add, remove, checkout
    registry=REGISTRY
)

# Database Metrics
DB_CONNECTION_COUNT = Gauge(
    'db_connections_active',
    'Number of active database connections',
    registry=REGISTRY
)

DB_QUERY_LATENCY = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type'],  # select, insert, update, delete
    registry=REGISTRY
)

# User Metrics
USER_SESSION_COUNT = Gauge(
    'user_sessions_active',
    'Number of active user sessions',
    registry=REGISTRY
)

USER_LOGIN_COUNT = Counter(
    'user_logins_total',
    'Total number of user logins',
    ['status'],  # success, failed
    registry=REGISTRY
)

def record_request_metrics(response):
    """Record request metrics for any endpoint"""
    try:
        method = request.method
        endpoint = request.endpoint or request.path
        status = response.status_code if hasattr(response, 'status_code') else 500
        
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        return response
    except Exception as e:
        print(f"Error recording metrics: {e}")
        return response

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

def track_order(func):
    """Decorator to track order metrics"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            status_code = result[1] if isinstance(result, tuple) else 200
            ORDER_COUNT.labels(status='success' if status_code == 201 else 'failed').inc()
            return result
        except Exception as e:
            ORDER_COUNT.labels(status='failed').inc()
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
                    status_code = result[1] if isinstance(result, tuple) else 200
                    USER_LOGIN_COUNT.labels(
                        status='success' if status_code == 200 else 'failed'
                    ).inc()
                return result
            except Exception as e:
                if action_type == 'login':
                    USER_LOGIN_COUNT.labels(status='failed').inc()
                raise e
        return wrapper
    return decorator