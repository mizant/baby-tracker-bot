from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from app.keyboards import get_stats_menu, get_main_menu
from app.services.stats import get_feedings, get_sleep_sessions, get_diapers, get_weights
from app.services.formatters import format_time, format_duration

router = Router()


@router.callback_query(F.data == "stats")
async def show_stats_menu_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📊 Выберите период статистики:",
        reply_markup=get_stats_menu()
    )
    await callback.answer()


async def build_stats_message(session, user_id, start_date, end_date, period_name):
    from app.models import Feeding, SleepSession, Diaper, Weight
    from sqlalchemy import select

    # Feedings
    feedings = await get_feedings(session, user_id, start_date, end_date)
    feeding_count = len(feedings)

    # Sleep
    sessions = await get_sleep_sessions(session, user_id, start_date, end_date)
    completed_sessions = [s for s in sessions if s.ended_at is not None]
    total_sleep_seconds = sum(
        (s.ended_at - s.started_at).total_seconds()
        for s in completed_sessions
    )
    last_session = sessions[0] if sessions else None

    # Diapers
    diapers = await get_diapers(session, user_id, start_date, end_date)
    wet_count = sum(1 for d in diapers if d.diaper_type in ["wet", "both"])
    dirty_count = sum(1 for d in diapers if d.diaper_type in ["dirty", "both"])

    # Weight - get all weights, not limited by period
    all_weights = await get_weights(session, user_id, limit=1)
    last_weight = all_weights[0] if all_weights else None

    # Build message
    message = f"📊 <b>Статистика: {period_name}</b>\n\n"

    # Feeding stats - show all feeding times
    message += "🍼 <b>Кормления</b>\n"
    if feeding_count > 0:
        message += f"• Количество: {feeding_count}\n"
        message += "• Время кормлений:\n"
        for i, feeding in enumerate(feedings, 1):
            message += f"  {i}. {format_time(feeding.created_at)}\n"
    else:
        message += "• Еще нет записей\n"

    message += "\n"

    # Sleep stats - show all sleep periods
    message += "😴 <b>Сон</b>\n"
    if completed_sessions:
        message += f"• Периодов: {len(completed_sessions)}\n"
        message += f"• Общее время: {format_duration(total_sleep_seconds)}\n"
        message += "• Периоды сна:\n"
        for i, session in enumerate(completed_sessions, 1):
            start = format_time(session.started_at)
            end = format_time(session.ended_at)
            duration = format_duration(
                (session.ended_at - session.started_at).total_seconds())
            message += f"  {i}. {start} - {end} ({duration})\n"
    else:
        message += "• Еще нет записей\n"

    message += "\n"

    # Diaper stats
    message += "🧷 <b>Подгузники</b>\n"
    if diapers:
        message += f"• Мокрые: {wet_count}\n"
        message += f"• Грязные: {dirty_count}\n"
        message += f"• Всего: {len(diapers)}\n"
    else:
        message += "• Еще нет записей\n"

    message += "\n"

    # Weight stats - simplified for today
    message += "⚖️ <b>Вес</b>\n"
    if last_weight:
        if period_name == "Сегодня":
            message += f"• Вес сегодня: {last_weight.weight_g:.0f} г\n"
        else:
            message += f"• Последняя запись: {last_weight.weight_g:.0f} г\n"
            message += f"• Время: {format_time(last_weight.created_at)}\n"
    else:
        message += "• Еще нет записей\n"

    return message


@router.callback_query(F.data == "stats_today")
async def show_today_stats(callback: types.CallbackQuery, session: AsyncSession):
    now = datetime.utcnow()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)

    message = await build_stats_message(session, callback.from_user.id, start_date, end_date, "Сегодня")

    await callback.message.edit_text(
        message,
        reply_markup=get_stats_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "stats_yesterday")
async def show_yesterday_stats(callback: types.CallbackQuery, session: AsyncSession):
    now = datetime.utcnow()
    yesterday_start = (now - timedelta(days=1)).replace(hour=0,
                                                        minute=0, second=0, microsecond=0)
    yesterday_end = now.replace(hour=0, minute=0, second=0, microsecond=0)

    message = await build_stats_message(session, callback.from_user.id, yesterday_start, yesterday_end, "Вчера")

    await callback.message.edit_text(
        message,
        reply_markup=get_stats_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "stats_week")
async def show_week_stats(callback: types.CallbackQuery, session: AsyncSession):
    now = datetime.utcnow()
    week_start = (now - timedelta(days=7)).replace(hour=0,
                                                   minute=0, second=0, microsecond=0)

    message = await build_stats_message(session, callback.from_user.id, week_start, now, "За неделю")

    await callback.message.edit_text(
        message,
        reply_markup=get_stats_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "stats_month")
async def show_month_stats(callback: types.CallbackQuery, session: AsyncSession):
    now = datetime.utcnow()
    month_start = (now - timedelta(days=30)).replace(hour=0,
                                                     minute=0, second=0, microsecond=0)

    message = await build_stats_message(session, callback.from_user.id, month_start, now, "За месяц")

    await callback.message.edit_text(
        message,
        reply_markup=get_stats_menu(),
        parse_mode="HTML"
    )
    await callback.answer()
