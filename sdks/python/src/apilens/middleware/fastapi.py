"""FastAPI/Starlette middleware for automatic request tracing and metrics."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Callable

from ..client import APILensClient, get_client
from ..models import SpanContext, SpanStatus

if TYPE_CHECKING:
    from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.types import ASGIApp


class APILensMiddleware:
    """
    ASGI middleware for FastAPI/Starlette automatic instrumentation.

    Automatically:
    - Creates a trace span for each request
    - Records request duration metrics
    - Propagates trace context from incoming headers
    - Logs errors

    Installation (FastAPI):
        from fastapi import FastAPI
        from apilens.middleware import APILensFastAPIMiddleware
        import apilens

        apilens.init(api_key="your-key", service_name="my-fastapi-app")

        app = FastAPI()
        app.add_middleware(APILensFastAPIMiddleware)

    Or with custom client:
        client = apilens.APILensClient(api_key="your-key")
        app.add_middleware(APILensFastAPIMiddleware, client=client)
    """

    def __init__(
        self,
        app: ASGIApp,
        client: APILensClient | None = None,
        exclude_paths: list[str] | None = None,
    ) -> None:
        """
        Initialize the middleware.

        Args:
            app: The ASGI application
            client: Custom APILens client (optional, uses global if not provided)
            exclude_paths: List of path patterns to exclude from tracing (e.g., ["/health", "/metrics"])
        """
        self.app = app
        self._client = client
        self._exclude_patterns = [re.compile(p) for p in (exclude_paths or [])]

    def _get_client(self) -> APILensClient:
        """Get the APILens client."""
        if self._client is not None:
            return self._client

        try:
            return get_client()
        except Exception:
            # Return disabled client if not configured
            self._client = APILensClient(enabled=False)
            return self._client

    def _should_trace(self, path: str) -> bool:
        """Check if this path should be traced."""
        for pattern in self._exclude_patterns:
            if pattern.match(path):
                return False
        return True

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Import here to avoid issues if starlette isn't installed
        from starlette.requests import Request

        request = Request(scope, receive)
        path = request.url.path

        if not self._should_trace(path):
            await self.app(scope, receive, send)
            return

        client = self._get_client()

        # Extract parent context from headers
        headers = dict(request.headers)
        parent_context = SpanContext.from_headers(headers)

        # Build operation name
        operation_name = f"{request.method} {path}"

        start_time = time.perf_counter()
        status_code = 500  # Default in case of unhandled error

        # Capture response status
        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        with client.span(operation_name, parent=parent_context) as span:
            # Set request attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.host", request.url.hostname or "")
            span.set_attribute("http.scheme", request.url.scheme)

            # Store span in request state for downstream access
            scope["state"] = getattr(scope, "state", {})
            scope["state"]["apilens_span"] = span
            scope["state"]["apilens_trace_id"] = span.trace_id

            try:
                await self.app(scope, receive, send_wrapper)

                span.set_attribute("http.status_code", str(status_code))

                if status_code >= 400:
                    span.status = SpanStatus.ERROR
                    span.set_attribute("http.error", "true")

            except Exception as e:
                span.set_error(e)
                client.error(
                    f"Request failed: {e}",
                    path=path,
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
                        "path": self._normalize_path(path),
                        "status_code": str(status_code),
                    },
                )

    def _normalize_path(self, path: str) -> str:
        """Normalize path for metric cardinality control."""
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


def get_current_span():
    """
    Get the current span from the request context.

    Usage in a FastAPI endpoint:
        from starlette.requests import Request

        @app.get("/users/{user_id}")
        async def get_user(request: Request, user_id: str):
            span = request.state.apilens_span
            span.set_attribute("user.id", user_id)
            ...
    """
    from ..client import get_current_span as _get_current_span

    return _get_current_span()
