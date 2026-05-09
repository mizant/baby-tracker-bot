from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone as tz
from pytz import timezone
from app.config import TIMEZONE
from app.keyboards import get_sleep_menu, get_main_menu, get_cancel_keyboard
from app.models import SleepSession, Event
from app.services.stats import get_sleep_sessions, get_active_sleep_session, get_last_sleep
from app.services.formatters import format_time, format_duration
from app.config import FAMILY_USER_ID

router = Router()


class SleepState(StatesGroup):
    waiting_for_start = State()
    waiting_for_end = State()


@router.callback_query(F.data == "sleep")
async def show_sleep_menu(callback: types.CallbackQuery, session: AsyncSession):
    # Get last sleep info
    last_sleep = await get_last_sleep(session, FAMILY_USER_ID)
    last_info = ""

    if last_sleep:
        if last_sleep.ended_at:
            # Completed sleep
            last_info = f"\n\n📋 Последний сон завершен в {format_time(last_sleep.ended_at)}"
        else:
            # Active sleep
            last_info = f"\n\n🌙 Ребенок спит с {format_time(last_sleep.started_at)} (активная сессия)"
    else:
        last_info = "\n\n📋 Еще нет записей о сне"

    await callback.message.edit_text(
        f"😴 Отслеживание сна:{last_info}",
        reply_markup=get_sleep_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "sleep_started")
async def sleep_started(callback: types.CallbackQuery, session: AsyncSession):
    # Check if there's already an active session
    active_session = await get_active_sleep_session(session, FAMILY_USER_ID)

    if active_session:
        await callback.answer("⚠️ Уже есть активная сессия сна!", show_alert=True)
        return

    sleep_session = SleepSession(
        user_id=FAMILY_USER_ID,
        started_at=datetime.now(timezone(TIMEZONE))
    )
    session.add(sleep_session)
    await session.flush()

    event = Event(
        user_id=FAMILY_USER_ID,
        event_type="sleep",
        record_id=sleep_session.id,
        created_at=datetime.now(timezone(TIMEZONE))
    )
    session.add(event)
    await session.commit()

    await callback.message.edit_text(
        f"😴 Ребенок уснул в {format_time(sleep_session.started_at)}\n"
        f"Нажмите 'Ребенок проснулся', когда проснется.",
        reply_markup=get_sleep_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "sleep_ended")
async def sleep_ended(callback: types.CallbackQuery, session: AsyncSession):
    active_session = await get_active_sleep_session(session, FAMILY_USER_ID)

    if not active_session:
        await callback.answer("⚠️ Нет активной сессии сна! Сначала нажмите 'Ребенок уснул'.", show_alert=True)
        return

    active_session.ended_at = datetime.now(timezone(TIMEZONE))
    await session.commit()

    # Record event
    event = Event(
        user_id=FAMILY_USER_ID,
        event_type="sleep",
        record_id=active_session.id,
        created_at=datetime.now(timezone(TIMEZONE))
    )
    session.add(event)
    await session.commit()

    # Calculate duration - ensure both datetimes have the same timezone awareness
    ended_at = active_session.ended_at
    started_at = active_session.started_at

    # If one has tzinfo and the other doesn't, normalize them
    if ended_at.tzinfo is not None and started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=ended_at.tzinfo)
    elif ended_at.tzinfo is None and started_at.tzinfo is not None:
        ended_at = ended_at.replace(tzinfo=started_at.tzinfo)

    duration = (ended_at - started_at).total_seconds()

    # Get today's sleep stats
    tz_local = timezone(TIMEZONE)
    now = datetime.now(tz_local)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_sessions = await get_sleep_sessions(session, FAMILY_USER_ID, today_start, today_end)
    total_duration = sum(
        (s.ended_at - s.started_at).total_seconds()
        for s in today_sessions
        if s.ended_at is not None
    )

    try:
        await callback.message.edit_text(
            f"☀️ Ребенок проснулся в {format_time(active_session.ended_at)}\n"
            f"⏱️ Длительность сна: {format_duration(duration)}\n\n"
            f"📊 Сегодня:\n"
            f"• Периодов сна: {len([s for s in today_sessions if s.ended_at])}\n"
            f"• Общее время сна: {format_duration(total_duration)}",
            reply_markup=get_sleep_menu()
        )
    except Exception:
        await callback.message.answer(
            f"☀️ Ребенок проснулся в {format_time(active_session.ended_at)}\n"
            f"⏱️ Длительность сна: {format_duration(duration)}\n\n"
            f"📊 Сегодня:\n"
            f"• Периодов сна: {len([s for s in today_sessions if s.ended_at])}\n"
            f"• Общее время сна: {format_duration(total_duration)}",
            reply_markup=get_sleep_menu()
        )
    await callback.answer()


