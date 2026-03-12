"""
LuxeLife API — Messaging routes.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import paginated_response, success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import generate_cuid
from app.models.supporting import Message
from app.models.user import User

router = APIRouter(prefix="/messaging", tags=["Messaging"])


class SendMessageRequest(BaseModel):
    content: str = Field(..., max_length=2000)
    content_type: str = Field(default="text", pattern=r"^(text|image|file)$")


def _channel_id(user_a: str, user_b: str) -> str:
    """Generate a deterministic channel ID for two users."""
    return f"ch_{'_'.join(sorted([user_a, user_b]))}"


@router.get("/channels")
async def list_channels(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Get all chat channels for the current user."""
    result = await db.execute(
        select(Message.channel_id, func.max(Message.created_at).label("last_at"))
        .where(or_(Message.sender_id == user.id, Message.receiver_id == user.id))
        .group_by(Message.channel_id)
        .order_by(func.max(Message.created_at).desc())
    )
    channels = []
    for row in result.all():
        unread = (await db.execute(
            select(func.count(Message.id)).where(
                Message.channel_id == row.channel_id,
                Message.receiver_id == user.id,
                Message.read_at.is_(None),
            )
        )).scalar() or 0
        channels.append({"channel_id": row.channel_id, "last_activity": str(row.last_at), "unread": unread})
    return success_response(channels)


@router.get("/channels/{channel_id}/messages")
async def get_messages(
    channel_id: str, page: int = Query(1, ge=1), limit: int = Query(30, ge=1, le=100),
    _user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Get messages in a channel (paginated)."""
    query = select(Message).where(Message.channel_id == channel_id)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(query.order_by(Message.created_at.desc()).offset((page - 1) * limit).limit(limit))
    msgs = [{"id": m.id, "sender_id": m.sender_id, "receiver_id": m.receiver_id,
             "content": m.content, "content_type": m.content_type,
             "read_at": str(m.read_at) if m.read_at else None,
             "created_at": str(m.created_at)} for m in result.scalars().all()]
    return paginated_response(msgs, total, page, limit)


@router.post("/channels/{receiver_id}/messages", status_code=201)
async def send_message(
    receiver_id: str, body: SendMessageRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Send a message to a user."""
    channel = _channel_id(user.id, receiver_id)
    msg = Message(id=generate_cuid(), sender_id=user.id, receiver_id=receiver_id,
                  channel_id=channel, content=body.content, content_type=body.content_type)
    db.add(msg)
    await db.flush()
    return success_response({"id": msg.id, "channel_id": channel, "content": msg.content, "created_at": str(msg.created_at)})


@router.patch("/channels/{channel_id}/read")
async def mark_channel_read(
    channel_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Mark all messages in a channel as read."""
    from datetime import datetime, timezone
    await db.execute(
        update(Message).where(
            Message.channel_id == channel_id, Message.receiver_id == user.id, Message.read_at.is_(None)
        ).values(read_at=datetime.now(timezone.utc))
    )
    await db.flush()
    return success_response({"message": "Channel marked as read"})
