from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from pytz import timezone
from app.config import TIMEZONE
from app.keyboards import get_feeding_menu, get_main_menu, get_cancel_keyboard
from app.models import Feeding, Event
from app.services.stats import get_feedings, get_active_feeding_session, get_last_feeding
from app.services.formatters import format_time, format_duration
from app.config import FAMILY_USER_ID

router = Router()


class FeedingState(StatesGroup):
    waiting_for_start = State()
    waiting_for_end = State()


@router.callback_query(F.data == "feeding")
async def show_feeding_menu(callback: types.CallbackQuery, session: AsyncSession):
    # Get last feeding info
    last_feeding = await get_last_feeding(session, FAMILY_USER_ID)
    last_info = ""

    if last_feeding:
        if last_feeding.ended_at:
            # Completed feeding
            last_info = f"\n\n📋 Последнее кормление завершено в {format_time(last_feeding.ended_at)}"
        else:
            # Active feeding
            last_info = f"\n\n🔴 Кормление начато в {format_time(last_feeding.started_at)} (активное)"
    else:
        last_info = "\n\n📋 Еще нет записей о кормлении"

    await callback.message.edit_text(
        f"🍼 Выберите действие:{last_info}",
        reply_markup=get_feeding_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "feeding_started")
async def feeding_started(callback: types.CallbackQuery, session: AsyncSession):
    # Check if there's already an active session
    import logging
    logging.info(f"=== FEEDING STARTED ===")
    logging.info(
        f"Checking for active feeding session for user {FAMILY_USER_ID}")

    active_session = await get_active_feeding_session(session, FAMILY_USER_ID)

    logging.info(f"Active session found: {active_session}")
    if active_session:
        logging.info(f"  started_at: {active_session.started_at}")
        logging.info(f"  ended_at: {active_session.ended_at}")

    if active_session:
        await callback.answer("⚠️ Уже есть активная сессия кормления!", show_alert=True)
        return

    feeding = Feeding(
        user_id=FAMILY_USER_ID,
        started_at=datetime.now(timezone(TIMEZONE))
    )
    session.add(feeding)
    await session.flush()

    logging.info(f"Created new feeding session with id={feeding.id}")
    logging.info(
        f"  started_at: {feeding.started_at} (tzinfo: {feeding.started_at.tzinfo})")

    event = Event(
        user_id=FAMILY_USER_ID,
        event_type="feeding",
        record_id=feeding.id,
        created_at=datetime.now(timezone(TIMEZONE))
    )
    session.add(event)
    await session.commit()

    logging.info(f"Feeding session saved successfully")

    await callback.message.edit_text(
        f"🍼 Кормление началось в {format_time(feeding.started_at)}\n"
        f"Нажмите 'Закончить кормление', когда закончите.",
        reply_markup=get_feeding_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "feeding_ended")
