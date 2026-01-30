"""Unit tests for DatabaseManager with complete schema validation."""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

import pytest

from src.database.db_manager import DatabaseManager


class TestDatabaseInitialization:
    """Test suite for database initialization and schema creation."""

    def test_database_initialization(self, tmp_path):
        """Test all 5 tables are created during initialization."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        # Verify database file created
        assert db_path.exists()

        # Verify all 5 tables exist
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row["name"] for row in cursor.fetchall()]

        expected_tables = ["audit_log", "backups", "job_results", "jobs", "settings"]
        assert tables == expected_tables

    def test_data_directory_auto_created(self, tmp_path):
        """Test data/ directory is automatically created."""
        db_path = tmp_path / "nested" / "data" / "test.db"

        # Directory should not exist initially
        assert not db_path.parent.exists()

        # Creating DatabaseManager should create directory
        db = DatabaseManager(db_path)

        # Verify directory created
        assert db_path.parent.exists()
        assert db_path.exists()

    def test_schema_validation_jobs_table(self, tmp_path):
        """Test jobs table has correct columns."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(jobs)")
            columns = {row["name"]: row["type"] for row in cursor.fetchall()}

        expected_columns = {
            "id": "TEXT",
            "created_at": "TEXT",
            "started_at": "TEXT",
            "completed_at": "TEXT",
            "operation": "TEXT",
            "config": "TEXT",
            "status": "TEXT",
            "total_files": "INTEGER",
            "processed_files": "INTEGER",
            "successful_files": "INTEGER",
            "failed_files": "INTEGER",
            "total_changes": "INTEGER",
            "duration_seconds": "REAL",
            "error_message": "TEXT"
        }

        assert columns == expected_columns

    def test_schema_validation_job_results_table(self, tmp_path):
        """Test job_results table has correct columns."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(job_results)")
            columns = {row["name"]: row["type"] for row in cursor.fetchall()}

        expected_columns = {
            "id": "TEXT",
            "job_id": "TEXT",
            "file_path": "TEXT",
            "status": "TEXT",
            "changes_made": "INTEGER",
            "error_message": "TEXT",
            "processing_time_seconds": "REAL",
            "backup_path": "TEXT",
            "created_at": "TEXT"
        }

        assert columns == expected_columns

    def test_schema_validation_settings_table(self, tmp_path):
        """Test settings table has correct columns."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(settings)")
            columns = {row["name"]: row["type"] for row in cursor.fetchall()}

        expected_columns = {
            "key": "TEXT",
            "value": "TEXT",
            "updated_at": "TEXT"
        }

        assert columns == expected_columns

    def test_schema_validation_backups_table(self, tmp_path):
        """Test backups table has correct columns."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(backups)")
            columns = {row["name"]: row["type"] for row in cursor.fetchall()}

        expected_columns = {
            "id": "TEXT",
            "job_id": "TEXT",
            "original_path": "TEXT",
            "backup_path": "TEXT",
            "created_at": "TEXT",
            "size_bytes": "INTEGER",
            "restored": "BOOLEAN",
            "restored_at": "TEXT"
        }

        assert columns == expected_columns

    def test_schema_validation_audit_log_table(self, tmp_path):
        """Test audit_log table has correct columns."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(audit_log)")
            columns = {row["name"]: row["type"] for row in cursor.fetchall()}

        expected_columns = {
            "id": "TEXT",
            "timestamp": "TEXT",
            "event_type": "TEXT",
            "user": "TEXT",
            "details": "TEXT",
            "ip_address": "TEXT"
        }

        assert columns == expected_columns


class TestDatabaseIndexes:
    """Test suite for database indexes."""

    def test_indexes_created(self, tmp_path):
        """Test all 8 indexes are created."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Get all indexes (excluding auto-created primary key indexes)
            cursor.execute("""
                SELECT name, tbl_name FROM sqlite_master
                WHERE type='index' AND name LIKE 'idx_%'
                ORDER BY name
            """)
            indexes = [(row["name"], row["tbl_name"]) for row in cursor.fetchall()]

        expected_indexes = [
            ("idx_audit_log_event_type", "audit_log"),
            ("idx_audit_log_timestamp", "audit_log"),
            ("idx_backups_created_at", "backups"),
            ("idx_backups_original_path", "backups"),
            ("idx_job_results_job_id", "job_results"),
            ("idx_job_results_status", "job_results"),
            ("idx_jobs_created_at", "jobs"),
            ("idx_jobs_operation", "jobs"),
            ("idx_jobs_status", "jobs")
        ]

        assert indexes == expected_indexes

    def test_jobs_indexes_exist(self, tmp_path):
        """Test jobs table has all required indexes."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA index_list(jobs)")
            index_names = [row["name"] for row in cursor.fetchall()]

        assert "idx_jobs_created_at" in index_names
        assert "idx_jobs_operation" in index_names
        assert "idx_jobs_status" in index_names


