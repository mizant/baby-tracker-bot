from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from app.keyboards import get_main_menu
from app.models import Event, Feeding, SleepSession, Diaper, Weight
from app.services.formatters import format_time
from app.config import FAMILY_USER_ID

router = Router()


@router.callback_query(F.data == "undo")
async def undo_last(callback: types.CallbackQuery, session: AsyncSession):
    user_id = FAMILY_USER_ID

    # Get the most recent event for this user
    result = await session.execute(
        select(Event)
        .where(Event.user_id == user_id)
        .order_by(Event.created_at.desc())
        .limit(1)
    )
    last_event = result.scalar_one_or_none()

    if not last_event:
        await callback.answer("❌ Нет записей для удаления", show_alert=True)
        return

    # Check if event is older than 24 hours
    if (datetime.utcnow() - last_event.created_at).total_seconds() > 86400:
        await callback.answer("❌ Можно удалять только записи за последние 24 часа", show_alert=True)
        return

    # Delete the record and event
    record_type = last_event.event_type
    record_id = last_event.record_id

    deleted_info = ""

    if record_type == "feeding":
        result = await session.execute(select(Feeding).where(Feeding.id == record_id))
        feeding = result.scalar_one_or_none()
        if feeding:
            deleted_info = f"🍼 Кормление: {format_time(feeding.started_at)}"
            if feeding.ended_at:
                deleted_info += f" - {format_time(feeding.ended_at)}"
            await session.delete(feeding)

    elif record_type == "sleep":
        result = await session.execute(select(SleepSession).where(SleepSession.id == record_id))
        sleep_session = result.scalar_one_or_none()
        if sleep_session:
            deleted_info = f"😴 Сон: {format_time(sleep_session.started_at)}"
            if sleep_session.ended_at:
                deleted_info += f" - {format_time(sleep_session.ended_at)}"
            await session.delete(sleep_session)

    elif record_type == "diaper":
        result = await session.execute(select(Diaper).where(Diaper.id == record_id))
        diaper = result.scalar_one_or_none()
        if diaper:
            type_text = {"wet": "💧 Мокрый", "dirty": "💩 Грязный",
                         "both": "💧💩 Мокрый + грязный"}
            deleted_info = f"🧷 Подгузник: {type_text[diaper.diaper_type]} в {format_time(diaper.created_at)}"
            await session.delete(diaper)

    elif record_type == "weight":
        result = await session.execute(select(Weight).where(Weight.id == record_id))
        weight = result.scalar_one_or_none()
        if weight:
            deleted_info = f"⚖️ Вес: {weight.weight_g:.0f} г в {format_time(weight.created_at)}"
            await session.delete(weight)

    # Delete the event
    await session.delete(last_event)
    await session.commit()

    await callback.message.edit_text(
        f"❌ Запись удалена:\n\n{deleted_info}",
        reply_markup=get_main_menu()
    )
    await callback.answer()