async def feeding_ended(callback: types.CallbackQuery, session: AsyncSession):
    import logging
    logging.info(f"=== FEEDING ENDED ===")
    logging.info(
        f"Looking for active feeding session for user {FAMILY_USER_ID}")

    active_session = await get_active_feeding_session(session, FAMILY_USER_ID)

    logging.info(f"Active session found: {active_session}")
    if active_session:
        logging.info(
            f"  started_at: {active_session.started_at} (tzinfo: {active_session.started_at.tzinfo})")
        logging.info(f"  ended_at: {active_session.ended_at}")

    if not active_session:
        # Debug: check all feedings to see what's in the DB
        from sqlalchemy import select
        from app.models import Feeding
        result = await session.execute(
            select(Feeding)
            .where(Feeding.user_id == FAMILY_USER_ID)
            .order_by(Feeding.started_at.desc())
            .limit(5)
        )
        recent_feedings = result.scalars().all()
        logging.info(f"Last 5 feedings in DB:")
        for f in recent_feedings:
            logging.info(
                f"  id={f.id}, started_at={f.started_at} (tzinfo: {f.started_at.tzinfo}), ended_at={f.ended_at}")

        await callback.answer("⚠️ Нет активной сессии кормления! Сначала нажмите 'Начать кормление'.", show_alert=True)
        return

    active_session.ended_at = datetime.now(timezone(TIMEZONE))
    await session.commit()

    # Record event
    event = Event(
        user_id=FAMILY_USER_ID,
        event_type="feeding",
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

    # Get today's feeding stats
    tz_local = timezone(TIMEZONE)
    now = datetime.now(tz_local)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_feedings = await get_feedings(session, FAMILY_USER_ID, today_start, today_end)
    completed_feedings = [f for f in today_feedings if f.ended_at is not None]
    count = len(completed_feedings)

    try:
        await callback.message.edit_text(
            f"✅ Кормление завершено в {format_time(active_session.ended_at)}\n"
            f"⏱️ Длительность: {format_duration(duration)}\n\n"
            f"📊 Сегодня:\n"
            f"• Кормлений: {count}",
            reply_markup=get_feeding_menu()
        )
    except Exception:
        await callback.message.answer(
            f"✅ Кормление завершено в {format_time(active_session.ended_at)}\n"
            f"⏱️ Длительность: {format_duration(duration)}\n\n"
            f"📊 Сегодня:\n"
            f"• Кормлений: {count}",
            reply_markup=get_feeding_menu()
        )
    await callback.answer()


@router.callback_query(F.data == "feeding_manual")
async def feeding_manual(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(FeedingState.waiting_for_start)
    await callback.message.edit_text(
        "✏️ Введите время начала кормления:\n"
        "ЧЧ:ММ\n"
        "(например: 14:00)",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(FeedingState.waiting_for_start, F.text)
async def process_feeding_start(message: types.Message, session: AsyncSession, state: FSMContext):
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
        await state.set_state(FeedingState.waiting_for_end)

        await message.answer(
            "✅ Время начала записано.\n\n"
            "Теперь введите время окончания:\n"
            "ЧЧ:ММ",
            reply_markup=get_cancel_keyboard()
        )
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Используйте: ЧЧ:ММ")


@router.message(FeedingState.waiting_for_end, F.text)
async def process_feeding_end(message: types.Message, session: AsyncSession, state: FSMContext):
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

        # Create feeding session
        feeding = Feeding(
            user_id=FAMILY_USER_ID,
            started_at=start_time,
            ended_at=end_time
        )
        session.add(feeding)
        await session.flush()

        event = Event(
            user_id=FAMILY_USER_ID,
            event_type="feeding",
            record_id=feeding.id,
            created_at=datetime.utcnow()
        )
        session.add(event)
        await session.commit()

        # Calculate duration
        duration = (end_time - start_time).total_seconds()

        await state.clear()

        await message.answer(
            f"✅ Кормление записано:\n"
            f"Начало: {start_time.strftime('%H:%M')}\n"
            f"Конец: {end_time.strftime('%H:%M')}\n"
            f"⏱️ Длительность: {format_duration(duration)}\n\n"
            f"Выберите действие:",
            reply_markup=get_main_menu()
        )
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Используйте: ЧЧ:ММ")


@router.callback_query(F.data == "feed_delete_last")
async def delete_last_feeding(callback: types.CallbackQuery, session: AsyncSession):
    # Get the most recent feeding event for this user
    result = await session.execute(
        select(Event)
        .where(Event.user_id == FAMILY_USER_ID, Event.event_type == "feeding")
        .order_by(Event.created_at.desc())
        .limit(1)
    )
    last_event = result.scalar_one_or_none()

    if not last_event:
        await callback.answer("❌ Нет записей о кормлении для удаления", show_alert=True)
        return

    # Check if event is older than 24 hours
    if (datetime.utcnow() - last_event.created_at).total_seconds() > 86400:
        await callback.answer("❌ Можно удалять только записи за последние 24 часа", show_alert=True)
        return

    # Get the feeding record
    result = await session.execute(select(Feeding).where(Feeding.id == last_event.record_id))
    feeding = result.scalar_one_or_none()

    if feeding:
        # Delete the feeding and event
        start_time = format_time(feeding.started_at)
        if feeding.ended_at:
            end_time = format_time(feeding.ended_at)
            duration = format_duration(
                (feeding.ended_at - feeding.started_at).total_seconds())
            deleted_info = f"Начало: {start_time}\nКонец: {end_time}\nДлительность: {duration}"
        else:
            deleted_info = f"Начало: {start_time}\n(активная сессия)"

        await session.delete(feeding)
        await session.delete(last_event)
        await session.commit()

        await callback.message.edit_text(
            f"❌ Запись о кормлении удалена:\n\n{deleted_info}",
            reply_markup=get_feeding_menu()
        )
    else:
        await callback.answer("❌ Запись не найдена", show_alert=True)

    await callback.answer()
