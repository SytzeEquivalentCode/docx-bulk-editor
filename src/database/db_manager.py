"""Database management with thread-safe SQLite operations and UTF-8 support."""

import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Optional


class DatabaseManager:
    """Thread-safe SQLite database manager for application data.

    Manages all database operations including job tracking, results storage,
    settings management, backup registry, and audit logging.

    Features:
    - Thread-safe connection management with check_same_thread=False
    - Automatic schema creation and migration
    - Foreign key constraint enforcement
    - UTF-8 encoding support
    - Row factory for dict-like access
    """

    def __init__(self, db_path: Path | str = Path("data/app.db")):
        """Initialize DatabaseManager.

        Args:
            db_path: Path to SQLite database file (default: data/app.db)
                    Use ":memory:" for in-memory database (testing)
        """
        # Handle special case for in-memory database
        if db_path == ":memory:":
            self.db_path = ":memory:"
            self._is_memory = True
            # Create persistent connection for in-memory database
            # (each new connection creates a separate database)
            self._persistent_conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._persistent_conn.execute("PRAGMA foreign_keys = ON")
            self._persistent_conn.row_factory = sqlite3.Row
        else:
            # Convert to Path if string
            self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
            self._is_memory = False
            self._persistent_conn = None

            # Create data directory if it doesn't exist (only for file-based DB)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_database()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get thread-safe database connection with context manager.

        Yields:
            SQLite connection with Row factory for dict-like access

        Examples:
            >>> db = DatabaseManager()
            >>> with db.get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT * FROM jobs")
            ...     rows = cursor.fetchall()
        """
        # For in-memory databases, use persistent connection
        if self._is_memory:
            try:
                if self._persistent_conn is None:
                    raise RuntimeError("Database connection has been closed")
                yield self._persistent_conn
                self._persistent_conn.commit()
            except Exception:
                if self._persistent_conn is not None:
                    self._persistent_conn.rollback()
                raise
        else:
            # For file-based databases, create new connection each time
            # Thread-safe connection (allows use from multiple threads)
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0  # 30 second timeout for locked database
            )

            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")

            # Use Row factory for dict-like access to rows
            conn.row_factory = sqlite3.Row

            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_database(self) -> None:
        """Initialize database schema with all tables and indexes.

        Creates:
        - jobs: Job tracking with status and configuration
        - job_results: Per-file results for each job
        - settings: Key-value store for user preferences
        - backups: Backup file registry
        - audit_log: Event tracking for compliance
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Jobs table: Track processing jobs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    operation TEXT NOT NULL,
                    config TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    total_files INTEGER DEFAULT 0,
                    processed_files INTEGER DEFAULT 0,
                    successful_files INTEGER DEFAULT 0,
                    failed_files INTEGER DEFAULT 0,
                    total_changes INTEGER DEFAULT 0,
                    error_message TEXT
                )
            """)

            # Job results table: Per-file results for each job
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_results (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    changes_made INTEGER DEFAULT 0,
                    error_message TEXT,
                    processing_time_seconds REAL DEFAULT 0.0,
                    backup_path TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            """)

            # Settings table: Key-value store for user preferences
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Backups table: Backup file registry
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    original_path TEXT NOT NULL,
                    backup_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    size_bytes INTEGER DEFAULT 0,
                    restored BOOLEAN DEFAULT 0,
                    restored_at TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL
                )
            """)

            # Audit log table: Event tracking for compliance
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    user TEXT,
                    details TEXT,
                    ip_address TEXT
                )
            """)

            # Create indexes for performance optimization

            # Jobs indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_created_at
                ON jobs(created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_operation
                ON jobs(operation)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status
                ON jobs(status)
            """)

            # Job results indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_results_job_id
                ON job_results(job_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_results_status
                ON job_results(status)
            """)

            # Backups indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_backups_created_at
                ON backups(created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_backups_original_path
                ON backups(original_path)
            """)

            # Audit log indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp
                ON audit_log(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_log_event_type
                ON audit_log(event_type)
            """)

            conn.commit()

    @staticmethod
    def generate_id() -> str:
        """Generate unique ID for database records.

        Returns:
            UUID4 string without hyphens

        Examples:
            >>> id1 = DatabaseManager.generate_id()
            >>> id2 = DatabaseManager.generate_id()
            >>> assert id1 != id2
            >>> assert len(id1) == 32  # UUID without hyphens
        """
        return uuid.uuid4().hex

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get setting value from database.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Set setting value in database.

        Args:
            key: Setting key
            value: Setting value
        """
        from datetime import datetime

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            """, (key, value, datetime.now().isoformat()))

    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as dictionary.

        Returns:
            Dictionary of all settings (key: value)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    def close(self):
        """Close database connection.

        For in-memory databases, closes the persistent connection.
        For file-based databases, no action needed (connections are
        managed by context managers).
        """
        if self._is_memory and self._persistent_conn:
            self._persistent_conn.close()
            self._persistent_conn = None
