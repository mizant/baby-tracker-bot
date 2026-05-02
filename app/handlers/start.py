from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from app.config import ADMIN_IDS
from app.keyboards import get_main_menu

router = Router()


@router.message(CommandStart())
async def command_start(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Доступ закрыт. Вы не авторизованы для использования этого бота.")
        return

    await message.answer(
        "👋 Привет! Я бот для трекинга режима новорожденного.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu()
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👋 Выберите действие:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Ввод отменен.",
        reply_markup=get_main_menu()
    )
    await callback.answer()
