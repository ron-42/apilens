"""HTTP transport layer with batching and retry logic."""

from __future__ import annotations

import atexit
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from .exceptions import AuthenticationError, RateLimitError, TransportError

logger = logging.getLogger("apilens")


@dataclass
class TransportConfig:
    """Configuration for the HTTP transport."""

    base_url: str = "https://api.apilens.ai"
    api_key: str = ""
    timeout: float = 10.0
    max_batch_size: int = 100
    flush_interval: float = 5.0  # seconds
    max_queue_size: int = 10000
    max_retries: int = 3
    retry_backoff: float = 1.0  # seconds


@dataclass
class Batch:
    """A batch of telemetry data to send."""

    metrics: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)
    traces: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.metrics) + len(self.logs) + len(self.traces) + len(self.events)

    def is_empty(self) -> bool:
        return len(self) == 0

    def clear(self) -> None:
        self.metrics.clear()
        self.logs.clear()
        self.traces.clear()
        self.events.clear()

    def to_payload(self) -> dict[str, Any]:
        """Convert to API request payload."""
        return {
            "metrics": self.metrics,
            "logs": self.logs,
            "traces": self.traces,
            "events": self.events,
        }


class Transport:
    """
    HTTP transport with batching, background flushing, and retry logic.

    Data is queued and sent in batches either when:
    - The batch reaches max_batch_size
    - The flush_interval timer fires
    - flush() is called explicitly
    """

    def __init__(
        self,
        config: TransportConfig,
        on_error: Callable[[Exception, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self.config = config
        self.on_error = on_error

        self._queue: queue.Queue[tuple[str, dict[str, Any]]] = queue.Queue(
            maxsize=config.max_queue_size
        )
        self._batch = Batch()
        self._lock = threading.Lock()
        self._shutdown = threading.Event()
        self._shutdown_complete = False

        # Create HTTP client
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": config.api_key,
                "User-Agent": "apilens-python/0.1.0",
            },
        )

        # Start background flush thread
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

        # Register shutdown handler (will be unregistered on shutdown)
        atexit.register(self._atexit_handler)

    def _atexit_handler(self) -> None:
        """Handler called by atexit - avoids timeout parameter issues."""
        self.shutdown(timeout=5.0)

    def enqueue(self, data_type: str, data: dict[str, Any]) -> bool:
        """
        Add data to the queue for batching.

        Args:
            data_type: One of "metric", "log", "trace", "event"
            data: The data payload as a dict

        Returns:
            True if enqueued, False if queue is full
        """
        try:
            self._queue.put_nowait((data_type, data))
            return True
        except queue.Full:
            logger.warning("APILens queue is full, dropping data")
            return False

    def flush(self, timeout: float | None = None) -> None:
        """
        Flush all queued data immediately.

        Args:
            timeout: Max time to wait for flush to complete
        """
        self._drain_queue()
        with self._lock:
            if not self._batch.is_empty():
                self._send_batch()

    def shutdown(self, timeout: float = 5.0) -> None:
        """
        Gracefully shutdown the transport.

        Flushes remaining data and stops the background thread.
        """
        # Prevent double shutdown
        if self._shutdown_complete:
            return

        # Unregister from atexit to prevent memory leak
        atexit.unregister(self._atexit_handler)

        self._shutdown.set()
        self.flush(timeout=timeout)
        self._client.close()
        self._shutdown_complete = True

    def _flush_loop(self) -> None:
        """Background thread that periodically flushes batches."""
        while not self._shutdown.is_set():
            time.sleep(self.config.flush_interval)
            self._drain_queue()
            with self._lock:
                if not self._batch.is_empty():
                    self._send_batch()

    def _drain_queue(self) -> None:
        """Move items from queue to current batch."""
        with self._lock:
            while True:
                try:
                    data_type, data = self._queue.get_nowait()
                    self._add_to_batch(data_type, data)

                    # Flush if batch is full
                    if len(self._batch) >= self.config.max_batch_size:
                        self._send_batch()
                except queue.Empty:
                    break

    def _add_to_batch(self, data_type: str, data: dict[str, Any]) -> None:
        """Add a single item to the current batch."""
        if data_type == "metric":
            self._batch.metrics.append(data)
        elif data_type == "log":
            self._batch.logs.append(data)
        elif data_type == "trace":
            self._batch.traces.append(data)
        elif data_type == "event":
            self._batch.events.append(data)

    def _send_batch(self) -> None:
        """Send the current batch to the API with retries."""
        if self._batch.is_empty():
            return

        payload = self._batch.to_payload()
        batch_data = list(self._batch.metrics + self._batch.logs + self._batch.traces + self._batch.events)
        self._batch.clear()

        for attempt in range(self.config.max_retries):
            try:
                response = self._client.post("/v1/ingest", json=payload)

                if response.status_code == 200:
                    logger.debug(f"Successfully sent batch of {len(batch_data)} items")
                    return
                elif response.status_code == 401:
                    raise AuthenticationError()
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(retry_after=retry_after)
                else:
                    raise TransportError(
                        f"API returned {response.status_code}: {response.text}",
                        status_code=response.status_code,
                    )

            except httpx.TimeoutException:
                logger.warning(f"Timeout sending batch (attempt {attempt + 1}/{self.config.max_retries})")
            except httpx.RequestError as e:
                logger.warning(f"Request error sending batch: {e} (attempt {attempt + 1}/{self.config.max_retries})")
            except (AuthenticationError, RateLimitError):
                # Don't retry auth/rate limit errors
                raise
            except TransportError as e:
                if e.status_code and e.status_code < 500:
                    # Don't retry client errors
                    raise
                logger.warning(f"Server error: {e} (attempt {attempt + 1}/{self.config.max_retries})")

            # Exponential backoff
            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_backoff * (2**attempt))

        # All retries failed
        error = TransportError(f"Failed to send batch after {self.config.max_retries} retries")
        if self.on_error:
            self.on_error(error, batch_data)
        else:
            logger.error(str(error))


class NoOpTransport:
    """A transport that does nothing - useful for testing or disabling telemetry."""

    def enqueue(self, data_type: str, data: dict[str, Any]) -> bool:
        return True

    def flush(self, timeout: float | None = None) -> None:
        pass

    def shutdown(self, timeout: float = 5.0) -> None:
        pass
