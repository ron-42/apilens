"""Tests for the APILens Python SDK."""

import pytest
from datetime import datetime, timezone

from apilens import APILensClient, Metric, Log, Trace, Event
from apilens.models import LogLevel, SpanStatus, SpanContext
from apilens.exceptions import ConfigurationError


class TestMetric:
    """Tests for the Metric model."""

    def test_metric_creation(self):
        m = Metric(name="test.metric", value=42.5)
        assert m.name == "test.metric"
        assert m.value == 42.5
        assert isinstance(m.timestamp, datetime)
        assert m.tags == {}

    def test_metric_with_tags(self):
        m = Metric(name="http.duration", value=100, tags={"method": "GET", "path": "/api"})
        assert m.tags == {"method": "GET", "path": "/api"}

    def test_metric_to_dict(self):
        m = Metric(name="test", value=1.0, tags={"env": "prod"})
        d = m.to_dict()
        assert d["metric_name"] == "test"
        assert d["value"] == 1.0
        assert d["tags"] == {"env": "prod"}
        assert "timestamp" in d


class TestLog:
    """Tests for the Log model."""

    def test_log_creation(self):
        log = Log(level="info", message="Test message")
        assert log.level == LogLevel.INFO
        assert log.message == "Test message"

    def test_log_with_level_enum(self):
        log = Log(level=LogLevel.ERROR, message="Error!")
        assert log.level == LogLevel.ERROR

    def test_log_with_trace_context(self):
        log = Log(
            level="debug",
            message="Traced log",
            trace_id="abc123",
            span_id="def456",
        )
        d = log.to_dict()
        assert d["trace_id"] == "abc123"
        assert d["span_id"] == "def456"

    def test_log_attributes(self):
        log = Log(level="info", message="User action", attributes={"user_id": "123"})
        d = log.to_dict()
        assert d["attributes"] == {"user_id": "123"}


class TestTrace:
    """Tests for the Trace model."""

    def test_trace_creation(self):
        trace = Trace(operation_name="GET /users", service_name="api")
        assert trace.operation_name == "GET /users"
        assert trace.service_name == "api"
        assert trace.trace_id  # Should be auto-generated
        assert trace.span_id  # Should be auto-generated
        assert trace.status == SpanStatus.UNSET

    def test_trace_finish(self):
        trace = Trace(operation_name="test", service_name="test")
        trace.finish()
        assert trace.end_time is not None
        assert trace.duration_ms is not None
        assert trace.duration_ms >= 0

    def test_trace_set_attribute(self):
        trace = Trace(operation_name="test", service_name="test")
        trace.set_attribute("http.method", "POST")
        assert trace.attributes["http.method"] == "POST"

    def test_trace_set_error(self):
        trace = Trace(operation_name="test", service_name="test")
        trace.set_error(ValueError("Something went wrong"))
        assert trace.status == SpanStatus.ERROR
        assert trace.attributes["error.type"] == "ValueError"
        assert trace.attributes["error.message"] == "Something went wrong"

    def test_trace_to_dict(self):
        trace = Trace(
            operation_name="GET /api",
            service_name="gateway",
            attributes={"http.status_code": "200"},
        )
        trace.finish(status=SpanStatus.OK)
        d = trace.to_dict()
        assert d["operation_name"] == "GET /api"
        assert d["service_name"] == "gateway"
        assert d["status_code"] == "ok"
        assert "duration_ms" in d


class TestEvent:
    """Tests for the Event model."""

    def test_event_creation(self):
        event = Event(event_type="user", event_name="signup")
        assert event.event_type == "user"
        assert event.event_name == "signup"

    def test_event_with_payload(self):
        event = Event(
            event_type="payment",
            event_name="checkout",
            payload={"amount": 99.99, "currency": "USD"},
        )
        d = event.to_dict()
        assert '"amount": 99.99' in d["payload"]
        assert '"currency": "USD"' in d["payload"]

    def test_event_with_attributes(self):
        """Event with attributes matches ClickHouse schema."""
        event = Event(
            event_type="user",
            event_name="signup",
            payload={"plan": "pro"},
            attributes={"source": "google", "campaign": "summer2025"},
        )
        d = event.to_dict()
        assert d["event_type"] == "user"
        assert d["event_name"] == "signup"
        assert d["attributes"] == {"source": "google", "campaign": "summer2025"}
        assert "payload" in d


