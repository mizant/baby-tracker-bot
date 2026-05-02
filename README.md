# Baby Tracker Bot 🍼

Telegram-бот для семейного трекинга режима новорожденного ребенка.

## Возможности

- ✅ Учет кормлений (объем мл)
- ✅ Отслеживание сна (длительность)
- ✅ Учет подгузников
- ✅ Запись веса
- ✅ Статистика за день
- ✅ Отмена последней записи

## Установка

1. **Создайте виртуальное окружение:**

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# или
source venv/bin/activate  # Linux/Mac
```

2. **Установите зависимости:**

```bash
pip install -r requirements.txt
```

3. **Настройте .env файл:**

```bash
cp .env.example .env
```

Откройте `.env` и укажите:

- `BOT_TOKEN` — токен от @BotFather
- `ADMIN_IDS` — ваши Telegram ID через запятую
- `TIMEZONE` — ваш часовой пояс (по умолчанию Europe/Warsaw)

4. **Получите Telegram Bot токен:**

   - Откройте @BotFather в Telegram
   - Отправьте `/newbot`
   - Следуйте инструкциям
   - Скопируйте токен в `.env`

5. **Узнайте свой Telegram ID:**
   - Отправьте сообщение @userinfobot
   - Скопируйте ваш ID в `ADMIN_IDS`

## Запуск

```bash
python -m app.main
```

## Команды бота

- `/start` — Главное меню
- 🍼 Кормление — записать объем молока
- 😴 Сон — зафиксировать сон
- 🧷 Подгузник — записать тип подгузника
- ⚖️ Вес — записать вес ребенка
- 📊 Сегодня — статистика за день
- ↩️ Отменить последнее — удалить последнюю запись

## Структура проекта

```
baby-tracker-bot/
├── app/
│   ├── __init__.py
│   ├── main.py              # Точка входа
│   ├── config.py            # Настройки
│   ├── db.py                # Подключение к БД
│   ├── models.py            # SQLAlchemy модели
│   ├── keyboards.py         # Inline-кнопки
│   ├── handlers/
│   │   ├── start.py         # /start команда
│   │   ├── feeding.py       # Кормление
│   │   ├── sleep.py         # Сон
│   │   ├── diaper.py        # Подгузники
│   │   ├── weight.py        # Вес
│   │   ├── stats.py         # Статистика
│   │   └── undo.py          # Отмена
│   └── services/
│       ├── stats.py         # Логика статистики
│       └── formatters.py    # Форматирование данных
├── requirements.txt
├── .env.example
├── .env
└── README.md
```

## Технологии

- Python 3.12
- aiogram 3 (async Telegram Bot API)
- SQLAlchemy (async)
- SQLite
- python-dotenv

## Важно

- Бот только фиксирует данные и показывает статистику
- Все времена хранятся в UTC
- Пользователю показывается время в вашем часовом поясе
