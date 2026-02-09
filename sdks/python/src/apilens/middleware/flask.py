"""Flask middleware for automatic request tracing and metrics."""

from __future__ import annotations

import re
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

from ..client import APILensClient, get_client
from ..models import SpanContext, SpanStatus

if TYPE_CHECKING:
    from flask import Flask, Request, Response


class APILensFlaskMiddleware:
    """
    Flask extension for automatic request instrumentation.

    Automatically:
    - Creates a trace span for each request
    - Records request duration metrics
    - Propagates trace context from incoming headers
    - Logs errors

    Installation:
        from flask import Flask
        from apilens.middleware import APILensFlaskMiddleware
        import apilens

        apilens.init(api_key="your-key", service_name="my-flask-app")

        app = Flask(__name__)
        APILensFlaskMiddleware(app)

    Or with custom client:
        client = apilens.APILensClient(api_key="your-key")
        APILensFlaskMiddleware(app, client=client)
    """

    def __init__(
        self,
        app: Flask | None = None,
        client: APILensClient | None = None,
        exclude_paths: list[str] | None = None,
    ) -> None:
        """
        Initialize the Flask middleware.

        Args:
            app: Flask application (can also use init_app)
            client: Custom APILens client
            exclude_paths: Path patterns to exclude from tracing
        """
        self._client = client
        self._exclude_patterns = [re.compile(p) for p in (exclude_paths or [])]

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize the middleware with a Flask app."""
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_request(self._teardown_request)

        # Store reference to middleware on app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["apilens"] = self

    def _get_client(self) -> APILensClient:
        """Get the APILens client."""
        if self._client is not None:
            return self._client

        try:
            return get_client()
        except Exception:
            self._client = APILensClient(enabled=False)
            return self._client

    def _should_trace(self, path: str) -> bool:
        """Check if this path should be traced."""
        for pattern in self._exclude_patterns:
            if pattern.match(path):
                return False
        return True

    def _before_request(self) -> None:
        """Called before each request."""
        from flask import g, request

        if not self._should_trace(request.path):
            g._apilens_skip = True
            return

        client = self._get_client()

        # Extract parent context
        parent_context = SpanContext.from_headers(dict(request.headers))

        # Create span context manager and enter it
        operation_name = f"{request.method} {request.path}"
        span_cm = client.span(operation_name, parent=parent_context)
        span = span_cm.__enter__()

        # Store both the context manager and the span
        g._apilens_span_cm = span_cm
        g._apilens_span = span
        g._apilens_start_time = time.perf_counter()

        # Set request attributes
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.set_attribute("http.host", request.host)
        span.set_attribute("http.scheme", request.scheme)

    def _after_request(self, response: Response) -> Response:
        """Called after each request (if no exception)."""
        from flask import g, request

        if getattr(g, "_apilens_skip", False):
            return response

        span = getattr(g, "_apilens_span", None)
        if span is None:
            return response

        # Record response attributes
        span.set_attribute("http.status_code", str(response.status_code))

        if response.status_code >= 400:
            span.status = SpanStatus.ERROR

        # Store status code for metrics in teardown
        g._apilens_status_code = response.status_code

        return response

    def _teardown_request(self, exception: BaseException | None) -> None:
        """Called at the end of each request."""
        from flask import g, request

        if getattr(g, "_apilens_skip", False):
            return

        span_cm = getattr(g, "_apilens_span_cm", None)
        span = getattr(g, "_apilens_span", None)
        if span_cm is None or span is None:
            return

        if exception:
            span.set_error(exception)

        # Record metrics
        client = self._get_client()
        duration_ms = (time.perf_counter() - g._apilens_start_time) * 1000
        status_code = getattr(g, "_apilens_status_code", 500)

        client.metric(
            "http.server.duration_ms",
            duration_ms,
            tags={
                "method": request.method,
                "path": self._normalize_path(request.path),
                "status_code": str(status_code),
            },
        )

        # Properly exit the context manager (this handles finish + enqueue)
        span_cm.__exit__(type(exception) if exception else None, exception, None)

    def _normalize_path(self, path: str) -> str:
        """Normalize path for metric cardinality control."""
        normalized = re.sub(r"/\d+", "/{id}", path)
        normalized = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{uuid}",
            normalized,
            flags=re.IGNORECASE,
        )
        return normalized


def trace_function(
    name: str | None = None,
    client: APILensClient | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to trace a function as a span.

    Args:
        name: Span name (defaults to function name)
        client: APILens client (uses global if not provided)

    Example:
        @trace_function()
        def process_order(order_id: str):
            ...

        @trace_function(name="custom-operation")
        def another_function():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        span_name = name or func.__name__

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            c = client or get_client()
            with c.span(span_name) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                return func(*args, **kwargs)

        return wrapper

    return decorator
