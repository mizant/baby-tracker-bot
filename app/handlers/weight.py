from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.keyboards import get_main_menu, get_cancel_keyboard
from app.models import Weight, Event
from app.services.stats import get_weights, get_last_weight
from app.services.formatters import format_time, format_datetime
from app.config import FAMILY_USER_ID

router = Router()


class WeightState(StatesGroup):
    waiting_for_weight = State()


@router.callback_query(F.data == "weight")
async def request_weight(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    # Get last weight info
    last_weight = await get_last_weight(session, FAMILY_USER_ID)
    last_info = ""

    if last_weight:
        last_info = f"\n\n📋 Последний вес: {last_weight.weight_g:.0f} г ({format_datetime(last_weight.created_at)})"
    else:
        last_info = "\n\n📋 Еще нет записей о весе"

    await state.set_state(WeightState.waiting_for_weight)
    await callback.message.edit_text(
        f"⚖️ Введите вес ребенка в граммах (например: 3250):{last_info}",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(WeightState.waiting_for_weight, F.text.regexp(r"^\d+$"))
async def process_weight(message: types.Message, session: AsyncSession, state: FSMContext):
    weight_g = float(message.text)

    # Get previous weight
    previous_weights = await get_weights(session, FAMILY_USER_ID, limit=2)
    previous_weight = previous_weights[1] if len(
        previous_weights) > 1 else None

    # Save new weight
    weight = Weight(
        user_id=FAMILY_USER_ID,
        weight_g=weight_g,
        created_at=datetime.utcnow()
    )
    session.add(weight)
    await session.flush()

    event = Event(
        user_id=FAMILY_USER_ID,
        event_type="weight",
        record_id=weight.id,
        created_at=datetime.utcnow()
    )
    session.add(event)
    await session.commit()

    # Calculate difference
    diff_text = ""
    if previous_weight:
        diff = weight_g - previous_weight.weight_g
        if diff > 0:
            diff_text = f"\n📈 Изменение: +{diff:.0f} г"
        elif diff < 0:
            diff_text = f"\n📉 Изменение: {diff:.0f} г"
        else:
            diff_text = f"\n➡️ Без изменений"

    await state.clear()

    await message.answer(
        f"✅ Вес записан: {weight_g:.0f} г в {format_time(weight.created_at)}\n"
        f"📊 Текущий вес: {weight_g:.0f} г{diff_text}\n\n"
        f"Выберите действие:",
        reply_markup=get_main_menu()
    )