class TestSpanContext:
    """Tests for SpanContext propagation."""

    def test_to_headers(self):
        ctx = SpanContext(trace_id="trace123", span_id="span456", parent_span_id="parent789")
        headers = ctx.to_headers()
        assert headers["X-Trace-Id"] == "trace123"
        assert headers["X-Span-Id"] == "span456"
        assert headers["X-Parent-Span-Id"] == "parent789"

    def test_from_headers(self):
        headers = {
            "X-Trace-Id": "trace123",
            "X-Span-Id": "span456",
        }
        ctx = SpanContext.from_headers(headers)
        assert ctx is not None
        assert ctx.trace_id == "trace123"
        assert ctx.span_id == "span456"

    def test_from_headers_missing(self):
        ctx = SpanContext.from_headers({})
        assert ctx is None


class TestAPILensClient:
    """Tests for the main client."""

    def test_client_disabled(self):
        """Disabled client should not raise errors."""
        client = APILensClient(enabled=False)
        client.metric("test", 1.0)
        client.log("info", "test")
        client.event("test", "test")
        client.flush()

    def test_client_requires_api_key(self):
        """Enabled client should require API key."""
        with pytest.raises(ConfigurationError):
            APILensClient(api_key="", enabled=True)

    def test_client_span_context_manager(self):
        """Span should work as context manager."""
        client = APILensClient(enabled=False)

        with client.span("test-operation", service="test") as span:
            span.set_attribute("test.key", "value")
            assert span.operation_name == "test-operation"
            assert span.end_time is None  # Not finished yet

        # After context exits, span should be finished
        assert span.end_time is not None
        assert span.status == SpanStatus.OK

    def test_client_span_error_handling(self):
        """Span should capture errors."""
        client = APILensClient(enabled=False)

        with pytest.raises(ValueError):
            with client.span("failing-operation", service="test") as span:
                raise ValueError("Test error")

        assert span.status == SpanStatus.ERROR
        assert span.attributes["error.type"] == "ValueError"

    def test_client_configure(self):
        """Configure should update client settings."""
        client = APILensClient(enabled=False)
        client.configure(service_name="my-service", default_tags={"env": "test"})
        assert client._service_name == "my-service"
        assert client._default_tags == {"env": "test"}

    def test_client_context_manager(self):
        """Client should work as context manager."""
        with APILensClient(enabled=False) as client:
            client.metric("test", 1.0)
        # Should not raise


class TestClientConvenienceMethods:
    """Tests for convenience methods."""

    def test_log_levels(self):
        """All log level methods should work."""
        client = APILensClient(enabled=False)
        client.debug("debug message")
        client.info("info message")
        client.warning("warning message")
        client.error("error message")
        client.critical("critical message")

    def test_metric_types(self):
        """All metric type methods should work."""
        client = APILensClient(enabled=False)
        client.counter("requests.count")
        client.gauge("memory.usage", 75.5)
        client.histogram("request.duration", 142.3)


