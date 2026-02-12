import uuid

from django.db import models

from .managers import EndpointManager


class Endpoint(models.Model):
    """
    Represents a monitored API endpoint belonging to an App.
    """

    class Method(models.TextChoices):
        GET = "GET"
        POST = "POST"
        PUT = "PUT"
        PATCH = "PATCH"
        DELETE = "DELETE"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(
        "projects.App",
        on_delete=models.CASCADE,
        related_name="endpoints",
    )
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.GET)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EndpointManager()

    class Meta:
        db_table = "endpoints"
        ordering = ["path", "method"]
        constraints = [
            models.UniqueConstraint(
                fields=["app", "path", "method"],
                name="unique_endpoint_per_app",
            ),
        ]

    def __str__(self):
        return f"{self.method} {self.path}"
