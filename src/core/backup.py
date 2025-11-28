"""Backup management with automatic cleanup and validation."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from docx import Document

from src.core.logger import get_logger
from src.database.db_manager import DatabaseManager

logger = get_logger()


class BackupManager:
    """Manages document backups with validation and cleanup.

    Features:
    - Automatic backup creation before file modification
    - Daily subdirectory organization (YYYY-MM-DD)
    - Timestamp-based naming
    - python-docx validation of backup integrity
    - Database tracking of all backups
    - Automatic cleanup based on retention policy
    """

    def __init__(
        self,
        backup_dir: Path,
        db_manager: DatabaseManager,
        retention_days: int = 7
    ):
        """Initialize BackupManager.

        Args:
            backup_dir: Directory for storing backups
            db_manager: DatabaseManager instance for tracking backups
            retention_days: Number of days to retain backups (default: 7)
        """
        self.backup_dir = Path(backup_dir)
        self.db_manager = db_manager
        self.retention_days = retention_days

        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        file_path: Path,
        job_id: Optional[str] = None
    ) -> Optional[Path]:
        """Create backup with validation before modification.

        Creates a backup in a daily subdirectory with timestamp-based naming:
        {backup_dir}/{YYYY-MM-DD}/{original_name}.{YYYYMMDD_HHMMSS}.backup.docx

        Args:
            file_path: Path to file to backup
            job_id: Optional job ID to associate with backup

        Returns:
            Path to backup file if successful, None if failed

        Examples:
            >>> manager = BackupManager(Path("backups"), db_manager)
            >>> backup_path = manager.create_backup(Path("document.docx"))
            >>> print(backup_path)
            backups/2025-01-26/document.20250126_143022.backup.docx
        """
        try:
            # Ensure source file exists
            if not file_path.exists():
                logger.error(f"Source file not found: {file_path}")
                return None

            # Create daily subdirectory (YYYY-MM-DD format)
            daily_dir = self.backup_dir / datetime.now().strftime('%Y-%m-%d')
            daily_dir.mkdir(parents=True, exist_ok=True)

            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{file_path.stem}.{timestamp}.backup{file_path.suffix}"
            backup_path = daily_dir / backup_name

            # Copy file with metadata preservation
            shutil.copy2(file_path, backup_path)

            # Validate backup is readable
            if not self._validate_backup(backup_path):
                logger.error(f"Backup validation failed: {backup_path}")
                backup_path.unlink(missing_ok=True)
                return None

            # Record backup in database
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO backups (
                        id, original_path, backup_path,
                        created_at, size_bytes, job_id, restored
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.db_manager.generate_id(),
                        str(file_path.resolve()),  # Store absolute path
                        str(backup_path.resolve()),
                        datetime.now().isoformat(),
                        backup_path.stat().st_size,
                        job_id,
                        0  # Not restored
                    )
                )
                conn.commit()

            logger.info(f"Backup created: {file_path.name} -> {backup_path}")
            return backup_path

        except PermissionError as e:
            logger.error(f"Permission denied creating backup for {file_path}: {e}")
            return None
        except OSError as e:
            logger.error(f"OS error creating backup for {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return None

    def _validate_backup(self, backup_path: Path) -> bool:
        """Validate backup file is readable with python-docx.

        Args:
            backup_path: Path to backup file

        Returns:
            True if backup is valid and readable, False otherwise
        """
        try:
            # Attempt to load document with python-docx
            doc = Document(backup_path)

            # Basic validation: ensure we can read paragraphs
            _ = len(doc.paragraphs)

            return True

        except Exception as e:
            logger.warning(f"Backup validation failed for {backup_path}: {e}")
            return False

    def restore_backup(
        self,
        backup_path: Path,
        target_path: Optional[Path] = None
    ) -> bool:
        """Restore backup to original or specified location.

        If target_path is not provided, looks up the original path from the database.
        Updates the database to mark the backup as restored.

        Args:
            backup_path: Path to backup file
            target_path: Optional target path for restoration (defaults to original)

        Returns:
            True if restoration successful, False otherwise

        Examples:
            >>> manager = BackupManager(Path("backups"), db_manager)
            >>> # Restore to original location
            >>> success = manager.restore_backup(backup_path)
            >>> # Restore to different location
            >>> success = manager.restore_backup(backup_path, Path("new_location.docx"))
        """
        try:
            # Ensure backup exists
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            # Lookup target path from database if not provided
            if target_path is None:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT original_path FROM backups WHERE backup_path = ?",
                        (str(backup_path.resolve()),)
                    )
                    row = cursor.fetchone()

                    if row is None:
                        logger.error(f"Original path not found in database for: {backup_path}")
                        return False

                    target_path = Path(row["original_path"])

            # Create target directory if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy backup to target with metadata preservation
            shutil.copy2(backup_path, target_path)

            # Update database to mark as restored
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE backups
                    SET restored = 1, restored_at = ?
                    WHERE backup_path = ?
                    """,
                    (datetime.now().isoformat(), str(backup_path.resolve()))
                )
                conn.commit()

            logger.info(f"Backup restored: {backup_path.name} -> {target_path}")
            return True

        except PermissionError as e:
            logger.error(f"Permission denied restoring {backup_path}: {e}")
            return False
        except OSError as e:
            logger.error(f"OS error restoring {backup_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_path}: {e}")
            return False

    def cleanup_old_backups(self) -> int:
        """Remove backups older than retention_days.

        Only removes backups that have not been restored (restored=0).
        Deletes both the backup files and their database records.

        Returns:
            Number of backups deleted

        Examples:
            >>> manager = BackupManager(Path("backups"), db_manager, retention_days=7)
            >>> deleted = manager.cleanup_old_backups()
            >>> print(f"Deleted {deleted} old backups")
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Find old backups that haven't been restored
                cursor.execute(
                    """
                    SELECT id, backup_path FROM backups
                    WHERE created_at < ? AND restored = 0
                    """,
                    (cutoff_date.isoformat(),)
                )
                old_backups = cursor.fetchall()

                # Delete backup files
                for row in old_backups:
                    backup_path = Path(row["backup_path"])
                    if backup_path.exists():
                        try:
                            backup_path.unlink()
                            deleted_count += 1
                        except PermissionError:
                            logger.warning(f"Permission denied deleting {backup_path}")
                        except OSError as e:
                            logger.warning(f"Error deleting {backup_path}: {e}")

                # Delete database records
                cursor.execute(
                    """
                    DELETE FROM backups
                    WHERE created_at < ? AND restored = 0
                    """,
                    (cutoff_date.isoformat(),)
                )
                conn.commit()

            logger.info(f"Cleaned up {deleted_count} old backups (older than {self.retention_days} days)")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0

    def get_backup_storage_usage(self) -> int:
        """Return total backup storage in bytes.

        Calculates total size of all backup files in the backup directory.

        Returns:
            Total size in bytes

        Examples:
            >>> manager = BackupManager(Path("backups"), db_manager)
            >>> size_bytes = manager.get_backup_storage_usage()
            >>> size_mb = size_bytes / (1024 * 1024)
            >>> print(f"Backups using {size_mb:.2f} MB")
        """
        total_size = 0

        try:
            # Find all .backup.docx files recursively
            for backup_file in self.backup_dir.rglob("*.backup.docx"):
                try:
                    total_size += backup_file.stat().st_size
                except (FileNotFoundError, PermissionError):
                    # Skip files that can't be accessed
                    continue

            return total_size

        except Exception as e:
            logger.error(f"Failed to calculate backup storage usage: {e}")
            return 0
