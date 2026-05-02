from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Feeding, SleepSession, Diaper, Weight


async def get_feedings(session: AsyncSession, user_id: int, start_date: datetime, end_date: datetime):
    result = await session.execute(
        select(Feeding)
        .where(
            and_(
                Feeding.user_id == user_id,
                Feeding.created_at >= start_date,
                Feeding.created_at < end_date
            )
        )
        .order_by(Feeding.created_at.desc())
    )
    return result.scalars().all()


async def get_sleep_sessions(session: AsyncSession, user_id: int, start_date: datetime, end_date: datetime):
    result = await session.execute(
        select(SleepSession)
        .where(
            and_(
                SleepSession.user_id == user_id,
                SleepSession.started_at >= start_date,
                SleepSession.started_at < end_date
            )
        )
        .order_by(SleepSession.started_at.desc())
    )
    return result.scalars().all()


async def get_diapers(session: AsyncSession, user_id: int, start_date: datetime, end_date: datetime):
    result = await session.execute(
        select(Diaper)
        .where(
            and_(
                Diaper.user_id == user_id,
                Diaper.created_at >= start_date,
                Diaper.created_at < end_date
            )
        )
        .order_by(Diaper.created_at.desc())
    )
    return result.scalars().all()


async def get_weights(session: AsyncSession, user_id: int, limit: int = 2):
    result = await session.execute(
        select(Weight)
        .where(Weight.user_id == user_id)
        .order_by(Weight.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_active_sleep_session(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(SleepSession)
        .where(
            SleepSession.user_id == user_id,
            SleepSession.ended_at == None
        )
        .order_by(SleepSession.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
