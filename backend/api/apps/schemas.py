from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Schema


class CreateAppRequest(Schema):
    name: str
    description: str = ""


class UpdateAppRequest(Schema):
    name: Optional[str] = None
    description: Optional[str] = None


class AppResponse(Schema):
    id: UUID
    name: str
    slug: str
    description: str
    created_at: datetime
    updated_at: datetime


class AppListResponse(Schema):
    id: UUID
    name: str
    slug: str
    description: str
    api_key_count: int
    created_at: datetime


class CreateApiKeyRequest(Schema):
    name: str


class ApiKeyResponse(Schema):
    id: UUID
    name: str
    prefix: str
    last_used_at: Optional[datetime] = None
    created_at: datetime


class CreateApiKeyResponse(Schema):
    key: str
    id: UUID
    name: str
    prefix: str
    created_at: datetime


class MessageResponse(Schema):
    message: str
