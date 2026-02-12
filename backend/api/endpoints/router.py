from django.http import HttpRequest
from ninja import Router

from apps.endpoints.services import EndpointService
from apps.projects.services import AppService
from apps.users.models import User
from core.auth.authentication import jwt_auth

from .schemas import (
    CreateEndpointRequest,
    UpdateEndpointRequest,
    EndpointResponse,
)

router = Router(auth=[jwt_auth])


@router.get("/{app_slug}/endpoints", response=list[EndpointResponse])
def list_endpoints(request: HttpRequest, app_slug: str):
    user: User = request.auth
    app = AppService.get_app_by_slug(user, app_slug)
    endpoints = EndpointService.list_endpoints(app)
    return [EndpointResponse.from_orm(e) for e in endpoints]


@router.post("/{app_slug}/endpoints", response={201: EndpointResponse})
def create_endpoint(request: HttpRequest, app_slug: str, data: CreateEndpointRequest):
    user: User = request.auth
    app = AppService.get_app_by_slug(user, app_slug)
    endpoint = EndpointService.create_endpoint(app, data.path, data.method, data.description)
    return 201, EndpointResponse.from_orm(endpoint)


@router.get("/{app_slug}/endpoints/{endpoint_id}", response=EndpointResponse)
def get_endpoint(request: HttpRequest, app_slug: str, endpoint_id: str):
    user: User = request.auth
    app = AppService.get_app_by_slug(user, app_slug)
    endpoint = EndpointService.get_endpoint(app, endpoint_id)
    return EndpointResponse.from_orm(endpoint)


@router.patch("/{app_slug}/endpoints/{endpoint_id}", response=EndpointResponse)
def update_endpoint(request: HttpRequest, app_slug: str, endpoint_id: str, data: UpdateEndpointRequest):
    user: User = request.auth
    app = AppService.get_app_by_slug(user, app_slug)
    endpoint = EndpointService.update_endpoint(
        app, endpoint_id, data.path, data.method, data.description,
    )
    return EndpointResponse.from_orm(endpoint)


@router.delete("/{app_slug}/endpoints/{endpoint_id}", response={204: None})
def delete_endpoint(request: HttpRequest, app_slug: str, endpoint_id: str):
    user: User = request.auth
    app = AppService.get_app_by_slug(user, app_slug)
    EndpointService.delete_endpoint(app, endpoint_id)
    return 204, None
