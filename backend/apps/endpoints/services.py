from django.db import transaction

from core.exceptions.base import NotFoundError, ValidationError, ConflictError

from .models import Endpoint


class EndpointService:
    @staticmethod
    @transaction.atomic
    def create_endpoint(app, path: str, method: str = "GET", description: str = "") -> Endpoint:
        path = path.strip()
        if not path:
            raise ValidationError("Endpoint path is required")

        method = method.upper()
        if method not in Endpoint.Method.values:
            raise ValidationError(f"Invalid method: {method}")

        if Endpoint.objects.filter(app=app, path=path, method=method, is_active=True).exists():
            raise ConflictError(f"{method} {path} already exists")

        return Endpoint.objects.create(
            app=app,
            path=path,
            method=method,
            description=description.strip(),
        )

    @staticmethod
    def list_endpoints(app) -> list[Endpoint]:
        return list(Endpoint.objects.for_app(app))

    @staticmethod
    def get_endpoint(app, endpoint_id: str) -> Endpoint:
        try:
            return Endpoint.objects.get(id=endpoint_id, app=app, is_active=True)
        except Endpoint.DoesNotExist:
            raise NotFoundError("Endpoint not found")

    @staticmethod
    @transaction.atomic
    def update_endpoint(
        app, endpoint_id: str, path: str | None = None,
        method: str | None = None, description: str | None = None,
    ) -> Endpoint:
        endpoint = EndpointService.get_endpoint(app, endpoint_id)

        if path is not None:
            path = path.strip()
            if not path:
                raise ValidationError("Endpoint path is required")
            endpoint.path = path

        if method is not None:
            method = method.upper()
            if method not in Endpoint.Method.values:
                raise ValidationError(f"Invalid method: {method}")
            endpoint.method = method

        if description is not None:
            endpoint.description = description.strip()

        endpoint.save()
        return endpoint

    @staticmethod
    @transaction.atomic
    def delete_endpoint(app, endpoint_id: str) -> None:
        endpoint = EndpointService.get_endpoint(app, endpoint_id)
        endpoint.is_active = False
        endpoint.save(update_fields=["is_active", "updated_at"])
