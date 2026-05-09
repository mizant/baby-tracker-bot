from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from pytz import timezone
from app.config import FAMILY_USER_ID, TIMEZONE
from app.services.stats import get_last_feeding, get_last_sleep, get_last_diaper, get_weights, get_active_sleep_session, get_active_feeding_session
from app.services.formatters import format_time

router = Router()


@router.message(Command("now"))
async def cmd_now(message: types.Message, session: AsyncSession):
    """Handle /now command"""
    tz_local = timezone(TIMEZONE)
    now = datetime.now(tz_local)

    message_text = await build_status_message(session, now)

    await message.answer(
        message_text,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "now")
async def show_current_status(callback: types.CallbackQuery, session: AsyncSession):
    """Show current status of the baby - what's happening right now"""
    tz_local = timezone(TIMEZONE)
    now = datetime.now(tz_local)

    message_text = await build_status_message(session, now)

    await callback.message.answer(
        message_text,
        parse_mode="HTML"
    )
    await callback.answer()


async def build_status_message(session: AsyncSession, now: datetime) -> str:
    """Build the status message with all baby info"""
    message = "👶 <b>Статус прямо сейчас</b>\n\n"

    # 1. Check active feeding
    active_feeding = await get_active_feeding_session(session, FAMILY_USER_ID)
    if active_feeding:
        # Make sure both datetimes have the same timezone awareness
        started_at = active_feeding.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=now.tzinfo)

        # Check if the feeding session is recent (within last 24 hours)
        feeding_age = (now - started_at).total_seconds()
        if feeding_age > 86400:  # More than 24 hours old
            # Treat as not actively feeding
            active_feeding = None
        else:
            feeding_duration = (now - started_at).total_seconds()
            feeding_minutes = int(feeding_duration // 60)
            feeding_hours = feeding_minutes // 60
            feeding_mins = feeding_minutes % 60

            if feeding_hours > 0:
                message += f"🍼 <b>Кормление:</b> {feeding_hours} ч {feeding_mins} мин назад\n"
            else:
                message += f"🍼 <b>Кормление:</b> {feeding_mins} мин назад\n"

    if not active_feeding:
        last_feeding = await get_last_feeding(session, FAMILY_USER_ID)
        if last_feeding:
            # If feeding has end time, use that, otherwise use start time
            feeding_time = last_feeding.ended_at if last_feeding.ended_at else last_feeding.started_at
            # Make sure both datetimes have the same timezone awareness
            if feeding_time.tzinfo is None:
                feeding_time = feeding_time.replace(tzinfo=now.tzinfo)

            time_diff = (now - feeding_time).total_seconds()
            minutes_ago = int(time_diff // 60)

            if minutes_ago < 60:
                message += f"🍼 <b>Последнее кормление:</b> {minutes_ago} мин назад\n"
            else:
                hours_ago = minutes_ago // 60
                mins = minutes_ago % 60
                message += f"🍼 <b>Последнее кормление:</b> {hours_ago} ч {mins} мин назад\n"
        else:
            message += "🍼 <b>Кормление:</b> еще нет записей\n"

    # 2. Check active sleep
    active_sleep = await get_active_sleep_session(session, FAMILY_USER_ID)
    if active_sleep:
        # Make sure both datetimes have the same timezone awareness
        started_at = active_sleep.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=now.tzinfo)

        # Check if the sleep session is recent (within last 24 hours)
        sleep_age = (now - started_at).total_seconds()
        if sleep_age > 86400:  # More than 24 hours old
            # Treat as not actively sleeping
            active_sleep = None
        else:
            sleep_duration = (now - started_at).total_seconds()
            sleep_minutes = int(sleep_duration // 60)
            sleep_hours = sleep_minutes // 60
            sleep_mins = sleep_minutes % 60

            if sleep_hours > 0:
                message += f"😴 <b>Спит уже:</b> {sleep_hours} ч {sleep_mins} мин\n"
            else:
                message += f"😴 <b>Спит уже:</b> {sleep_mins} мин\n"

    if not active_sleep:
        last_sleep = await get_last_sleep(session, FAMILY_USER_ID)
        if last_sleep:
            sleep_time = last_sleep.ended_at if last_sleep.ended_at else last_sleep.started_at
            # Make sure both datetimes have the same timezone awareness
            if sleep_time.tzinfo is None:
                sleep_time = sleep_time.replace(tzinfo=now.tzinfo)

            time_diff = (now - sleep_time).total_seconds()
            minutes_ago = int(time_diff // 60)

            if minutes_ago < 60:
                message += f"😴 <b>Последний сон:</b> {minutes_ago} мин назад\n"
            else:
                hours_ago = minutes_ago // 60
                mins = minutes_ago % 60
                message += f"😴 <b>Последний сон:</b> {hours_ago} ч {mins} мин назад\n"
        else:
            message += "😴 <b>Сон:</b> еще нет записей\n"

    # 3. Last diaper change
    from app.models import Diaper
    from sqlalchemy import select

    result = await session.execute(
        select(Diaper)
        .where(Diaper.user_id == FAMILY_USER_ID)
        .order_by(Diaper.created_at.desc())
        .limit(1)
    )
    last_diaper = result.scalar_one_or_none()

    if last_diaper:
        # Make sure both datetimes have the same timezone awareness
        created_at = last_diaper.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=now.tzinfo)

        time_diff = (now - created_at).total_seconds()
        minutes_ago = int(time_diff // 60)

        type_text = {
            "wet": "💧 Мокрый",
            "dirty": "💩 Грязный",
            "both": "💧💩 Мокрый + грязный"
        }
        diaper_type = type_text.get(
            last_diaper.diaper_type, last_diaper.diaper_type)

        if minutes_ago < 60:
            message += f"🧷 <b>Подгузник:</b> {minutes_ago} мин назад ({diaper_type})\n"
        else:
            hours_ago = minutes_ago // 60
            mins = minutes_ago % 60
            message += f"🧷 <b>Подгузник:</b> {hours_ago} ч {mins} мин назад ({diaper_type})\n"
    else:
        message += "🧷 <b>Подгузник:</b> еще нет записей\n"

    return message
