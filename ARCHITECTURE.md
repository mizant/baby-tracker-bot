# Baby Tracker Bot - Архитектура проекта

## Обзор

Telegram-бот для отслеживания режима новорожденного ребенка, построенный на aiogram 3 с асинхронной архитектурой.

## Технологический стек

- **Python 3.12** - основной язык
- **aiogram 3** - асинхронная библиотека для Telegram Bot API
- **SQLAlchemy 2.0** - ORM для работы с БД
- **SQLite (aiosqlite)** - асинхронная база данных
- **pytz** - работа с часовыми поясами
- **python-dotenv** - загрузка переменных окружения

## Структура проекта

```
baby-tracker-bot/
├── app/
│   ├── __init__.py
│   ├── main.py              # Точка входа, инициализация бота
│   ├── config.py            # Конфигурация (загрузка из .env)
│   ├── db.py                # Подключение к БД, сессии
│   ├── models.py            # SQLAlchemy модели (5 таблиц)
│   ├── keyboards.py         # Inline-клавиатуры
│   ├── handlers/            # Обработчики сообщений
│   │   ├── __init__.py
│   │   ├── start.py         # /start, back_to_menu, cancel
│   │   ├── feeding.py       # Кормление (FSM для ручного ввода)
│   │   ├── sleep.py         # Сон (начало/конец сессии)
│   │   ├── diaper.py        # Подгузники (3 типа)
│   │   ├── weight.py        # Вес (FSM для ввода)
│   │   ├── stats.py         # Статистика за день
│   │   └── undo.py          # Отмена последней записи
│   └── services/            # Бизнес-логика
│       ├── __init__.py
│       ├── stats.py         # Запросы к БД для статистики
│       └── formatters.py    # Форматирование времени/длительности
├── requirements.txt         # Python зависимости
├── .env                     # Переменные окружения (не в git)
├── .env.example             # Пример .env
├── .gitignore
├── README.md               # Основная документация
├── QUICKSTART.md           # Быстрый старт
└── start.bat               # Скрипт запуска (Windows)
```

## База данных

### Таблицы

#### 1. feedings (Кормления)

```sql
- id: Integer (PK)
- user_id: Integer
- volume_ml: Integer (объем в мл)
- created_at: DateTime (UTC)
```

#### 2. sleep_sessions (Сессии сна)

```sql
- id: Integer (PK)
- user_id: Integer
- started_at: DateTime (UTC, NOT NULL)
- ended_at: DateTime (UTC, nullable)
```

#### 3. diapers (Подгузники)

```sql
- id: Integer (PK)
- user_id: Integer
- diaper_type: String (wet/dirty/both)
- created_at: DateTime (UTC)
```

#### 4. weights (Вес)

```sql
- id: Integer (PK)
- user_id: Integer
- weight_g: Float (вес в граммах)
- created_at: DateTime (UTC)
```

#### 5. events (События для undo)

```sql
- id: Integer (PK)
- user_id: Integer
- event_type: String (feeding/sleep/diaper/weight)
- record_id: Integer (ID записи в соответствующей таблице)
- created_at: DateTime (UTC)
```

### Схема связей

```
User (Telegram)
  ├── feedings (1:N)
  ├── sleep_sessions (1:N)
  ├── diapers (1:N)
  ├── weights (1:N)
  └── events (1:N)
```

## Архитектура обработки запросов

```
Telegram API
    ↓
aiogram Dispatcher
    ↓
Middleware (DB Session)
    ↓
Handler (routing by callback_data)
    ↓
Service Layer (business logic)
    ↓
Database (via SQLAlchemy)
    ↓
Response (edited message)
```

## Поток данных

### Кормление (пример)

```
1. User нажимает "🍼 Кормление" → callback: "feeding"
2. Bot показывает меню кормления
3. User выбирает "50 мл" → callback: "feed_50"
4. Handler создает:
   - Feeding record (user_id, volume_ml, created_at)
   - Event record (user_id, event_type="feeding", record_id)
5. Bot считает статистику за сегодня
6. Bot показывает подтверждение + статистика
```

### Сон с активной сессией

