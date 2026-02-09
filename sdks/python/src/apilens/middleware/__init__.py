"""Framework middleware integrations."""

from .django import APILensDjangoMiddleware
from .fastapi import APILensMiddleware as APILensFastAPIMiddleware
from .flask import APILensFlaskMiddleware

__all__ = [
    "APILensDjangoMiddleware",
    "APILensFastAPIMiddleware",
    "APILensFlaskMiddleware",
]