@router.callback_query(F.data == "sleep_manual")
async def sleep_manual(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SleepState.waiting_for_start)
    await callback.message.edit_text(
        "✏️ Введите время начала сна:\n"
        "ЧЧ:ММ\n"
        "(например: 14:00)",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(SleepState.waiting_for_start, F.text)
async def process_sleep_start(message: types.Message, session: AsyncSession, state: FSMContext):
    try:
        parts = message.text.strip().split(':')
        if len(parts) != 2:
            await message.answer("❌ Неверный формат. Используйте: ЧЧ:ММ")
            return

        hour, minute = map(int, parts)

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            await message.answer("⚠️ Неверное время. Часы: 0-23, Минуты: 0-59")
            return

        # Create datetime with today's date and specified time (naive datetime, interpreted as local time)
        now = datetime.utcnow()
        start_time = now.replace(
            hour=hour, minute=minute, second=0, microsecond=0)

        await state.update_data(start_time=start_time)
        await state.set_state(SleepState.waiting_for_end)

        await message.answer(
            "✅ Время начала записано.\n\n"
            "Теперь введите время окончания:\n"
            "ЧЧ:ММ",
            reply_markup=get_cancel_keyboard()
        )
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Используйте: ЧЧ:ММ")


@router.message(SleepState.waiting_for_end, F.text)
async def process_sleep_end(message: types.Message, session: AsyncSession, state: FSMContext):
    try:
        parts = message.text.strip().split(':')
        if len(parts) != 2:
            await message.answer("❌ Неверный формат. Используйте: ЧЧ:ММ")
            return

        hour, minute = map(int, parts)

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            await message.answer("⚠️ Неверное время. Часы: 0-23, Минуты: 0-59")
            return

        # Create datetime with today's date and specified time (naive datetime, interpreted as local time)
        now = datetime.utcnow()
        end_time = now.replace(hour=hour, minute=minute,
                               second=0, microsecond=0)

        data = await state.get_data()
        start_time = data.get('start_time')

        # If end time is before start time, assume it's next day
        if end_time <= start_time:
            end_time = end_time + timedelta(days=1)

        # Create sleep session
        sleep_session = SleepSession(
            user_id=FAMILY_USER_ID,
            started_at=start_time,
            ended_at=end_time
        )
        session.add(sleep_session)
        await session.flush()

        event = Event(
            user_id=FAMILY_USER_ID,
            event_type="sleep",
            record_id=sleep_session.id,
            created_at=datetime.utcnow()
        )
        session.add(event)
        await session.commit()

        # Calculate duration
        duration = (end_time - start_time).total_seconds()

        await state.clear()

        await message.answer(
            f"✅ Сон записан:\n"
            f"Начало: {start_time.strftime('%H:%M')}\n"
            f"Конец: {end_time.strftime('%H:%M')}\n"
            f"⏱️ Длительность: {format_duration(duration)}\n\n"
            f"Выберите действие:",
            reply_markup=get_main_menu()
        )
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Используйте: ЧЧ:ММ")


@router.callback_query(F.data == "sleep_delete_last")
async def delete_last_sleep(callback: types.CallbackQuery, session: AsyncSession):
    # Get the most recent sleep event for this user
    result = await session.execute(
        select(Event)
        .where(Event.user_id == FAMILY_USER_ID, Event.event_type == "sleep")
        .order_by(Event.created_at.desc())
        .limit(1)
    )
    last_event = result.scalar_one_or_none()

    if not last_event:
        await callback.answer("❌ Нет записей о сне для удаления", show_alert=True)
        return

    # Check if event is older than 24 hours
    if (datetime.utcnow() - last_event.created_at).total_seconds() > 86400:
        await callback.answer("❌ Можно удалять только записи за последние 24 часа", show_alert=True)
        return

    # Get the sleep record
    result = await session.execute(select(SleepSession).where(SleepSession.id == last_event.record_id))
    sleep_session = result.scalar_one_or_none()

    if sleep_session:
        # Delete the sleep session and event
        start_time = format_time(sleep_session.started_at)
        if sleep_session.ended_at:
            end_time = format_time(sleep_session.ended_at)
            duration = format_duration(
                (sleep_session.ended_at - sleep_session.started_at).total_seconds())
            deleted_info = f"Начало: {start_time}\nКонец: {end_time}\nДлительность: {duration}"
        else:
            deleted_info = f"Начало: {start_time}\n(активная сессия)"

        await session.delete(sleep_session)
        await session.delete(last_event)
        await session.commit()

        await callback.message.edit_text(
            f"❌ Запись о сне удалена:\n\n{deleted_info}",
            reply_markup=get_sleep_menu()
        )
    else:
        await callback.answer("❌ Запись не найдена", show_alert=True)

    await callback.answer()