```
1. User нажимает "😴 Сон" → callback: "sleep"
2. Bot показывает меню сна
3. User нажимает "Ребенок уснул" → callback: "sleep_started"
4. Bot проверяет, нет ли активной сессии
5. Если нет → создает SleepSession (started_at, ended_at=NULL)
6. Позже: User нажимает "Ребенок проснулся" → callback: "sleep_ended"
7. Bot находит активную сессию, ставит ended_at=now
8. Bot считает длительность и показывает результат
```

### Отмена записи

```
1. User нажимает "↩️ Отменить" → callback: "undo"
2. Handler ищет последний Event пользователя
3. Проверяет, что запись < 24 часов
4. Удаляет соответствующую запись (feeding/sleep/diaper/weight)
5. Удаляет Event
6. Показывает, что именно удалено
```

## FSM (Finite State Machine)

Используется для обработки ручного ввода:

### feeding.FeedingState

- `waiting_for_manual` - ожидание ввода объема в мл

### weight.WeightState

- `waiting_for_weight` - ожидание ввода веса в граммах

Состояния очищаются при:

- Успешном сохранении
- Нажатии "❌ Отмена"
- Нажатии "↩️ Назад"

## Часовые пояса

- **Хранение:** Все времена в UTC (datetime.utcnow())
- **Отображение:** Конвертация в TIMEZONE из .env
- **Форматирование:** services/formatters.py

## Безопасность

### Whitelist пользователей

- Проверка в /start: `message.from_user.id in ADMIN_IDS`
- Если не в списке → отказ в доступе
- Все обработчики работают только с разрешенными пользователями

### Ограничения

- Undo только за последние 24 часа
- Только один активный сон сессия на пользователя
- Валидация ввода через regex

## Middleware

### Session Middleware

```python
# Автоматически injects async DB session в каждый handler
async def session_middleware(handler, event, data):
    async for session in get_session():
        data["session"] = session
        return await handler(event, data)
```

## Обработка ошибок

- Try/except в main.py при polling
- Валидация ввода (regex для чисел)
- Проверка на None при поиске записей
- Проверка активной сессии сна
- Сообщения об ошибках пользователю

## Ключевые особенности

### 1. Модульность

Каждый функционал в отдельном файле handlers/

### 2. Async-first

Все операции асинхронные (aiogram 3 + aiosqlite)

### 3. Быстрый UI

- Inline-кнопки вместо текстовых команд
- Минимум ручного ввода
- Быстрые callback handlers

### 4. Event-driven architecture

Таблица events позволяет отслеживать все изменения для undo

### 5. Single-responsibility

- handlers/ - обработка сообщений
- services/ - бизнес-логика
- models/ - данные

## Расширение

Для добавления нового функционала:

1. Создать модель в models.py
2. Создать handler в handlers/
3. (Опционально) Создать FSM states
4. Добавить клавиатуру в keyboards.py
5. Зарегистрировать router в main.py
6. Добавить сервисные функции в services/

## Производительность

- Async I/O для всех операций с БД
- Один запрос на обновление сообщения
- Кэширование статистики в пределах handler
- Минимум запросов при отображении stats

## Деплой

### Requirements

- Python 3.12+
- Зависимости: pip install -r requirements.txt

### Запуск

```bash
python -m app.main
```

### Persistence

- SQLite хранится в файле baby_tracker.db
- FSM storage: MemoryStorage (в памяти)
- При перезапуске FSM сбрасывается, DB сохраняется

## Мониторинг

Логи в stdout:

- INFO: старт бота, инициализация БД
- ERROR: критические ошибки
- Формат: %(asctime)s - %(name)s - %(levelname)s - %(message)s

## Тестирование

Ручное тестирование:

1. /start - проверка whitelist
2. Все кнопки меню
3. FSM states (ручной ввод)
4. Undo функционал
5. 24-hour ограничение
6. Активная сессия сна
7. Статистика за день

## Будущие улучшения

- [ ] Экспорт данных (CSV/Excel)
- [ ] Графики (matplotlib)
- [ ] Мульти-детность
- [ ] Уведомления (напоминания)
- [ ] Веб-интерфейс
- [ ] PostgreSQL поддержка
- [ ] Юнит-тесты
- [ ] Docker контейнеризация
