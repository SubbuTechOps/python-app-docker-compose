from functools import wraps
from flask import request, current_app
import time
from prometheus_client import Counter, Histogram

class MonitoringMiddleware:
    def __init__(self, app):
        self.app = app
        self.REQUEST_COUNT = Counter(
            'http_requests_total',
            'Total HTTP Requests',
            ['method', 'endpoint', 'status']
        )
        self.REQUEST_LATENCY = Histogram(
            'http_request_duration_seconds',
            'HTTP Request Latency'
        )
        
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')
        
        start_time = time.time()
        
        def custom_start_response(status, headers, exc_info=None):
            status_code = int(status.split()[0])
            self.REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status=status_code
            ).inc()
            
            duration = time.time() - start_time
            self.REQUEST_LATENCY.observe(duration)
            
            return start_response(status, headers, exc_info)
        
        return self.app(environ, custom_start_response)