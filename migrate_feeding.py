"""
Migration script to update Feeding table structure
Changes: created_at -> started_at, added ended_at column
"""
import asyncio
import sqlite3
from app.config import DATABASE_URL


async def migrate_feeding_table():
    """Migrate feeding table from old structure to new structure"""
    # Extract database path from DATABASE_URL
    db_path = DATABASE_URL.split("sqlite+aiosqlite:///")[-1]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if migration is needed
        cursor.execute("PRAGMA table_info(feedings)")
        columns = [row[1] for row in cursor.fetchall()]

        if "started_at" in columns and "ended_at" in columns:
            print("✓ Migration already completed")
            return

        if "created_at" not in columns:
            print("✓ Table already has correct structure")
            return

        print("Starting migration...")

        # Rename old table
        cursor.execute("ALTER TABLE feedings RENAME TO feedings_old")

        # Create new table with correct structure
        cursor.execute("""
            CREATE TABLE feedings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                started_at DATETIME NOT NULL,
                ended_at DATETIME
            )
        """)

        # Copy data from old table, using created_at as started_at
        cursor.execute("""
            INSERT INTO feedings (id, user_id, started_at, ended_at)
            SELECT id, user_id, created_at, created_at as ended_at
            FROM feedings_old
        """)

        # Drop old table
        cursor.execute("DROP TABLE feedings_old")

        conn.commit()
        print("✓ Migration completed successfully!")
        print("  - Renamed created_at to started_at")
        print("  - Added ended_at column")
        print("  - Set ended_at = started_at for existing records")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate_feeding_table())
