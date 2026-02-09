"""Data models for APILens telemetry data."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

# Limits for string truncation
MAX_STRING_LENGTH = 4096
MAX_ATTRIBUTE_KEY_LENGTH = 256
MAX_ATTRIBUTE_VALUE_LENGTH = 4096


def _now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def _generate_id() -> str:
    """Generate a unique ID for spans."""
    return uuid.uuid4().hex[:16]


def _sanitize_float(value: float) -> float:
    """Sanitize a float value, replacing NaN/Infinity with 0."""
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return value


def _sanitize_string(value: str, max_length: int = MAX_STRING_LENGTH) -> str:
    """Truncate a string to max length."""
    if len(value) > max_length:
        return value[:max_length - 3] + "..."
    return value


def _sanitize_tags(tags: dict[str, Any]) -> dict[str, str]:
    """Convert tag values to strings and sanitize."""
    result: dict[str, str] = {}
    for key, value in tags.items():
        if not key:  # Skip empty keys
            continue
        sanitized_key = _sanitize_string(str(key), MAX_ATTRIBUTE_KEY_LENGTH)
        sanitized_value = _sanitize_string(str(value), MAX_ATTRIBUTE_VALUE_LENGTH)
        result[sanitized_key] = sanitized_value
    return result


class LogLevel(str, Enum):
    """Log severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SpanStatus(str, Enum):
    """Trace span status codes."""

    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class Metric:
    """
    A single metric data point.

    Attributes:
        name: Metric name (e.g., "api.request.duration")
        value: Numeric value
        timestamp: When the metric was recorded (defaults to now)
        tags: Key-value pairs for filtering/grouping

    Example:
        Metric("http.request.duration_ms", 142.5, tags={"method": "GET", "path": "/users"})
    """

    name: str
    value: float
    timestamp: datetime = field(default_factory=_now)
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to API payload format."""
        return {
            "metric_name": _sanitize_string(self.name, MAX_ATTRIBUTE_KEY_LENGTH),
            "value": _sanitize_float(self.value),
            "timestamp": self.timestamp.isoformat(),
            "tags": _sanitize_tags(self.tags),
        }


@dataclass
class Log:
    """
    A structured log entry.

    Attributes:
        level: Log severity (debug, info, warning, error, critical)
        message: Log message
        timestamp: When the log was recorded
        attributes: Additional structured data
        trace_id: Optional trace correlation ID
        span_id: Optional span correlation ID

    Example:
        Log("info", "User logged in", attributes={"user_id": "123"})
    """

    level: LogLevel | str
    message: str
    timestamp: datetime = field(default_factory=_now)
    attributes: dict[str, str] = field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.level, str):
            self.level = LogLevel(self.level.lower())

    def to_dict(self) -> dict[str, Any]:
        """Convert to API payload format."""
        return {
            "level": self.level.value if isinstance(self.level, LogLevel) else self.level,
            "message": _sanitize_string(self.message),
            "timestamp": self.timestamp.isoformat(),
            "attributes": _sanitize_tags(self.attributes),
            "trace_id": self.trace_id or "",
            "span_id": self.span_id or "",
        }


@dataclass
class Trace:
    """
    A distributed trace span.

    Attributes:
        trace_id: Unique identifier for the entire trace
        span_id: Unique identifier for this span
        operation_name: Name of the operation (e.g., "GET /users")
        service_name: Name of the service
        parent_span_id: ID of the parent span (if any)
        start_time: When the span started
        end_time: When the span ended
        duration_ms: Duration in milliseconds
        status: Span status (ok, error, unset)
        attributes: Additional span attributes

    Example:
        Trace(
            operation_name="GET /users",
            service_name="api-gateway",
            duration_ms=45.2,
            attributes={"http.status_code": "200"}
        )
    """

    operation_name: str
    service_name: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    span_id: str = field(default_factory=_generate_id)
    parent_span_id: str | None = None
    start_time: datetime = field(default_factory=_now)
    end_time: datetime | None = None
    duration_ms: float | None = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: dict[str, str] = field(default_factory=dict)

    def finish(self, status: SpanStatus | None = None) -> None:
        """Mark the span as finished. Does nothing if already finished."""
        if self.end_time is not None:
            return  # Already finished
        self.end_time = _now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        if status:
            self.status = status

    def set_attribute(self, key: str, value: str) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def set_error(self, error: Exception) -> None:
        """Record an error on this span."""
        self.status = SpanStatus.ERROR
        self.attributes["error.type"] = type(error).__name__
        self.attributes["error.message"] = str(error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to API payload format."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id or "",
            "operation_name": _sanitize_string(self.operation_name, MAX_ATTRIBUTE_KEY_LENGTH),
            "service_name": _sanitize_string(self.service_name, MAX_ATTRIBUTE_KEY_LENGTH),
            "timestamp": self.start_time.isoformat(),
            "duration_ms": _sanitize_float(self.duration_ms or 0),
            "status_code": self.status.value,
            "attributes": _sanitize_tags(self.attributes),
        }


@dataclass
class Event:
    """
    A custom application event.

    Attributes:
        event_type: Category of the event (e.g., "user", "payment")
        event_name: Specific event name (e.g., "signup", "checkout")
        timestamp: When the event occurred
        payload: JSON-serializable event data
        attributes: Additional metadata

    Example:
        Event("user", "signup", payload={"plan": "pro", "source": "google"})
    """

    event_type: str
    event_name: str
    timestamp: datetime = field(default_factory=_now)
    payload: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to API payload format."""
        import json

        # Safely serialize payload, handling non-serializable objects
        try:
            payload_str = json.dumps(self.payload, default=str)
        except (TypeError, ValueError):
            payload_str = "{}"

        return {
            "event_type": _sanitize_string(self.event_type, MAX_ATTRIBUTE_KEY_LENGTH),
            "event_name": _sanitize_string(self.event_name, MAX_ATTRIBUTE_KEY_LENGTH),
            "timestamp": self.timestamp.isoformat(),
            "payload": payload_str,
            "attributes": _sanitize_tags(self.attributes),
        }


@dataclass
class SpanContext:
    """Context for span propagation across service boundaries."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers for propagation."""
        headers = {
            "X-Trace-Id": self.trace_id,
            "X-Span-Id": self.span_id,
        }
        if self.parent_span_id:
            headers["X-Parent-Span-Id"] = self.parent_span_id
        return headers

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> SpanContext | None:
        """Extract span context from HTTP headers."""
        trace_id = headers.get("X-Trace-Id") or headers.get("x-trace-id")
        span_id = headers.get("X-Span-Id") or headers.get("x-span-id")

        if not trace_id or not span_id:
            return None

        return cls(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=headers.get("X-Parent-Span-Id") or headers.get("x-parent-span-id"),
        )
