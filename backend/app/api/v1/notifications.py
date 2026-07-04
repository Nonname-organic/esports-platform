import uuid
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.dependencies import Cache, CurrentUser, DBSession
from app.schemas.common import ListResponse, Meta, Response
from app.schemas.notification import NotificationSchema, UnreadCountSchema
from app.services.notification_service import NotificationService
from app.notifications.preferences import PreferenceService

router = APIRouter(prefix="/notifications", tags=["通知"])


# ── 通知設定（機能③ / ADR-0010: JSONBはPreferenceServiceに隠蔽・DTOで受け渡し） ──
class NotificationPrefsUpdate(BaseModel):
    channels: Optional[dict[str, bool]] = None
    categories: Optional[dict[str, bool]] = None


@router.get("/preferences", response_model=Response[dict])
async def get_notification_preferences(db: DBSession, current_user: CurrentUser):
    dto = await PreferenceService(db).get_preferences(current_user.id)
    return Response(data=dto.to_dict(), meta=None)


@router.patch("/preferences", response_model=Response[dict])
async def update_notification_preferences(
    data: NotificationPrefsUpdate, db: DBSession, current_user: CurrentUser,
):
    dto = await PreferenceService(db).update_preferences(
        current_user.id, channels=data.channels, categories=data.categories,
    )
    return Response(data=dto.to_dict(), meta=None)


@router.get("", response_model=ListResponse[NotificationSchema])
async def list_notifications(
    db: DBSession,
    cache: Cache,
    current_user: CurrentUser,
    unread: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    cursor: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
):
    service = NotificationService(db, cache)
    notifs, has_next = await service.list_for_user(
        current_user.id, only_unread=unread, search=search, limit=limit, cursor=cursor
    )
    items = [NotificationSchema(**service.to_schema(n)) for n in notifs]
    next_cursor = str(notifs[-1].id) if has_next and notifs else None
    return ListResponse(data=items, meta=Meta(has_next=has_next, cursor=next_cursor))


@router.get("/unread-count", response_model=Response[UnreadCountSchema])
async def unread_count(db: DBSession, cache: Cache, current_user: CurrentUser):
    service = NotificationService(db, cache)
    count = await service.unread_count(current_user.id)
    return Response(data=UnreadCountSchema(count=count), meta=None)


@router.patch("/{notification_id}/read", status_code=204)
async def mark_read(
    notification_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser
):
    service = NotificationService(db, cache)
    await service.mark_read(current_user.id, notification_id)


@router.patch("/read-all", status_code=204)
async def mark_all_read(db: DBSession, cache: Cache, current_user: CurrentUser):
    service = NotificationService(db, cache)
    await service.mark_all_read(current_user.id)


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: uuid.UUID, db: DBSession, cache: Cache, current_user: CurrentUser
):
    service = NotificationService(db, cache)
    await service.delete(current_user.id, notification_id)
