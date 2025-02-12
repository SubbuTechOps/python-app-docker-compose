from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry

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
    'HTTP request latency',
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
    'Cart operations',
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

# Product Metrics
PRODUCT_VIEW_COUNT = Counter(
    'product_views_total',
    'Total product views',
    ['product_id'],
    registry=REGISTRY
)

STOCK_LEVEL = Gauge(
    'product_stock_level',
    'Current stock level',
    ['product_id'],
    registry=REGISTRY
)