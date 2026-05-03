from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.keyboards import get_diaper_menu, get_main_menu
from app.models import Diaper, Event
from app.services.stats import get_diapers, get_last_diaper
from app.services.formatters import format_time
from app.config import FAMILY_USER_ID

router = Router()


@router.callback_query(F.data == "diaper")
async def show_diaper_menu(callback: types.CallbackQuery, session: AsyncSession):
    # Get last diaper info
    last_diaper = await get_last_diaper(session, FAMILY_USER_ID)
    last_info = ""

    if last_diaper:
        type_text = {
            "wet": "💧 Мокрый",
            "dirty": "💩 Грязный",
            "both": "💧💩 Мокрый + грязный"
        }
        diaper_type = type_text.get(
            last_diaper.diaper_type, last_diaper.diaper_type)
        last_info = f"\n\n📋 Последний подгузник: {diaper_type} в {format_time(last_diaper.created_at)}"
    else:
        last_info = "\n\n📋 Еще нет записей о подгузниках"

    await callback.message.edit_text(
        f"🧷 Выберите тип подгузника:{last_info}",
        reply_markup=get_diaper_menu()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("diaper_") & ~F.data.contains("delete"))
async def process_diaper(callback: types.CallbackQuery, session: AsyncSession):
    diaper_type = callback.data.split("_")[1]

    diaper = Diaper(
        user_id=FAMILY_USER_ID,
        diaper_type=diaper_type,
        created_at=datetime.utcnow()
    )
    session.add(diaper)
    await session.flush()

    event = Event(
        user_id=FAMILY_USER_ID,
        event_type="diaper",
        record_id=diaper.id,
        created_at=datetime.utcnow()
    )
    session.add(event)
    await session.commit()

    # Get today's diaper stats
    today_start = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_diapers = await get_diapers(session, FAMILY_USER_ID, today_start, today_end)
    wet_count = sum(
        1 for d in today_diapers if d.diaper_type in ["wet", "both"])
    dirty_count = sum(
        1 for d in today_diapers if d.diaper_type in ["dirty", "both"])

    type_text = {
        "wet": "💧 Мокрый",
        "dirty": "💩 Грязный",
        "both": "💧💩 Мокрый + грязный"
    }

    await callback.message.edit_text(
        f"✅ Записано: {type_text[diaper_type]} в {format_time(diaper.created_at)}\n\n"
        f"📊 Сегодня:\n"
        f"• Мокрых: {wet_count}\n"
        f"• Грязных: {dirty_count}\n"
        f"• Всего: {len(today_diapers)}",
        reply_markup=get_diaper_menu()
    )
    await callback.answer()


def format_time(dt):
    from app.services.formatters import format_time as ft
    return ft(dt)


@router.callback_query(F.data == "diaper_delete_last")
async def delete_last_diaper(callback: types.CallbackQuery, session: AsyncSession):
    # Get the most recent diaper event for this user
    result = await session.execute(
        select(Event)
        .where(Event.user_id == FAMILY_USER_ID, Event.event_type == "diaper")
        .order_by(Event.created_at.desc())
        .limit(1)
    )
    last_event = result.scalar_one_or_none()

    if not last_event:
        await callback.answer("❌ Нет записей о подгузниках для удаления", show_alert=True)
        return

    # Check if event is older than 24 hours
    if (datetime.utcnow() - last_event.created_at).total_seconds() > 86400:
        await callback.answer("❌ Можно удалять только записи за последние 24 часа", show_alert=True)
        return

    # Get the diaper record
    result = await session.execute(select(Diaper).where(Diaper.id == last_event.record_id))
    diaper = result.scalar_one_or_none()

    if diaper:
        # Delete the diaper and event
        type_text = {
            "wet": "💧 Мокрый",
            "dirty": "💩 Грязный",
            "both": "💧💩 Мокрый + грязный"
        }

        await session.delete(diaper)
        await session.delete(last_event)
        await session.commit()

        await callback.message.edit_text(
            f"❌ Запись о подгузнике удалена:\n\n"
            f"Тип: {type_text[diaper.diaper_type]}\n"
            f"Время: {format_time(diaper.created_at)}",
            reply_markup=get_diaper_menu()
        )
    else:
        await callback.answer("❌ Запись не найдена", show_alert=True)

    await callback.answer()
