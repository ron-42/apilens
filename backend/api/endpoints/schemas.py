from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Schema


class CreateEndpointRequest(Schema):
    path: str
    method: str = "GET"
    description: str = ""


class UpdateEndpointRequest(Schema):
    path: Optional[str] = None
    method: Optional[str] = None
    description: Optional[str] = None


class EndpointResponse(Schema):
    id: UUID
    path: str
    method: str
    description: str
    is_active: bool
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
