"""
APILens Python SDK - API Observability Platform

Usage:
    from apilens import APILensClient

    client = APILensClient(api_key="your-api-key")
    
    # Record a metric
    client.metric("api.request.duration", 142.5, tags={"endpoint": "/users"})
    
    # Record a log
    client.log("info", "Request processed", attributes={"user_id": "123"})
    
    # Record a trace span
    with client.span("handle_request", service="my-api") as span:
        span.set_attribute("http.method", "GET")
        # ... your code ...

    # Flush before shutdown
    client.flush()
"""

from .client import APILensClient, init
from .models import Metric, Log, Trace, Event
from .exceptions import APILensError, ConfigurationError, TransportError

__version__ = "0.1.0"

__all__ = [
    "APILensClient",
    "init",
    "Metric",
    "Log",
    "Trace",
    "Event",
    "APILensError",
    "ConfigurationError",
    "TransportError",
]
