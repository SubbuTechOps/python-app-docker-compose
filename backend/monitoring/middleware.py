from functools import wraps
from flask import request
import time
from .prometheus_metrics import REQUEST_COUNT, REQUEST_LATENCY, REGISTRY

class MonitoringMiddleware:
    def __init__(self, app):
        self.app = app
        
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')
        
        if path == '/api/metrics':
            return self.app(environ, start_response)
            
        start_time = time.time()
        
        def custom_start_response(status, headers, exc_info=None):
            status_code = int(status.split()[0])
            
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status=status_code
            ).inc()
            
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            
            return start_response(status, headers, exc_info)
            
        return self.app(environ, custom_start_response)