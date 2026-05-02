from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.keyboards import get_feeding_menu, get_main_menu, get_cancel_keyboard
from app.models import Feeding, Event
from app.services.stats import get_feedings
from app.services.formatters import format_time

router = Router()


class FeedingState(StatesGroup):
    waiting_for_datetime = State()


@router.callback_query(F.data == "feeding")
async def show_feeding_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🍼 Выберите действие:",
        reply_markup=get_feeding_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "feed_now")
async def feed_now(callback: types.CallbackQuery, session: AsyncSession):
    feeding = Feeding(
        user_id=callback.from_user.id,
        created_at=datetime.utcnow()
    )
    session.add(feeding)
    await session.flush()

    event = Event(
        user_id=callback.from_user.id,
        event_type="feeding",
        record_id=feeding.id,
        created_at=datetime.utcnow()
    )
    session.add(event)
    await session.commit()

    # Get today's stats
    today_start = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_feedings = await get_feedings(session, callback.from_user.id, today_start, today_end)
    count = len(today_feedings)

    await callback.message.edit_text(
        f"✅ Кормление записано в {format_time(feeding.created_at)}\n\n"
        f"📊 Сегодня:\n"
        f"• Кормлений: {count}",
        reply_markup=get_feeding_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "feed_manual_time")
async def feed_manual_time(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(FeedingState.waiting_for_datetime)
    await callback.message.edit_text(
        "✏️ Введите время кормления в формате:\n"
        "ЧЧ:ММ\n"
        "(например: 14:30)",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(FeedingState.waiting_for_datetime, F.text)
async def manual_feeding_time(message: types.Message, session: AsyncSession, state: FSMContext):
    try:
        # Parse time: ЧЧ:ММ
        parts = message.text.strip().split(':')
        if len(parts) != 2:
            await message.answer("❌ Неверный формат. Используйте: ЧЧ:ММ\nПример: 14:30")
            return

        hour, minute = map(int, parts)

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            await message.answer("⚠️ Неверное время. Часы: 0-23, Минуты: 0-59")
            return

        # Create datetime with today's date and specified time
        now = datetime.utcnow()
        feeding_time = now.replace(
            hour=hour, minute=minute, second=0, microsecond=0)

        feeding = Feeding(
            user_id=message.from_user.id,
            created_at=feeding_time
        )
        session.add(feeding)
        await session.flush()

        event = Event(
            user_id=message.from_user.id,
            event_type="feeding",
            record_id=feeding.id,
            created_at=datetime.utcnow()
        )
        session.add(event)
        await session.commit()

        await state.clear()

        # Get today's stats
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        today_feedings = await get_feedings(session, message.from_user.id, today_start, today_end)
        count = len(today_feedings)

        await message.answer(
            f"✅ Кормление записано: {feeding_time.strftime('%H:%M')}\n\n"
            f"📊 Сегодня:\n"
            f"• Кормлений: {count}\n\n"
            f"Выберите действие:",
            reply_markup=get_main_menu()
        )
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Используйте: ЧЧ:ММ\nПример: 14:30")


@router.callback_query(F.data == "feed_delete_last")
async def delete_last_feeding(callback: types.CallbackQuery, session: AsyncSession):
    # Get the most recent feeding event for this user
    result = await session.execute(
        select(Event)
        .where(Event.user_id == callback.from_user.id, Event.event_type == "feeding")
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
        await session.delete(feeding)
        await session.delete(last_event)
        await session.commit()

        await callback.message.edit_text(
            f"❌ Запись о кормлении удалена:\n"
            f"Время: {format_time(feeding.created_at)}",
            reply_markup=get_feeding_menu()
        )
    else:
        await callback.answer("❌ Запись не найдена", show_alert=True)

    await callback.answer()