class TestForeignKeys:
    """Test suite for foreign key constraints."""

    def test_foreign_key_cascade_delete(self, tmp_path):
        """Test job_results CASCADE delete when parent job is deleted."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Create a job
            job_id = db.generate_id()
            cursor.execute("""
                INSERT INTO jobs (id, created_at, operation, config, status)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, datetime.now().isoformat(), "test", "{}", "pending"))

            # Create job results
            result_id = db.generate_id()
            cursor.execute("""
                INSERT INTO job_results (id, job_id, file_path, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (result_id, job_id, "test.docx", "success", datetime.now().isoformat()))

            # Verify result exists
            cursor.execute("SELECT COUNT(*) as count FROM job_results WHERE job_id = ?", (job_id,))
            assert cursor.fetchone()["count"] == 1

            # Delete job (should cascade to job_results)
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()

            # Verify result was deleted (CASCADE)
            cursor.execute("SELECT COUNT(*) as count FROM job_results WHERE job_id = ?", (job_id,))
            assert cursor.fetchone()["count"] == 0

    def test_foreign_key_set_null(self, tmp_path):
        """Test backups SET NULL when parent job is deleted."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Create a job
            job_id = db.generate_id()
            cursor.execute("""
                INSERT INTO jobs (id, created_at, operation, config, status)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, datetime.now().isoformat(), "test", "{}", "pending"))

            # Create backup with job_id
            backup_id = db.generate_id()
            cursor.execute("""
                INSERT INTO backups (id, job_id, original_path, backup_path, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (backup_id, job_id, "original.docx", "backup.docx", datetime.now().isoformat()))

            # Delete job (should set backup.job_id to NULL)
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()

            # Verify backup still exists but job_id is NULL
            cursor.execute("SELECT job_id FROM backups WHERE id = ?", (backup_id,))
            row = cursor.fetchone()
            assert row is not None
            assert row["job_id"] is None


class TestConnectionManager:
    """Test suite for connection management."""

    def test_connection_context_manager(self, tmp_path):
        """Test connection context manager commits and closes properly."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        # Insert data using context manager
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, ("test_key", "test_value", datetime.now().isoformat()))

        # Verify data was committed
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", ("test_key",))
            row = cursor.fetchone()
            assert row["value"] == "test_value"

    def test_connection_rollback_on_error(self, tmp_path):
        """Test connection rolls back on exception."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        # Try to insert invalid data
        with pytest.raises(sqlite3.IntegrityError):
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Insert valid data
                cursor.execute("""
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, ("key1", "value1", datetime.now().isoformat()))

                # Try to insert duplicate key (should fail and rollback)
                cursor.execute("""
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, ("key1", "value2", datetime.now().isoformat()))

        # Verify no data was committed
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM settings")
            assert cursor.fetchone()["count"] == 0

    def test_row_factory_dict_access(self, tmp_path):
        """Test Row factory provides dict-like access."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, ("test", "value", datetime.now().isoformat()))

            cursor.execute("SELECT * FROM settings WHERE key = ?", ("test",))
            row = cursor.fetchone()

            # Test dict-like access
            assert row["key"] == "test"
            assert row["value"] == "value"

            # Test keys() method
            assert "key" in row.keys()
            assert "value" in row.keys()


class TestIDGeneration:
    """Test suite for ID generation."""

    def test_generate_id_uniqueness(self):
        """Test generate_id creates unique IDs."""
        ids = set()
        for _ in range(1000):
            new_id = DatabaseManager.generate_id()
            assert new_id not in ids
            ids.add(new_id)

    def test_generate_id_format(self):
        """Test generate_id returns UUID4 hex string."""
        generated_id = DatabaseManager.generate_id()

        # Should be 32 characters (UUID without hyphens)
        assert len(generated_id) == 32

        # Should be valid hex
        assert all(c in "0123456789abcdef" for c in generated_id)


class TestThreadSafety:
    """Test suite for thread safety."""

    def test_concurrent_connections(self, tmp_path):
        """Test multiple threads can use database concurrently."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        errors = []

        def writer_thread(thread_id: int):
            """Write data from a thread."""
            try:
                for i in range(10):
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO settings (key, value, updated_at)
                            VALUES (?, ?, ?)
                        """, (f"thread{thread_id}_key{i}", f"value{i}", datetime.now().isoformat()))
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=writer_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0

        # Verify all data was written
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM settings")
            assert cursor.fetchone()["count"] == 50  # 5 threads * 10 inserts


class TestSettingsMethods:
    """Test suite for settings helper methods."""

    def test_get_set_setting(self, tmp_path):
        """Test get_setting and set_setting methods."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        # Set a setting
        db.set_setting("test_key", "test_value")

        # Get the setting
        value = db.get_setting("test_key")
        assert value == "test_value"

    def test_get_setting_default(self, tmp_path):
        """Test get_setting returns default for non-existent key."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        value = db.get_setting("nonexistent", "default_value")
        assert value == "default_value"

    def test_set_setting_updates(self, tmp_path):
        """Test set_setting updates existing values."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        # Set initial value
        db.set_setting("key", "value1")
        assert db.get_setting("key") == "value1"

        # Update value
        db.set_setting("key", "value2")
        assert db.get_setting("key") == "value2"

    def test_get_all_settings(self, tmp_path):
        """Test get_all_settings returns all settings as dict."""
        db_path = tmp_path / "data" / "test.db"
        db = DatabaseManager(db_path)

        # Set multiple settings
        db.set_setting("key1", "value1")
        db.set_setting("key2", "value2")
        db.set_setting("key3", "value3")

        # Get all settings
        settings = db.get_all_settings()

        assert settings == {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }

    def test_memory_database_initialization(self):
        """Test DatabaseManager initialization with :memory: database path."""
        # This tests the special case handling for ":memory:" in __init__ (line 33)
        db = DatabaseManager(":memory:")

        # Verify in-memory database path is set correctly
        assert db.db_path == ":memory:"

        # Verify the database connection works
        with db.get_connection() as conn:
            # Should be able to execute SQL
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

        db.close()