class TestEdgeCases:
    """Tests for edge cases and input validation."""

    def test_metric_nan_value(self):
        """NaN metric values should be sanitized to 0."""
        import math
        m = Metric(name="test", value=float('nan'))
        d = m.to_dict()
        assert d["value"] == 0.0

    def test_metric_infinity_value(self):
        """Infinity metric values should be sanitized to 0."""
        m = Metric(name="test", value=float('inf'))
        d = m.to_dict()
        assert d["value"] == 0.0  # All non-finite values become 0

    def test_metric_negative_infinity_value(self):
        """Negative infinity should be sanitized to 0."""
        m = Metric(name="test", value=float('-inf'))
        d = m.to_dict()
        assert d["value"] == 0.0  # All non-finite values become 0

    def test_metric_empty_name_preserved(self):
        """Empty metric name is preserved (validation should be done at input)."""
        m = Metric(name="", value=1.0)
        d = m.to_dict()
        # Empty names are preserved - input validation should happen earlier
        assert d["metric_name"] == ""

    def test_metric_long_name_truncated(self):
        """Very long metric names should be truncated."""
        long_name = "x" * 500
        m = Metric(name=long_name, value=1.0)
        d = m.to_dict()
        assert len(d["metric_name"]) == 256

    def test_log_empty_tag_key_removed(self):
        """Tags with empty keys should be removed."""
        log = Log(level="info", message="test", attributes={"": "value", "valid": "ok"})
        d = log.to_dict()
        assert "" not in d.get("attributes", {})
        assert d["attributes"]["valid"] == "ok"

    def test_log_long_message_truncated(self):
        """Very long log messages should be truncated."""
        long_msg = "x" * 20000
        log = Log(level="info", message=long_msg)
        d = log.to_dict()
        assert len(d["message"]) <= 10000

    def test_trace_invalid_parent_span_id(self):
        """Trace with parent should propagate correctly."""
        trace = Trace(
            operation_name="child", 
            service_name="test",
            parent_span_id="parent123"
        )
        d = trace.to_dict()
        assert d["parent_span_id"] == "parent123"

    def test_trace_nested_span_context(self):
        """Nested spans should have correct parent-child relationship."""
        client = APILensClient(enabled=False)
        
        with client.span("parent-op", service="test") as parent:
            parent_trace_id = parent.trace_id
            parent_span_id = parent.span_id
            
            with client.span("child-op", service="test") as child:
                # Child should have same trace_id but different span_id
                assert child.trace_id == parent_trace_id
                assert child.span_id != parent_span_id
                assert child.parent_span_id == parent_span_id

    def test_event_non_serializable_payload(self):
        """Non-JSON-serializable payloads should be handled gracefully."""
        class NonSerializable:
            pass
        
        event = Event(
            event_type="test",
            event_name="test",
            payload={"obj": NonSerializable()}
        )
        d = event.to_dict()
        # Should serialize to error message or empty, not crash
        assert "payload" in d

    def test_span_context_invalid_headers(self):
        """SpanContext should handle malformed headers gracefully."""
        headers = {
            "X-Trace-Id": None,
            "X-Span-Id": "",
        }
        ctx = SpanContext.from_headers(headers)
        assert ctx is None

    def test_trace_double_finish(self):
        """Calling finish twice should not cause errors."""
        trace = Trace(operation_name="test", service_name="test")
        trace.finish()
        first_end_time = trace.end_time
        first_duration = trace.duration_ms
        trace.finish()
        # Values should not change on second finish
        assert trace.end_time == first_end_time
        assert trace.duration_ms == first_duration

    def test_client_multiple_configure_calls(self):
        """Multiple configure calls should merge settings."""
        client = APILensClient(enabled=False)
        client.configure(service_name="service1")
        client.configure(default_tags={"env": "prod"})
        assert client._service_name == "service1"
        assert client._default_tags == {"env": "prod"}

    def test_metric_special_characters_in_name(self):
        """Metric names with special characters should work."""
        m = Metric(name="http.request.duration_ms", value=100)
        d = m.to_dict()
        assert d["metric_name"] == "http.request.duration_ms"

    def test_log_level_case_insensitive(self):
        """Log levels should be case-insensitive."""
        log1 = Log(level="INFO", message="test")
        log2 = Log(level="info", message="test")
        log3 = Log(level="Info", message="test")
        assert log1.level == log2.level == log3.level == LogLevel.INFO

    def test_trace_zero_duration(self):
        """Trace with instant finish should have non-negative duration."""
        trace = Trace(operation_name="instant", service_name="test")
        trace.finish()
        assert trace.duration_ms >= 0

    def test_event_empty_payload(self):
        """Event with empty payload should serialize correctly."""
        event = Event(event_type="test", event_name="test", payload={})
        d = event.to_dict()
        assert d["payload"] == "{}"

    def test_client_flush_when_disabled(self):
        """Flushing disabled client should not raise errors."""
        client = APILensClient(enabled=False)
        client.metric("test", 1.0)
        client.flush()  # Should not raise

    def test_client_shutdown_when_disabled(self):
        """Shutting down disabled client should not raise errors."""
        client = APILensClient(enabled=False)
        client.shutdown()  # Should not raise
