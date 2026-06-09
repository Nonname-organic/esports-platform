import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationSchema(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: Optional[str]
    is_read: bool
    action_url: Optional[str]
    metadata: Optional[dict] = None
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    type: str
    title: str
    body: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Optional[dict] = None


class UnreadCountSchema(BaseModel):
    count: int
