from prometheus_client import Counter, Histogram, Gauge, Summary
import time

# HTTP Request Metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Business Metrics
ORDER_COUNT = Counter(
    'orders_total',
    'Total orders placed',
    ['status']  # success, failed
)

CART_OPERATIONS = Counter(
    'cart_operations_total',
    'Cart operations',
    ['operation']  # add, remove, checkout
)

# Database Metrics
DB_CONNECTION_COUNT = Gauge(
    'db_connections_active',
    'Number of active database connections'
)

DB_QUERY_LATENCY = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type']  # select, insert, update, delete
)

# User Metrics
USER_SESSION_COUNT = Gauge(
    'user_sessions_active',
    'Number of active user sessions'
)

USER_LOGIN_COUNT = Counter(
    'user_logins_total',
    'Total number of user logins',
    ['status']  # success, failed
)

# Product Metrics
PRODUCT_VIEW_COUNT = Counter(
    'product_views_total',
    'Total product views',
    ['product_id']
)

STOCK_LEVEL = Gauge(
    'product_stock_level',
    'Current stock level',
    ['product_id']
)