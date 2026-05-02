from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🍼 Кормление", callback_data="feeding"),
            InlineKeyboardButton(text="😴 Сон", callback_data="sleep")
        ],
        [
            InlineKeyboardButton(text="🧷 Подгузник", callback_data="diaper"),
            InlineKeyboardButton(text="⚖️ Вес", callback_data="weight")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="↩️ Отменить", callback_data="undo")
        ]
    ])
    return keyboard


def get_feeding_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🕐 Кормление сейчас",
                                 callback_data="feed_now")
        ],
        [
            InlineKeyboardButton(text="✏️ Ввести другое время",
                                 callback_data="feed_manual_time")
        ],
        [
            InlineKeyboardButton(text="🗑️ Удалить последнее",
                                 callback_data="feed_delete_last")
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_menu")
        ]
    ])
    return keyboard


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        ]
    ])
    return keyboard


def get_sleep_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="😴 Ребенок уснул",
                                 callback_data="sleep_started")
        ],
        [
            InlineKeyboardButton(text="☀️ Ребенок проснулся",
                                 callback_data="sleep_ended")
        ],
        [
            InlineKeyboardButton(text="✏️ Ввести начало и конец сна",
                                 callback_data="sleep_manual")
        ],
        [
            InlineKeyboardButton(text="🗑️ Удалить последний",
                                 callback_data="sleep_delete_last")
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_menu")
        ]
    ])
    return keyboard


def get_diaper_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💧 Мокрый", callback_data="diaper_wet"),
            InlineKeyboardButton(
                text="💩 Грязный", callback_data="diaper_dirty")
        ],
        [
            InlineKeyboardButton(text="💧💩 Мокрый + грязный",
                                 callback_data="diaper_both")
        ],
        [
            InlineKeyboardButton(text="🗑️ Удалить последний",
                                 callback_data="diaper_delete_last")
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_menu")
        ]
    ])
    return keyboard


def get_stats_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Сегодня", callback_data="stats_today")
        ],
        [
            InlineKeyboardButton(
                text="📅 Вчера", callback_data="stats_yesterday")
        ],
        [
            InlineKeyboardButton(text="📆 За неделю",
                                 callback_data="stats_week")
        ],
        [
            InlineKeyboardButton(text="🗓️ За месяц",
                                 callback_data="stats_month")
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_menu")
        ]
    ])
    return keyboard
