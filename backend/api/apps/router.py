from django.db.models import Count, Q
from django.http import HttpRequest
from ninja import Router

from apps.auth.services import ApiKeyService
from apps.projects.services import AppService
from apps.users.models import User
from core.auth.authentication import jwt_auth
from core.exceptions.base import ValidationError

from .schemas import (
    AppListResponse,
    AppResponse,
    CreateApiKeyRequest,
    CreateAppRequest,
    UpdateAppRequest,
    ApiKeyResponse,
    CreateApiKeyResponse,
    MessageResponse,
)

router = Router(auth=[jwt_auth])


@router.post("/", response={201: AppResponse})
def create_app(request: HttpRequest, data: CreateAppRequest):
    user: User = request.auth
    app = AppService.create_app(user, data.name, data.description)
    return 201, AppResponse(
        id=app.id,
        name=app.name,
        slug=app.slug,
        description=app.description,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.get("/", response=list[AppListResponse])
def list_apps(request: HttpRequest):
    user: User = request.auth
    apps = AppService.list_apps(user)

    # Annotate with active key count
    from apps.projects.models import App
    app_ids = [a.id for a in apps]
    counts = dict(
        App.objects.filter(id__in=app_ids)
        .annotate(
            key_count=Count(
                "api_keys",
                filter=Q(api_keys__is_revoked=False),
            )
        )
        .values_list("id", "key_count")
    )

    return [
        AppListResponse(
            id=a.id,
            name=a.name,
            slug=a.slug,
            description=a.description,
            api_key_count=counts.get(a.id, 0),
            created_at=a.created_at,
        )
        for a in apps
    ]


@router.get("/{app_slug}", response=AppResponse)
def get_app(request: HttpRequest, app_slug: str):
    user: User = request.auth
    app = AppService.get_app_by_slug(user, app_slug)
    return AppResponse(
        id=app.id,
        name=app.name,
        slug=app.slug,
        description=app.description,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.patch("/{app_slug}", response=AppResponse)
def update_app(request: HttpRequest, app_slug: str, data: UpdateAppRequest):
    user: User = request.auth
    app = AppService.update_app(user, app_slug, data.name, data.description)
    return AppResponse(
        id=app.id,
        name=app.name,
        slug=app.slug,
        description=app.description,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.delete("/{app_slug}", response=MessageResponse)
def delete_app(request: HttpRequest, app_slug: str):
    user: User = request.auth
    AppService.delete_app(user, app_slug)
    return {"message": "App deleted"}


# ── App-scoped API Keys ──────────────────────────────────────────────


@router.post("/{app_slug}/api-keys", response={201: CreateApiKeyResponse})
def create_api_key(request: HttpRequest, app_slug: str, data: CreateApiKeyRequest):
    user: User = request.auth
    app = AppService.get_app_by_slug(user, app_slug)
    if not data.name or not data.name.strip():
        raise ValidationError("API key name is required")
    raw_key, api_key = ApiKeyService.create_key(app, data.name.strip())
    return 201, CreateApiKeyResponse(
        key=raw_key,
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        created_at=api_key.created_at,
    )


@router.get("/{app_slug}/api-keys", response=list[ApiKeyResponse])
def list_api_keys(request: HttpRequest, app_slug: str):
    user: User = request.auth
    app = AppService.get_app_by_slug(user, app_slug)
    keys = ApiKeyService.list_keys(app)
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            prefix=k.prefix,
            last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/{app_slug}/api-keys/{key_id}", response=MessageResponse)
def revoke_api_key(request: HttpRequest, app_slug: str, key_id: str):
    user: User = request.auth
    app = AppService.get_app_by_slug(user, app_slug)
    from core.exceptions.base import NotFoundError
    revoked = ApiKeyService.revoke_key(app, key_id)
    if not revoked:
        raise NotFoundError("API key not found")
    return {"message": "API key revoked"}

