"""Main APILens client for sending telemetry data."""

from __future__ import annotations

import contextvars
import logging
import os
from contextlib import contextmanager
from typing import Any, Callable, Generator

from .exceptions import ConfigurationError
from .models import Event, Log, LogLevel, Metric, SpanContext, SpanStatus, Trace
from .transport import NoOpTransport, Transport, TransportConfig

logger = logging.getLogger("apilens")

# Context variable for current span (for automatic trace correlation)
_current_span: contextvars.ContextVar[Trace | None] = contextvars.ContextVar(
    "apilens_current_span", default=None
)


def get_current_span() -> Trace | None:
    """Get the currently active span, if any."""
    return _current_span.get()


class APILensClient:
    """
    Main client for sending observability data to APILens.

    Example:
        client = APILensClient(api_key="your-api-key")

        # Metrics
        client.metric("api.requests", 1, tags={"endpoint": "/users"})
        client.metric("api.latency_ms", 42.5, tags={"method": "GET"})

        # Logs
        client.log("info", "Request processed", attributes={"user_id": "123"})

        # Traces
        with client.span("handle_request", service="my-api") as span:
            span.set_attribute("http.method", "GET")
            # ... your code ...

        # Events
        client.event("user", "signup", payload={"plan": "pro"})

        # Cleanup
        client.flush()
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        service_name: str | None = None,
        enabled: bool = True,
        on_error: Callable[[Exception, list[dict[str, Any]]], None] | None = None,
        # Transport options
        batch_size: int = 100,
        flush_interval: float = 5.0,
        timeout: float = 10.0,
    ) -> None:
        """
        Initialize the APILens client.

        Args:
            api_key: Your APILens API key (or set APILENS_API_KEY env var)
            base_url: APILens API URL (defaults to https://api.apilens.ai or APILENS_BASE_URL)
            service_name: Default service name for traces (or APILENS_SERVICE_NAME)
            enabled: Whether to actually send data (set False for testing)
            on_error: Callback for handling send errors
            batch_size: Max items per batch before automatic flush
            flush_interval: Seconds between automatic flushes
            timeout: HTTP request timeout in seconds
        """
        self._api_key = api_key or os.environ.get("APILENS_API_KEY", "")
        self._base_url = base_url or os.environ.get("APILENS_BASE_URL", "https://api.apilens.ai")
        self._service_name = service_name or os.environ.get("APILENS_SERVICE_NAME", "unknown")
        self._enabled = enabled
        self._default_tags: dict[str, str] = {}

        if not enabled:
            self._transport: Transport | NoOpTransport = NoOpTransport()
            return

        if not self._api_key:
            raise ConfigurationError(
                "API key is required. Pass api_key argument or set APILENS_API_KEY environment variable."
            )

        config = TransportConfig(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=timeout,
            max_batch_size=batch_size,
            flush_interval=flush_interval,
        )
        self._transport = Transport(config, on_error=on_error)

    def configure(
        self,
        service_name: str | None = None,
        default_tags: dict[str, str] | None = None,
    ) -> APILensClient:
        """
        Configure additional client options.

        Args:
            service_name: Default service name for traces
            default_tags: Tags to add to all metrics

        Returns:
            self for chaining
        """
        if service_name:
            self._service_name = service_name
        if default_tags:
            self._default_tags.update(default_tags)
        return self

    # =========================================================================
    # Metrics
    # =========================================================================

    def metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a metric data point.

        Args:
            name: Metric name (e.g., "api.request.duration_ms")
            value: Numeric value
            tags: Key-value pairs for filtering/grouping

        Example:
            client.metric("http.request.duration_ms", 142.5, tags={"method": "GET"})
        """
        all_tags = {**self._default_tags, **(tags or {})}
        m = Metric(name=name, value=value, tags=all_tags)
        self._transport.enqueue("metric", m.to_dict())

    def counter(self, name: str, value: float = 1, tags: dict[str, str] | None = None) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            value: Amount to increment (default 1)
            tags: Key-value pairs for filtering/grouping
        """
        self.metric(name, value, tags)

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """
        Record a gauge metric (current value).

        Args:
            name: Gauge name
            value: Current value
            tags: Key-value pairs for filtering/grouping
        """
        self.metric(name, value, tags)

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """
        Record a histogram/distribution value.

        Args:
            name: Histogram name
            value: Observed value
            tags: Key-value pairs for filtering/grouping
        """
        self.metric(name, value, tags)

    # =========================================================================
    # Logs
    # =========================================================================

    def log(
        self,
        level: LogLevel | str,
        message: str,
        attributes: dict[str, str] | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> None:
        """
        Record a structured log entry.

        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            attributes: Additional structured data
            trace_id: Trace ID for correlation (auto-detected if in span context)
            span_id: Span ID for correlation (auto-detected if in span context)

        Example:
            client.log("info", "User logged in", attributes={"user_id": "123"})
        """
        # Auto-correlate with current span if available
        current_span = get_current_span()
        if current_span:
            trace_id = trace_id or current_span.trace_id
            span_id = span_id or current_span.span_id

        log_entry = Log(
            level=level,
            message=message,
            attributes=attributes or {},
            trace_id=trace_id,
            span_id=span_id,
        )
        self._transport.enqueue("log", log_entry.to_dict())

    def debug(self, message: str, **attributes: str) -> None:
        """Log a debug message."""
        self.log(LogLevel.DEBUG, message, attributes=attributes or None)

    def info(self, message: str, **attributes: str) -> None:
        """Log an info message."""
        self.log(LogLevel.INFO, message, attributes=attributes or None)

    def warning(self, message: str, **attributes: str) -> None:
        """Log a warning message."""
        self.log(LogLevel.WARNING, message, attributes=attributes or None)

    def error(self, message: str, **attributes: str) -> None:
        """Log an error message."""
        self.log(LogLevel.ERROR, message, attributes=attributes or None)

    def critical(self, message: str, **attributes: str) -> None:
        """Log a critical message."""
        self.log(LogLevel.CRITICAL, message, attributes=attributes or None)

    # =========================================================================
    # Traces
    # =========================================================================

    @contextmanager
    def span(
        self,
        operation_name: str,
        service: str | None = None,
        parent: Trace | SpanContext | None = None,
        attributes: dict[str, str] | None = None,
    ) -> Generator[Trace, None, None]:
        """
        Create a trace span as a context manager.

        Args:
            operation_name: Name of the operation (e.g., "GET /users")
            service: Service name (defaults to client's service_name)
            parent: Parent span or context for distributed tracing
            attributes: Initial span attributes

        Example:
            with client.span("handle_request", service="api") as span:
                span.set_attribute("http.method", "GET")
                span.set_attribute("http.url", "/users")
                # ... your code ...

        Yields:
            The Trace span object
        """
        # Determine parent context
        parent_span_id = None
        trace_id = None

        if isinstance(parent, Trace):
            parent_span_id = parent.span_id
            trace_id = parent.trace_id
        elif isinstance(parent, SpanContext):
            parent_span_id = parent.span_id
            trace_id = parent.trace_id
        else:
            # Check for current span in context
            current = get_current_span()
            if current:
                parent_span_id = current.span_id
                trace_id = current.trace_id

        span = Trace(
            operation_name=operation_name,
            service_name=service or self._service_name,
            parent_span_id=parent_span_id,
            attributes=attributes or {},
        )

        if trace_id:
            span.trace_id = trace_id

        # Set as current span
        token = _current_span.set(span)

        try:
            yield span
            if span.status == SpanStatus.UNSET:
                span.status = SpanStatus.OK
        except Exception as e:
            span.set_error(e)
            raise
        finally:
            span.finish()
            self._transport.enqueue("trace", span.to_dict())
            _current_span.reset(token)

    def record_span(self, span: Trace) -> None:
        """
        Record a manually created span.

        Use this when you need more control than the context manager provides.

        Args:
            span: The completed Trace span
        """
        if span.end_time is None:
            span.finish()
        self._transport.enqueue("trace", span.to_dict())

    # =========================================================================
    # Events
    # =========================================================================

    def event(
        self,
        event_type: str,
        event_name: str,
        payload: dict[str, Any] | None = None,
        attributes: dict[str, str] | None = None,
    ) -> None:
        """
        Record a custom application event.

        Args:
            event_type: Category of the event (e.g., "user", "payment", "system")
            event_name: Specific event name (e.g., "signup", "checkout", "deploy")
            payload: JSON-serializable event data
            attributes: Additional metadata for filtering

        Example:
            client.event("user", "signup", payload={"plan": "pro", "source": "google"})
        """
        evt = Event(
            event_type=event_type,
            event_name=event_name,
            payload=payload or {},
            attributes=attributes or {},
        )
        self._transport.enqueue("event", evt.to_dict())

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def flush(self, timeout: float | None = None) -> None:
        """
        Flush all queued data to the API.

        Call this before your application shuts down to ensure all data is sent.

        Args:
            timeout: Maximum time to wait for flush (optional)
        """
        self._transport.flush(timeout=timeout)

    def shutdown(self, timeout: float = 5.0) -> None:
        """
        Gracefully shutdown the client.

        Flushes remaining data and releases resources.

        Args:
            timeout: Maximum time to wait for shutdown
        """
        self._transport.shutdown(timeout=timeout)

    def __enter__(self) -> APILensClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown()


# Default global client (optional singleton pattern)
_default_client: APILensClient | None = None


def init(
    api_key: str | None = None,
    **kwargs: Any,
) -> APILensClient:
    """
    Initialize the default global client.

    Args:
        api_key: Your APILens API key
        **kwargs: Additional arguments passed to APILensClient

    Returns:
        The initialized client

    Example:
        import apilens
        apilens.init(api_key="your-key", service_name="my-api")
        apilens.metric("requests", 1)
    """
    global _default_client
    _default_client = APILensClient(api_key=api_key, **kwargs)
    return _default_client


def get_client() -> APILensClient:
    """Get the default global client."""
    if _default_client is None:
        raise ConfigurationError("APILens not initialized. Call apilens.init() first.")
    return _default_client
