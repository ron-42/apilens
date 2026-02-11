from django.db import transaction
from django.utils.text import slugify

from apps.users.models import User
from core.exceptions.base import NotFoundError, RateLimitError, ValidationError

from .models import App

MAX_APPS_PER_USER = 20

# Reserved slugs that cannot be used as app names
RESERVED_SLUGS = frozenset({
    "settings", "api", "new", "account", "admin", "help", "support",
    "dashboard", "apps", "app", "auth", "login", "logout", "signup",
    "register", "notifications", "search", "docs", "documentation",
    "billing", "pricing", "terms", "privacy", "about", "contact",
})


class AppService:
    @staticmethod
    @transaction.atomic
    def create_app(user: User, name: str, description: str = "") -> App:
        active_count = App.objects.for_user(user).count()
        if active_count >= MAX_APPS_PER_USER:
            raise RateLimitError(f"Maximum of {MAX_APPS_PER_USER} apps allowed")

        name = name.strip()
        if not name:
            raise ValidationError("App name is required")

        slug = _unique_slug(user, name)

        return App.objects.create(
            owner=user,
            name=name[:100],
            slug=slug,
            description=description.strip()[:500],
        )

    @staticmethod
    def list_apps(user: User) -> list[App]:
        return list(
            App.objects.for_user(user)
            .order_by("-created_at")
        )

    @staticmethod
    def get_app(user: User, app_id: str) -> App:
        try:
            return App.objects.active().get(id=app_id, owner=user)
        except App.DoesNotExist:
            raise NotFoundError("App not found")

    @staticmethod
    def get_app_by_slug(user: User, slug: str) -> App:
        """Lookup app by slug instead of UUID."""
        try:
            return App.objects.active().get(slug=slug, owner=user)
        except App.DoesNotExist:
            raise NotFoundError("App not found")

    @staticmethod
    @transaction.atomic
    def update_app(
        user: User, app_slug: str, name: str | None = None, description: str | None = None,
    ) -> App:
        app = AppService.get_app_by_slug(user, app_slug)

        update_fields = ["updated_at"]

        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError("App name is required")
            app.name = name[:100]
            app.slug = _unique_slug(user, name, exclude_id=app.id)
            update_fields += ["name", "slug"]

        if description is not None:
            app.description = description.strip()[:500]
            update_fields.append("description")

        app.save(update_fields=update_fields)
        return app

    @staticmethod
    @transaction.atomic
    def delete_app(user: User, app_slug: str) -> None:
        app = AppService.get_app_by_slug(user, app_slug)

        # Revoke all API keys for this app
        app.api_keys.filter(is_revoked=False).update(is_revoked=True)

        # Soft-delete
        app.is_active = False
        app.save(update_fields=["is_active", "updated_at"])


def _unique_slug(user: User, name: str, exclude_id=None) -> str:
    base = slugify(name)[:100]
    if not base:
        base = "app"

    # Check if base slug is reserved
    if base in RESERVED_SLUGS:
        base = f"{base}-app"

    slug = base
    counter = 1
    qs = App.objects.filter(owner=user)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    while qs.filter(slug=slug).exists() or slug in RESERVED_SLUGS:
        slug = f"{base}-{counter}"
        counter += 1

    return slug
