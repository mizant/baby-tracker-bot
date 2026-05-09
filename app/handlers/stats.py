from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import pytz
from aiogram.exceptions import TelegramBadRequest
from app.config import TIMEZONE, FAMILY_USER_ID
from app.keyboards import get_stats_menu, get_main_menu, get_feeding_menu, get_sleep_menu, get_diaper_menu
from app.services.stats import get_feedings, get_sleep_sessions, get_diapers, get_weights
from app.services.formatters import format_time, format_duration, format_datetime
from app.services.weight_chart import create_weight_chart

router = Router()


@router.callback_query(F.data == "stats")
async def show_stats_menu_callback(callback: types.CallbackQuery):
    try:
        await callback.message.edit_text(
            "📊 Выберите период статистики:",
            reply_markup=get_stats_menu()
        )
    except TelegramBadRequest:
        # Message content hasn't changed, ignore error
        pass
    await callback.answer()


async def build_stats_message(session, user_id, start_date, end_date, period_name, detailed=True):
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
        completed_feedings = [f for f in feedings if f.ended_at is not None]
        message += f"• Количество: {len(completed_feedings)}\n"
        if detailed:
            message += "• Периоды кормлений:\n"
            for i, feeding in enumerate(completed_feedings, 1):
                start = format_time(feeding.started_at)
                end = format_time(feeding.ended_at)
                duration = format_duration(
                    (feeding.ended_at - feeding.started_at).total_seconds())
                message += f"  {i}. {start} - {end} ({duration})\n"
    else:
        message += "• Еще нет записей\n"

    message += "\n"

    # Sleep stats - show all sleep periods
    message += "😴 <b>Сон</b>\n"
    if completed_sessions:
        message += f"• Периодов: {len(completed_sessions)}\n"
        message += f"• Общее время: {format_duration(total_sleep_seconds)}\n"
        if detailed:
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
        if period_name.startswith("Сегодня"):
            message += f"• Вес сегодня: {last_weight.weight_g:.0f} г\n"
        else:
            message += f"• Последняя запись: {last_weight.weight_g:.0f} г\n"
            message += f"• Дата: {format_datetime(last_weight.created_at)}\n"
    else:
        message += "• Еще нет записей\n"

    return message


@router.callback_query(F.data == "stats_today")
async def show_today_stats(callback: types.CallbackQuery, session: AsyncSession):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    # Use local time (naive) for comparison since DB stores local time
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)

    date_str = now.strftime("%d.%m.%Y")
    period_name = f"Сегодня ({date_str})"

    message = await build_stats_message(session, FAMILY_USER_ID, start_date, end_date, period_name)

    await callback.message.edit_text(
        message,
        reply_markup=get_stats_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "stats_yesterday")
async def show_yesterday_stats(callback: types.CallbackQuery, session: AsyncSession):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    # Use local time (naive) for comparison since DB stores local time
    yesterday_start = (now - timedelta(days=1)).replace(hour=0,
                                                        minute=0, second=0, microsecond=0)
    yesterday_end = now.replace(hour=0, minute=0, second=0, microsecond=0)

    yesterday_date = (now - timedelta(days=1)).strftime("%d.%m.%Y")
    period_name = f"Вчера ({yesterday_date})"

    message = await build_stats_message(session, FAMILY_USER_ID, yesterday_start, yesterday_end, period_name)

    await callback.message.edit_text(
        message,
        reply_markup=get_stats_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "stats_week")
async def show_week_stats(callback: types.CallbackQuery, session: AsyncSession):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    # Use local time (naive) for comparison since DB stores local time
    week_start = (now - timedelta(days=7)).replace(hour=0,
                                                   minute=0, second=0, microsecond=0)

    message = await build_stats_message(session, FAMILY_USER_ID, week_start, now, "За неделю", detailed=False)

    await callback.message.edit_text(
        message,
        reply_markup=get_stats_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "stats_month")
async def show_month_stats(callback: types.CallbackQuery, session: AsyncSession):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    # Use local time (naive) for comparison since DB stores local time
    month_start = (now - timedelta(days=30)).replace(hour=0,
                                                     minute=0, second=0, microsecond=0)

    message = await build_stats_message(session, FAMILY_USER_ID, month_start, now, "За месяц", detailed=False)

    await callback.message.edit_text(
        message,
        reply_markup=get_stats_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "feeding_stats_today")
