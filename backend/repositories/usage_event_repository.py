import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.usage_event import UsageEvent, UsageEventType
from models.user import User


class UsageEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(self, user_id: uuid.UUID, event_type: UsageEventType) -> UsageEvent:
        event = UsageEvent(user_id=user_id, event_type=event_type.value)
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def count_by_type(self, event_type: UsageEventType, exclude_test_users: bool = True) -> int:
        query = select(func.count()).select_from(UsageEvent).where(UsageEvent.event_type == event_type.value)
        if exclude_test_users:
            query = query.join(User, User.id == UsageEvent.user_id).where(User.is_test_user.is_(False))
        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_active_users_since(self, since: datetime, exclude_test_users: bool = True) -> int:
        query = select(func.count(func.distinct(UsageEvent.user_id))).where(UsageEvent.created_at >= since)
        if exclude_test_users:
            query = query.join(User, User.id == UsageEvent.user_id).where(User.is_test_user.is_(False))
        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_for_user(self, user_id: uuid.UUID, event_type: UsageEventType) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(UsageEvent)
            .where(UsageEvent.user_id == user_id, UsageEvent.event_type == event_type.value)
        )
        return result.scalar_one()


def days_ago(n: int) -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=n)
