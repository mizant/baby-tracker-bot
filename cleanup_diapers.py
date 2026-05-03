"""
Script to delete invalid diaper records with type='stats'
"""
import asyncio
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import DATABASE_URL
from app.models import Diaper, Event


async def cleanup_invalid_diapers():
    """Delete all diaper records with invalid type"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Find invalid diapers
        result = await session.execute(
            select(Diaper).where(Diaper.diaper_type == "stats")
        )
        invalid_diapers = result.scalars().all()

        if not invalid_diapers:
            print("✓ No invalid diaper records found")
            return

        print(
            f"Found {len(invalid_diapers)} invalid diaper record(s) with type='stats'")

        # Delete invalid diapers and their events
        for diaper in invalid_diapers:
            print(
                f"  Deleting diaper id={diaper.id}, created_at={diaper.created_at}")

            # Delete associated events
            await session.execute(
                delete(Event).where(
                    Event.event_type == "diaper",
                    Event.record_id == diaper.id
                )
            )

            # Delete the diaper
            await session.delete(diaper)

        await session.commit()
        print("✓ Cleanup completed!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_invalid_diapers())