async def show_feeding_today(callback: types.CallbackQuery, session: AsyncSession):
    """Show today feeding stats only"""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    # Use local time (naive) for comparison since DB stores local time
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)

    date_str = now.strftime("%d.%m.%Y")

    # Debug logging
    import logging
    logging.info(f"=== FEEDING STATS TODAY ===")
    logging.info(f"Now: {now}")
    logging.info(f"Start date: {start_date}")
    logging.info(f"End date: {end_date}")

    # Get only feeding data
    feedings = await get_feedings(session, FAMILY_USER_ID, start_date, end_date)

    logging.info(f"Found {len(feedings)} feedings")
    for f in feedings:
        logging.info(
            f"  Feeding: started_at={f.started_at}, ended_at={f.ended_at}")

    feeding_count = len([f for f in feedings if f.ended_at is not None])

    message = f"🍼 <b>Кормления - Сегодня ({date_str})</b>\n\n"

    if feeding_count > 0:
        message += f"• Количество: {feeding_count}\n"
        message += "• Периоды кормлений:\n"
        for i, feeding in enumerate([f for f in feedings if f.ended_at], 1):
            start = format_time(feeding.started_at)
            end = format_time(feeding.ended_at)
            duration = format_duration(
                (feeding.ended_at - feeding.started_at).total_seconds())
            message += f"  {i}. {start} - {end} ({duration})\n"
    else:
        message += "• Еще нет записей\n"

    await callback.message.edit_text(
        message,
        reply_markup=get_feeding_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "sleep_stats_today")
async def show_sleep_today(callback: types.CallbackQuery, session: AsyncSession):
    """Show today sleep stats only"""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    # Use local time (naive) for comparison since DB stores local time
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)

    date_str = now.strftime("%d.%m.%Y")

    # Get only sleep data
    sessions = await get_sleep_sessions(session, FAMILY_USER_ID, start_date, end_date)
    completed_sessions = [s for s in sessions if s.ended_at is not None]
    total_sleep_seconds = sum(
        (s.ended_at - s.started_at).total_seconds()
        for s in completed_sessions
    )

    message = f"😴 <b>Сон - Сегодня ({date_str})</b>\n\n"

    if completed_sessions:
        message += f"• Периодов: {len(completed_sessions)}\n"
        message += f"• Общее время: {format_duration(total_sleep_seconds)}\n"
        message += "• Периоды сна:\n"
        for i, sess in enumerate(completed_sessions, 1):
            start = format_time(sess.started_at)
            end = format_time(sess.ended_at)
            duration = format_duration(
                (sess.ended_at - sess.started_at).total_seconds())
            message += f"  {i}. {start} - {end} ({duration})\n"
    else:
        message += "• Еще нет записей\n"

    await callback.message.edit_text(
        message,
        reply_markup=get_sleep_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "diaper_stats_today")
async def show_diaper_today(callback: types.CallbackQuery, session: AsyncSession):
    """Show today diaper stats only"""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    # Use local time (naive) for comparison since DB stores local time
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)

    date_str = now.strftime("%d.%m.%Y")

    # Get only diaper data
    diapers = await get_diapers(session, FAMILY_USER_ID, start_date, end_date)
    wet_count = sum(1 for d in diapers if d.diaper_type in ["wet", "both"])
    dirty_count = sum(1 for d in diapers if d.diaper_type in ["dirty", "both"])

    # Debug: check what diaper types we have
    import logging
    types_list = [d.diaper_type for d in diapers]
    logging.info(f"Diaper types today: {types_list}")
    logging.info(
        f"Total: {len(diapers)}, Wet: {wet_count}, Dirty: {dirty_count}")

    message = f"🧷 <b>Подгузники - Сегодня ({date_str})</b>\n\n"

    if diapers:
        message += f"• Мокрые: {wet_count}\n"
        message += f"• Грязные: {dirty_count}\n"
        message += f"• Всего: {len(diapers)}\n"
    else:
        message += "• Еще нет записей\n"

    await callback.message.edit_text(
        message,
        reply_markup=get_diaper_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "weight_chart")
async def show_weight_chart(callback: types.CallbackQuery, session: AsyncSession):
    """Show weight change chart over time"""
    # Get all weights to check if we have enough data
    all_weights = await get_weights(session, FAMILY_USER_ID, limit=1000)

    if not all_weights or len(all_weights) < 2:
        await callback.answer("❌ Нужно минимум 2 записи веса для построения графика", show_alert=True)
        return

    chart_file = await create_weight_chart(session, FAMILY_USER_ID)

    if not chart_file:
        await callback.answer("❌ Ошибка при создании графика", show_alert=True)
        return

    # Build caption
    first_weight = all_weights[-1]  # Oldest
    last_weight = all_weights[0]    # Newest
    diff = last_weight.weight_g - first_weight.weight_g

    caption = f"📊 <b>График изменения веса</b>\n\n"
    caption += f"📈 <b>Всего записей:</b> {len(all_weights)}\n"
    caption += f"📅 <b>Первая запись:</b> {format_datetime(first_weight.created_at)}\n"
    caption += f"📅 <b>Последняя запись:</b> {format_datetime(last_weight.created_at)}\n\n"
    caption += f"⚖️ <b>Изменение:</b> "

    if diff > 0:
        caption += f"+{diff:.0f} г (набор веса)"
    elif diff < 0:
        caption += f"{diff:.0f} г (потеря веса)"
    else:
        caption += "без изменений"

    await callback.message.answer_photo(
        photo=chart_file,
        caption=caption,
        parse_mode="HTML",
        reply_markup=get_stats_menu()
    )

    await callback.answer()
