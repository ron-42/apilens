"""Custom exceptions for the APILens SDK."""


class APILensError(Exception):
    """Base exception for all APILens SDK errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class ConfigurationError(APILensError):
    """Raised when the SDK is misconfigured."""

    pass


class TransportError(APILensError):
    """Raised when data cannot be sent to the APILens server."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class RateLimitError(TransportError):
    """Raised when the API rate limit is exceeded."""

    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after}s" if retry_after else "Rate limit exceeded",
            status_code=429,
        )


class AuthenticationError(TransportError):
    """Raised when the API key is invalid or missing."""

    def __init__(self) -> None:
        super().__init__("Invalid or missing API key", status_code=401)
