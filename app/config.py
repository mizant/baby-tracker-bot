from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./baby_tracker.db")
