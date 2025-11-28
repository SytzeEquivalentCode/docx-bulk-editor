"""Integration tests for core infrastructure components."""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path

import pytest

from src.core.config import ConfigManager
from src.core.logger import setup_logger
from src.database.db_manager import DatabaseManager


@pytest.fixture
def clean_environment(tmp_path):
    """Provide clean test environment with temporary directory."""
    return tmp_path


class TestCoreInfrastructureIntegration:
    """Integration tests for ConfigManager, Logger, and DatabaseManager."""

    def test_full_initialization(self, clean_environment):
        """Test complete initialization of all core components."""
        base_path = clean_environment / "app"

        # Initialize all components
        config_path = base_path / "config.json"
        log_dir = base_path / "logs"
        db_path = base_path / "data" / "app.db"

        config = ConfigManager(config_path)
        logger = setup_logger(log_dir=log_dir, config=config)
        db = DatabaseManager(db_path)

        # Verify all components initialized
        assert config_path.exists()
        assert log_dir.exists()
        assert db_path.exists()

        # Verify config has defaults
        assert config.get("version") == "1.0.0"
        assert config.get("logging.level") == "INFO"

        # Verify logger works
        logger.info("Test message")
        log_file = log_dir / "app.log"
        assert log_file.exists()

        # Verify database has tables
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='jobs'
            """)
            assert cursor.fetchone() is not None

    def test_config_logger_integration(self, clean_environment):
        """Test ConfigManager settings affect Logger behavior."""
        base_path = clean_environment / "app"

        # Create config with DEBUG level
        config_path = base_path / "config.json"
        config = ConfigManager(config_path)
        config.set("logging.level", "DEBUG")

        # Setup logger with config
        log_dir = base_path / "logs"
        logger = setup_logger(log_dir=log_dir, config=config)

        # Log DEBUG message
        logger.debug("Debug level message")

        # Verify DEBUG message in log file
        log_file = log_dir / "app.log"
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Debug level message" in content
            assert "DEBUG" in content

        # Change config to WARNING
        config.set("logging.level", "WARNING")

        # Setup new logger with updated config
        logger2 = setup_logger(name="test_warning", log_dir=log_dir, config=config)

        # Verify console handler has WARNING level
        for handler in logger2.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.handlers.RotatingFileHandler):
                assert handler.level == logging.WARNING

    def test_config_database_integration(self, clean_environment):
        """Test ConfigManager and DatabaseManager integration."""
        base_path = clean_environment / "app"

        # Create config
        config_path = base_path / "config.json"
        config = ConfigManager(config_path)

        # Set backup directory in config
        backup_dir = str(base_path / "backups")
        config.set("backup.directory", backup_dir)

        # Create database
        db_path = base_path / "data" / "app.db"
        db = DatabaseManager(db_path)

        # Store config value in database settings
        db.set_setting("backup_directory", backup_dir)

        # Verify both have same value
        assert config.get("backup.directory") == db.get_setting("backup_directory")

    def test_logger_database_integration(self, clean_environment):
        """Test Logger and DatabaseManager integration."""
        base_path = clean_environment / "app"

        # Setup logger
        log_dir = base_path / "logs"
        logger = setup_logger(log_dir=log_dir)

        # Setup database
        db_path = base_path / "data" / "app.db"
        db = DatabaseManager(db_path)

        # Log database operations
        logger.info("Creating job record")

        job_id = db.generate_id()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (id, created_at, operation, config, status)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, datetime.now().isoformat(), "test", "{}", "pending"))

        logger.info(f"Job created with ID: {job_id}")

        # Verify logging worked
        log_file = log_dir / "app.log"
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Creating job record" in content
            assert job_id in content

        # Verify database operation worked
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
            assert cursor.fetchone() is not None


class TestUTF8RoundtripIntegration:
    """Integration tests for UTF-8 handling across all components."""

    def test_utf8_roundtrip_all_components(self, clean_environment):
        """Test UTF-8 data flows correctly through all components."""
        base_path = clean_environment / "app"

        # Test data with various Unicode characters
        test_data = {
            "emoji": "Hello 😀 World 🎉",
            "chinese": "测试中文字符",
            "mixed": "Émojis and 中文 together!",
            "file_path": "C:/Users/测试/Documents/文档.docx"
        }

        # 1. Write to ConfigManager
        config_path = base_path / "config.json"
        config = ConfigManager(config_path)
        config.set("test.emoji", test_data["emoji"])
        config.set("test.chinese", test_data["chinese"])
        config.set("test.mixed", test_data["mixed"])

        # Verify config file is UTF-8
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
            assert test_data["emoji"] in config_content
            assert test_data["chinese"] in config_content

        # 2. Log Unicode messages
        log_dir = base_path / "logs"
        logger = setup_logger(log_dir=log_dir)
        logger.info(test_data["emoji"])
        logger.info(test_data["chinese"])
        logger.info(test_data["mixed"])
        logger.info(f"Processing file: {test_data['file_path']}")

        # Verify log file is UTF-8
        log_file = log_dir / "app.log"
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert test_data["emoji"] in log_content
            assert test_data["chinese"] in log_content
            assert test_data["file_path"] in log_content

        # 3. Store in database
        db_path = base_path / "data" / "app.db"
        db = DatabaseManager(db_path)

        job_id = db.generate_id()
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Insert job with Unicode in config
            cursor.execute("""
                INSERT INTO jobs (id, created_at, operation, config, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                job_id,
                datetime.now().isoformat(),
                test_data["emoji"],
                json.dumps({"message": test_data["chinese"]}, ensure_ascii=False),
                "pending"
            ))

            # Insert job result with Unicode file path
            result_id = db.generate_id()
            cursor.execute("""
                INSERT INTO job_results (id, job_id, file_path, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (result_id, job_id, test_data["file_path"], "success", datetime.now().isoformat()))

        # 4. Read back from database and verify
        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT operation, config FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            assert row["operation"] == test_data["emoji"]
            config_data = json.loads(row["config"])
            assert config_data["message"] == test_data["chinese"]

            cursor.execute("SELECT file_path FROM job_results WHERE id = ?", (result_id,))
            row = cursor.fetchone()
            assert row["file_path"] == test_data["file_path"]

    def test_utf8_config_persistence(self, clean_environment):
        """Test UTF-8 config values persist across reloads."""
        config_path = clean_environment / "config.json"

        # Write UTF-8 data
        config1 = ConfigManager(config_path)
        config1.set("unicode.emoji", "🎉🎊🎈")
        config1.set("unicode.japanese", "日本語")
        config1.set("unicode.arabic", "العربية")

        # Reload config
        config2 = ConfigManager(config_path)

        # Verify data preserved
        assert config2.get("unicode.emoji") == "🎉🎊🎈"
        assert config2.get("unicode.japanese") == "日本語"
        assert config2.get("unicode.arabic") == "العربية"


class TestWindowsSpecificUTF8:
    """Windows-specific UTF-8 and path handling tests."""

    def test_unicode_paths_with_spaces(self, clean_environment):
        """Test handling of Windows paths with spaces and Unicode."""
        base_path = clean_environment / "app"

        # Create nested Unicode directory
        unicode_dir = base_path / "测试目录 with spaces" / "子目录"
        unicode_dir.mkdir(parents=True, exist_ok=True)

        # Create config in Unicode path
        config_path = unicode_dir / "config.json"
        config = ConfigManager(config_path)
        config.set("test.path", str(unicode_dir))

        # Verify config created and readable
        assert config_path.exists()
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert "测试目录 with spaces" in data["test"]["path"]

        # Create log in Unicode path
        log_dir = unicode_dir / "logs"
        logger = setup_logger(log_dir=log_dir)
        logger.info("Logging to Unicode path")

        # Verify log created
        log_file = log_dir / "app.log"
        assert log_file.exists()

        # Create database in Unicode path
        db_path = unicode_dir / "data" / "app.db"
        db = DatabaseManager(db_path)

        # Verify database created
        assert db_path.exists()

    def test_unicode_file_paths_in_database(self, clean_environment):
        """Test storing Unicode file paths in database."""
        db_path = clean_environment / "data" / "app.db"
        db = DatabaseManager(db_path)

        # Test various Unicode file paths
        test_paths = [
            "C:/Users/用户/Documents/文档.docx",
            "C:/Program Files/应用程序/file.docx",
            "\\\\server\\共享\\folder\\文件.docx",
            "C:/Users/Émile/Documents/résumé.docx"
        ]

        job_id = db.generate_id()
        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO jobs (id, created_at, operation, config, status)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, datetime.now().isoformat(), "test", "{}", "pending"))

            # Insert results with Unicode paths
            for path in test_paths:
                result_id = db.generate_id()
                cursor.execute("""
                    INSERT INTO job_results (id, job_id, file_path, status, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (result_id, job_id, path, "success", datetime.now().isoformat()))

        # Verify all paths stored correctly
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM job_results WHERE job_id = ?", (job_id,))
            stored_paths = [row["file_path"] for row in cursor.fetchall()]

        assert set(stored_paths) == set(test_paths)

    def test_first_run_setup(self, clean_environment):
        """Test first-run scenario with missing directories and files."""
        base_path = clean_environment / "fresh_install"

        # Verify nothing exists initially
        assert not base_path.exists()

        # Initialize components (should create everything)
        config_path = base_path / "config.json"
        log_dir = base_path / "logs"
        db_path = base_path / "data" / "app.db"

        config = ConfigManager(config_path)
        logger = setup_logger(log_dir=log_dir, config=config)
        db = DatabaseManager(db_path)

        # Verify all directories and files created
        assert base_path.exists()
        assert config_path.exists()
        assert log_dir.exists()
        assert (log_dir / "app.log").exists()
        assert db_path.parent.exists()
        assert db_path.exists()

        # Verify defaults generated
        assert config.get("version") == "1.0.0"
        assert config.get("backup.retention_days") == 7

        # Verify logger works
        logger.info("First run test")
        with open(log_dir / "app.log", 'r', encoding='utf-8') as f:
            assert "First run test" in f.read()

        # Verify database has schema
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            table_count = cursor.fetchone()["count"]
            assert table_count == 5  # 5 tables


class TestConcurrentOperations:
    """Integration tests for concurrent operations across components."""

    def test_database_concurrent_writes(self, clean_environment):
        """Test thread-safe concurrent database writes."""
        db_path = clean_environment / "data" / "app.db"
        db = DatabaseManager(db_path)

        errors = []
        write_counts = []

        def worker_thread(thread_id: int):
            """Write job records from a thread."""
            try:
                local_count = 0
                for i in range(10):
                    job_id = db.generate_id()
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO jobs (id, created_at, operation, config, status)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            job_id,
                            datetime.now().isoformat(),
                            f"thread{thread_id}_op{i}",
                            "{}",
                            "pending"
                        ))
                        local_count += 1
                write_counts.append(local_count)
            except Exception as e:
                errors.append(e)

        # Create and start 10 threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0

        # Verify all writes succeeded
        assert sum(write_counts) == 100

        # Verify database has all records
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM jobs")
            assert cursor.fetchone()["count"] == 100

    def test_config_logger_database_workflow(self, clean_environment):
        """Test complete workflow with all components."""
        base_path = clean_environment / "workflow"

        # Step 1: Initialize all components
        config = ConfigManager(base_path / "config.json")
        logger = setup_logger(log_dir=base_path / "logs", config=config)
        db = DatabaseManager(base_path / "data" / "app.db")

        logger.info("Starting workflow test")

        # Step 2: Configure backup settings
        backup_dir = str(base_path / "backups")
        config.set("backup.directory", backup_dir)
        config.set("backup.retention_days", 30)

        logger.info(f"Configured backup directory: {backup_dir}")

        # Step 3: Create job in database
        job_id = db.generate_id()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (id, created_at, operation, config, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                job_id,
                datetime.now().isoformat(),
                "search_replace",
                json.dumps({"find": "old", "replace": "new"}, ensure_ascii=False),
                "running"
            ))

        logger.info(f"Created job {job_id}")

        # Step 4: Create backup record
        backup_id = db.generate_id()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO backups (id, job_id, original_path, backup_path, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                backup_id,
                job_id,
                "test.docx",
                f"{backup_dir}/test_backup.docx",
                datetime.now().isoformat()
            ))

        logger.info(f"Created backup {backup_id}")

        # Step 5: Update job status
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs SET status = ?, completed_at = ?
                WHERE id = ?
            """, ("completed", datetime.now().isoformat(), job_id))

        logger.info(f"Completed job {job_id}")

        # Verify workflow completed successfully
        assert config.get("backup.retention_days") == 30

        with open(base_path / "logs" / "app.log", 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert "Starting workflow test" in log_content
            assert job_id in log_content
            assert backup_id in log_content

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
            assert cursor.fetchone()["status"] == "completed"
