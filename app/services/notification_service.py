"""
LuxeLife API — Notification service.
"""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import generate_cuid
from app.models.notification import Notification
from app.models.user import User


class NotificationService:

    @staticmethod
    async def create(db: AsyncSession, *, user_id: str, type: str, title: str, body: str, icon: str | None = None, action_label: str | None = None, action_target: str | None = None) -> dict:
        notif = Notification(
            id=generate_cuid(), user_id=user_id, type=type, title=title,
            body=body, icon=icon, action_label=action_label, action_target=action_target,
        )
        db.add(notif)
        await db.flush()
        return _to_dict(notif)

    @staticmethod
    async def list_notifications(db: AsyncSession, user_id: str, *, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
        query = select(Notification).where(Notification.user_id == user_id)
        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
        query = query.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await db.execute(query)
        return [_to_dict(n) for n in result.scalars().all()], total

    @staticmethod
    async def mark_read(db: AsyncSession, notification_id: str, user_id: str) -> dict:
        result = await db.execute(select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id))
        notif = result.scalar_one_or_none()
        if not notif:
            raise NotFoundError("Notification")
        notif.unread = False
        await db.flush()
        return _to_dict(notif)

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: str) -> dict:
        await db.execute(
            update(Notification).where(Notification.user_id == user_id, Notification.unread == True).values(unread=False)
        )
        await db.flush()
        return {"message": "All notifications marked as read"}

    @staticmethod
    async def unread_count(db: AsyncSession, user_id: str) -> int:
        result = await db.execute(
            select(func.count(Notification.id)).where(Notification.user_id == user_id, Notification.unread == True)
        )
        return result.scalar() or 0


def _to_dict(n: Notification) -> dict:
    return {
        "id": n.id, "type": n.type, "title": n.title, "body": n.body,
        "icon": n.icon, "unread": n.unread, "action_label": n.action_label,
        "action_target": n.action_target, "created_at": str(n.created_at),
    }
