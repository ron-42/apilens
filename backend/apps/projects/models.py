import uuid

from django.conf import settings
from django.db import models

from .managers import AppManager


class App(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="apps",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, db_index=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AppManager()

    class Meta:
        db_table = "apps"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "slug"],
                name="unique_app_slug_per_owner",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.slug})"
