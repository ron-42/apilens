from django.db import transaction
from django.utils.text import slugify

from core.exceptions.base import NotFoundError, RateLimitError, ValidationError

from .models import App

MAX_APPS_PER_USER = 20

RESERVED_SLUGS = {
    "new", "create", "edit", "delete", "settings", "account",
    "admin", "api", "auth", "login", "logout", "signup", "register",
    "dashboard", "home", "help", "support",
    "null", "undefined", "true", "false",
    "system", "internal", "public", "private",
}


def _unique_slug(user, name: str, exclude_id=None) -> str:
    base = slugify(name)[:100]
    if not base:
        base = "app"

    candidate = base
    counter = 1

    while True:
        if candidate in RESERVED_SLUGS:
            candidate = f"{base}-{counter}"
            counter += 1
            continue

        qs = App.objects.filter(owner=user, slug=candidate, is_active=True)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        if not qs.exists():
            return candidate

        candidate = f"{base}-{counter}"
        counter += 1


class AppService:
    @staticmethod
    @transaction.atomic
    def create_app(user, name: str, description: str = "") -> App:
        name = name.strip()
        if not name:
            raise ValidationError("App name is required")

        if App.objects.for_user(user).count() >= MAX_APPS_PER_USER:
            raise RateLimitError(f"Maximum of {MAX_APPS_PER_USER} apps allowed")

        slug = _unique_slug(user, name)
        return App.objects.create(
            owner=user,
            name=name,
            slug=slug,
            description=description.strip(),
        )

    @staticmethod
    def list_apps(user) -> list[App]:
        return list(App.objects.for_user(user).order_by("-created_at"))

    @staticmethod
    def get_app_by_slug(user, slug: str) -> App:
        try:
            return App.objects.get(owner=user, slug=slug, is_active=True)
        except App.DoesNotExist:
            raise NotFoundError("App not found")

    @staticmethod
    @transaction.atomic
    def update_app(user, slug: str, name: str | None = None, description: str | None = None) -> App:
        app = AppService.get_app_by_slug(user, slug)

        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError("App name is required")
            app.name = name
            app.slug = _unique_slug(user, name, exclude_id=app.id)

        if description is not None:
            app.description = description.strip()

        app.save()
        return app

    @staticmethod
    @transaction.atomic
    def delete_app(user, slug: str) -> None:
        app = AppService.get_app_by_slug(user, slug)

        # Revoke all API keys for this app
        from apps.auth.services import ApiKeyService
        ApiKeyService.revoke_all_for_app(app)

        app.is_active = False
        app.save(update_fields=["is_active", "updated_at"])
