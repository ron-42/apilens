# APILens Python SDK

The official Python SDK for [APILens](https://github.com/apilens/apilens) - an open-source API observability platform.

[![PyPI version](https://badge.fury.io/py/apilens.svg)](https://badge.fury.io/py/apilens)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 📊 **Metrics** - Track counters, gauges, and histograms
- 📝 **Logs** - Structured logging with trace correlation
- 🔍 **Traces** - Distributed tracing with automatic context propagation
- 🎯 **Events** - Custom application events
- 🚀 **Auto-instrumentation** - Middleware for Django, FastAPI, and Flask
- ⚡ **Async-friendly** - Background batching with configurable flush intervals

## Installation

```bash
pip install apilens
```

With framework integrations:

```bash
pip install apilens[django]    # Django middleware
pip install apilens[fastapi]   # FastAPI/Starlette middleware
pip install apilens[flask]     # Flask middleware
pip install apilens[all]       # All frameworks + dev dependencies
```

## Quick Start

### Basic Usage

```python
from apilens import APILensClient

# Initialize the client
client = APILensClient(
    api_key="your-api-key",
    service_name="my-service",
)

# Record a metric
client.metric("api.requests", 1, tags={"endpoint": "/users", "method": "GET"})

# Record a log
client.info("Request processed", user_id="123", status="success")

# Record a trace span
with client.span("process_order", service="order-service") as span:
    span.set_attribute("order.id", "ORD-123")
    span.set_attribute("order.total", "99.99")
    # ... your code ...

# Record a custom event
client.event("user", "signup", payload={"plan": "pro", "source": "google"})

# Flush before shutdown
client.flush()
```

### Global Client (Singleton Pattern)

```python
import apilens

# Initialize once at startup
apilens.init(
    api_key="your-api-key",
    service_name="my-service",
)

# Use anywhere in your code
apilens.get_client().metric("requests", 1)
```

## Framework Integrations

### Django

```python
# settings.py
import apilens

# Initialize the client
apilens.init(api_key="your-api-key", service_name="my-django-app")

MIDDLEWARE = [
    'apilens.middleware.APILensDjangoMiddleware',
    # ... other middleware
]
```

This automatically:
- Creates a trace span for each request
- Records `http.server.duration_ms` metrics
- Propagates trace context from incoming headers
- Logs errors

### FastAPI

```python
from fastapi import FastAPI
from apilens.middleware import APILensFastAPIMiddleware
import apilens

apilens.init(api_key="your-api-key", service_name="my-fastapi-app")

app = FastAPI()
app.add_middleware(
    APILensFastAPIMiddleware,
    exclude_paths=["/health", "/metrics"],  # Optional: paths to skip
)

@app.get("/users/{user_id}")
async def get_user(request: Request, user_id: str):
    # Access the current span
    span = request.state.apilens_span
    span.set_attribute("user.id", user_id)
    return {"user_id": user_id}
```

### Flask

```python
from flask import Flask
from apilens.middleware import APILensFlaskMiddleware
import apilens

apilens.init(api_key="your-api-key", service_name="my-flask-app")

app = Flask(__name__)
APILensFlaskMiddleware(app)
```

## API Reference

### Metrics

```python
# Generic metric
client.metric("name", value, tags={"key": "value"})

# Convenience methods
client.counter("requests.total")           # Increment by 1
client.counter("requests.total", 5)        # Increment by 5
client.gauge("memory.usage_percent", 75.5)
client.histogram("request.duration_ms", 142.3)
```

### Logs

```python
# With level
client.log("info", "Message", attributes={"key": "value"})

# Convenience methods
client.debug("Debug message", key="value")
client.info("Info message", key="value")
client.warning("Warning message", key="value")
client.error("Error message", key="value")
client.critical("Critical message", key="value")
```

Logs are automatically correlated with the current trace span if one exists.

### Traces

```python
# As context manager (recommended)
with client.span("operation-name", service="my-service") as span:
    span.set_attribute("key", "value")
    # ... your code ...

# With parent context (for distributed tracing)
parent_context = SpanContext.from_headers(request.headers)
with client.span("child-operation", parent=parent_context) as span:
    # ... your code ...

# Nested spans
with client.span("parent-operation") as parent:
    with client.span("child-operation") as child:
        # child automatically inherits parent's trace_id
        pass
```

### Events

```python
client.event(
    event_type="user",           # Category
    event_name="signup",         # Specific event
    payload={"plan": "pro"},     # JSON-serializable data
    attributes={"source": "web"} # Metadata for filtering
)
```

### Configuration

```python
client = APILensClient(
    # Required
    api_key="your-api-key",

    # Optional
    base_url="https://api.apilens.ai",  # Or APILENS_BASE_URL env var
    service_name="my-service",           # Or APILENS_SERVICE_NAME env var
    enabled=True,                        # Set False to disable sending

    # Transport options
    batch_size=100,        # Max items per batch
    flush_interval=5.0,    # Seconds between auto-flushes
    timeout=10.0,          # HTTP timeout in seconds

    # Error handling
    on_error=lambda err, data: print(f"Failed to send: {err}"),
)

# Add default tags to all metrics
client.configure(default_tags={"env": "production", "region": "us-east-1"})
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APILENS_API_KEY` | Your API key | (required) |
| `APILENS_BASE_URL` | API endpoint URL | `https://api.apilens.ai` |
| `APILENS_SERVICE_NAME` | Default service name | `unknown` |

## Distributed Tracing

### Context Propagation

The SDK uses custom headers for trace propagation:

```
X-Trace-Id: <trace-id>
X-Span-Id: <span-id>
X-Parent-Span-Id: <parent-span-id>
```

### Extracting Context from Incoming Requests

```python
from apilens.models import SpanContext

# In your request handler
context = SpanContext.from_headers(dict(request.headers))
if context:
    with client.span("handle-request", parent=context) as span:
        # This span is part of the distributed trace
        pass
```

### Injecting Context into Outgoing Requests

```python
with client.span("call-external-service") as span:
    headers = SpanContext(
        trace_id=span.trace_id,
        span_id=span.span_id,
    ).to_headers()

    response = httpx.get("https://other-service/api", headers=headers)
```

## Testing

Disable the client in tests to avoid sending data:

```python
# conftest.py
import pytest
import apilens

@pytest.fixture(autouse=True)
def disable_apilens():
    apilens.init(enabled=False)
```

Or use the disabled client directly:

```python
client = APILensClient(enabled=False)
# All methods work but don't send data
```

## Development

```bash
# Clone the repo
git clone https://github.com/apilens/apilens.git
cd apilens/sdks/python

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/apilens

# Linting
ruff check src/apilens
```

## License

MIT License - see [LICENSE](../../LICENSE) for details.
