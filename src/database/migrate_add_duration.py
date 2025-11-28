"""Database migration: Add duration_seconds column to jobs table.

This migration adds the duration_seconds column to track processing time for each job.

Run this script once to migrate existing databases:
    python src/database/migrate_add_duration.py

For new installations, this migration is not needed (schema includes the column).
"""

import sqlite3
import sys
from pathlib import Path

# Configure stdout for UTF-8 on Windows (prevents Unicode encoding errors)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def migrate_database(db_path: Path | str = Path("data/app.db")) -> bool:
    """Add duration_seconds column to jobs table if it doesn't exist.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if migration was successful or already applied, False otherwise
    """
    db_path = Path(db_path) if isinstance(db_path, str) else db_path

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("No migration needed (database will be created with correct schema)")
        return True

    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'duration_seconds' in columns:
            print("✓ Migration already applied: duration_seconds column exists")
            conn.close()
            return True

        # Add the column
        print("Adding duration_seconds column to jobs table...")
        cursor.execute("""
            ALTER TABLE jobs
            ADD COLUMN duration_seconds REAL DEFAULT 0.0
        """)
        conn.commit()

        # Verify the column was added
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'duration_seconds' in columns:
            print("✓ Migration successful: duration_seconds column added")
            conn.close()
            return True
        else:
            print("✗ Migration failed: Column not added")
            conn.close()
            return False

    except sqlite3.Error as e:
        print(f"✗ Migration failed with error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during migration: {e}")
        return False


if __name__ == "__main__":
    # Allow custom database path as command-line argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else Path("data/app.db")

    print("=" * 60)
    print("Database Migration: Add duration_seconds column")
    print("=" * 60)
    print(f"Database: {db_path}")
    print()

    success = migrate_database(db_path)

    print()
    print("=" * 60)
    if success:
        print("Migration completed successfully")
    else:
        print("Migration failed - please check errors above")
        sys.exit(1)
