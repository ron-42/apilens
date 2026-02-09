"""Django middleware for automatic request tracing and metrics."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable

from ..client import APILensClient, get_client
from ..models import SpanContext, SpanStatus

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class APILensDjangoMiddleware:
    """
    Django middleware for automatic request instrumentation.

    Automatically:
    - Creates a trace span for each request
    - Records request duration metrics
    - Propagates trace context from incoming headers
    - Logs errors

    Installation:
        # settings.py
        MIDDLEWARE = [
            'apilens.middleware.APILensDjangoMiddleware',
            # ... other middleware
        ]

        # Configure the client
        import apilens
        apilens.init(api_key="your-key", service_name="my-django-app")

    Or pass a custom client:
        APILENS_CLIENT = apilens.APILensClient(api_key="your-key")
    """

    def __init__(self, get_response: Callable[[Any], Any]) -> None:
        self.get_response = get_response
        self._client: APILensClient | None = None

    def _get_client(self) -> APILensClient:
        """Get or create the APILens client."""
        if self._client is None:
            try:
                # Try to get from Django settings first
                from django.conf import settings

                self._client = getattr(settings, "APILENS_CLIENT", None)
            except Exception:
                pass

            if self._client is None:
                # Fall back to global client
                try:
                    self._client = get_client()
                except Exception:
                    # Create a disabled client if not configured
                    self._client = APILensClient(enabled=False)

        return self._client

    def __call__(self, request: HttpRequest) -> HttpResponse:
        client = self._get_client()

        # Extract parent context from headers
        parent_context = SpanContext.from_headers(dict(request.headers))

        # Build operation name
        operation_name = f"{request.method} {request.path}"

        start_time = time.perf_counter()
        status_code = 500  # Default for errors

        with client.span(operation_name, parent=parent_context) as span:
            # Set request attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", request.get_full_path())
            span.set_attribute("http.host", request.get_host())
            span.set_attribute("http.scheme", request.scheme)

            if request.content_type:
                span.set_attribute("http.request.content_type", request.content_type)

            # Store span context on request for downstream use
            request.apilens_span = span  # type: ignore
            request.apilens_trace_id = span.trace_id  # type: ignore

            try:
                response = self.get_response(request)
                status_code = response.status_code

                # Record response attributes
                span.set_attribute("http.status_code", str(status_code))

                if status_code >= 400:
                    span.status = SpanStatus.ERROR
                    span.set_attribute("http.error", "true")

                return response

            except Exception as e:
                span.set_error(e)
                client.error(
                    f"Request failed: {e}",
                    path=request.path,
                    method=request.method,
                    error_type=type(e).__name__,
                )
                raise

            finally:
                # Record duration metric
                duration_ms = (time.perf_counter() - start_time) * 1000
                client.metric(
                    "http.server.duration_ms",
                    duration_ms,
                    tags={
                        "method": request.method,
                        "path": self._normalize_path(request.path),
                        "status_code": str(status_code),
                    },
                )

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path for metric cardinality control.

        Replaces dynamic segments like /users/123 with /users/{id}
        """
        # Basic normalization - replace numeric segments
        import re

        # Replace numeric IDs
        normalized = re.sub(r"/\d+", "/{id}", path)
        # Replace UUIDs
        normalized = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{uuid}",
            normalized,
            flags=re.IGNORECASE,
        )
        return normalized
