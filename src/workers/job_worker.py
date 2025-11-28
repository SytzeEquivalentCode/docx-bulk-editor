"""
JobWorker QThread for orchestrating document processing with multiprocessing.

This module provides a background worker thread that manages document processing
jobs using a multiprocessing pool for CPU-bound operations while keeping the UI
responsive.
"""

import multiprocessing
from multiprocessing import Pool, cpu_count
from typing import List, Dict, Any, Optional
from pathlib import Path
import importlib
import time

from PySide6.QtCore import QThread, Signal

from src.database.db_manager import DatabaseManager
from src.core.backup import BackupManager
from src.core.logger import setup_logger

logger = setup_logger()


class JobWorker(QThread):
    """
    Background worker for document processing with multiprocessing pool.

    This QThread handles job orchestration, managing a multiprocessing pool for
    CPU-bound document processing operations. It provides thread-safe signals
    for UI updates and supports cancellation.

    Signals:
        progress_updated(int, str, int, int): Emitted when progress changes
            - percentage: Overall completion percentage (0-100)
            - current_file: Path of file currently being processed
            - success_count: Number of successfully processed files
            - failure_count: Number of failed files

        job_completed(dict): Emitted when job finishes (success or cancelled)
            - job_id: Job identifier
            - status: 'completed' or 'cancelled'
            - total_files: Total number of files
            - success_count: Number of successful files
            - failure_count: Number of failed files
            - duration_seconds: Total processing time

        error_occurred(str): Emitted when an unrecoverable error occurs
            - error_message: Description of the error

    Threading Model:
        - Runs in background QThread (not main UI thread)
        - Creates multiprocessing Pool for document processing
        - Uses signals for thread-safe UI communication
        - Supports graceful cancellation via cancel() method
    """

    # Qt Signals for thread-safe UI updates
    progress_updated = Signal(int, str, int, int)  # (percentage, current_file, success_count, failure_count)
    job_completed = Signal(dict)  # final results
    error_occurred = Signal(str)  # error message

    def __init__(
        self,
        job_id: str,
        files: List[str],
        operation: str,
        config: Dict[str, Any],
        db_manager: DatabaseManager,
        backup_manager: BackupManager,
        pool_size: Optional[int] = None
    ):
        """
        Initialize JobWorker thread.

        Args:
            job_id: Unique identifier for this job (from database)
            files: List of file paths to process
            operation: Operation name ('search_replace', 'metadata', etc.)
            config: Operation-specific configuration dictionary
            db_manager: Database manager for storing results
            backup_manager: Backup manager for creating file backups
            pool_size: Number of worker processes (default: cpu_count - 1)
        """
        super().__init__()

        self.job_id = job_id
        self.files = files
        self.operation = operation
        self.config = config
        self.db_manager = db_manager
        self.backup_manager = backup_manager

        # Calculate optimal pool size: leave 1 core for UI thread
        self.pool_size = pool_size if pool_size is not None else max(1, cpu_count() - 1)

        # Cancellation flag (thread-safe via GIL)
        self._cancelled = False

        logger.info(
            f"JobWorker initialized: job_id={job_id}, operation={operation}, "
            f"files={len(files)}, pool_size={self.pool_size}"
        )

    def run(self):
        """
        Execute the job in background thread.

        This method is called when start() is invoked. It should not be called directly.
        Override of QThread.run() for background execution.

        The execution flow:
        1. Update job status to 'running'
        2. Load processor module dynamically
        3. Create backups for all files
        4. Process files using multiprocessing pool
        5. Update job status on completion
        6. Emit completion signal

        Handles cancellation gracefully and ensures proper cleanup.
        """
        start_time = time.time()

        try:
            # Update job status to running
            logger.info(f"JobWorker.run() started for job {self.job_id}")
            self._update_job_status('running', started_at=time.time())

            # Load processor module dynamically
            processor_module = self._load_processor()
            if processor_module is None:
                raise ValueError(f"Unknown operation: {self.operation}")

            # Create backups for all files before processing
            logger.info(f"Creating backups for {len(self.files)} files")
            backup_paths = {}
            backup_failures = []

            for file_path in self.files:
                try:
                    backup_path = self.backup_manager.create_backup(Path(file_path), self.job_id)
                    if backup_path:
                        backup_paths[file_path] = str(backup_path)
                        logger.debug(f"Backup created: {file_path} -> {backup_path}")
                    else:
                        # Backup creation failed
                        backup_failures.append(file_path)
                        logger.warning(f"Backup creation failed for: {file_path}")
                except Exception as e:
                    backup_failures.append(file_path)
                    logger.error(f"Error creating backup for {file_path}: {e}")

            # Log backup summary
            if backup_failures:
                logger.warning(
                    f"Backup failures: {len(backup_failures)}/{len(self.files)} files. "
                    f"Processing will continue, but these files may not be recoverable on error."
                )
            else:
                logger.info(f"All {len(self.files)} backups created successfully")

            # Get timeout from config (default: 60 seconds per file)
            timeout_per_file = self.config.get('timeout_per_file_seconds', 60)

            # Process files with multiprocessing pool
            logger.info(f"Creating multiprocessing pool with {self.pool_size} processes")

            # Use context manager for proper pool cleanup
            with Pool(processes=self.pool_size) as pool:
                logger.info(f"Pool created successfully with {self.pool_size} worker processes")

                results = []
                success_count = 0
                failure_count = 0

                # Job submission loop - submit all jobs to pool
                logger.info(f"Submitting {len(self.files)} jobs to multiprocessing pool")

                for i, file_path in enumerate(self.files):
                    if self._cancelled:
                        logger.info("Job cancelled by user during submission")
                        break

                    # Submit async job to pool
                    async_result = pool.apply_async(
                        processor_module.process_document,
                        args=(file_path, self.config)
                    )
                    results.append((file_path, async_result))
                    logger.debug(f"Submitted job {i+1}/{len(self.files)}: {file_path}")

                logger.info(f"Submitted {len(results)} jobs for processing")

                # Result collection loop - collect results and emit progress
                logger.info("Collecting results from worker processes")

                for i, (file_path, async_result) in enumerate(results):
                    if self._cancelled:
                        logger.info("Job cancelled by user during collection")
                        break

                    try:
                        # Get result with timeout (blocks until worker completes or times out)
                        result = async_result.get(timeout=timeout_per_file)

                        # Update counters based on result
                        if result.success:
                            success_count += 1
                            logger.debug(f"Success: {file_path} ({result.changes_made} changes)")
                        else:
                            failure_count += 1
                            logger.warning(f"Failed: {file_path} - {result.error_message}")

                        # Store result in database
                        self._store_result(result, backup_paths.get(file_path))

                        # Calculate progress percentage
                        progress = int((i + 1) / len(results) * 100)

                        # Emit progress signal to UI (thread-safe)
                        self.progress_updated.emit(
                            progress,
                            file_path,
                            success_count,
                            failure_count
                        )

                        logger.debug(
                            f"Progress: {progress}% "
                            f"(success={success_count}, failed={failure_count})"
                        )

                    except multiprocessing.TimeoutError:
                        # Processing exceeded timeout limit
                        logger.error(
                            f"Timeout processing {file_path} "
                            f"(exceeded {timeout_per_file}s limit)"
                        )
                        failure_count += 1
                        self._store_error_result(file_path, "Processing timeout")

                    except Exception as e:
                        # Unexpected error during result retrieval
                        logger.error(f"Error processing {file_path}: {e}", exc_info=True)
                        failure_count += 1
                        self._store_error_result(file_path, str(e))

                logger.info(
                    f"Result collection complete: "
                    f"{len(results)} processed, {success_count} success, {failure_count} failed"
                )

                # Pool will be automatically closed and joined here by context manager
                logger.info("Multiprocessing pool closed successfully")

            # Update job completion
            duration = time.time() - start_time
            status = 'cancelled' if self._cancelled else 'completed'
            self._update_job_status(
                status,
                completed_at=time.time(),
                duration_seconds=duration,
                success_count=success_count,
                failure_count=failure_count
            )

            # Emit completion signal
            self.job_completed.emit({
                'job_id': self.job_id,
                'status': status,
                'total_files': len(self.files),
                'success_count': success_count,
                'failure_count': failure_count,
                'duration_seconds': duration
            })

            logger.info(
                f"Job {self.job_id} {status}: "
                f"success={success_count}, failed={failure_count}, "
                f"duration={duration:.1f}s"
            )

        except Exception as e:
            # Handle unrecoverable errors
            logger.exception(f"Job worker error: {e}")
            self._update_job_status('failed', error_message=str(e))
            self.error_occurred.emit(str(e))

    def cancel(self):
        """
        Request cancellation of the job.

        This method is thread-safe and can be called from the UI thread.
        The worker will stop processing at the next safe checkpoint.

        The cancellation is checked at two points:
        1. During job submission loop
        2. During result collection loop

        This ensures graceful cancellation without data corruption.
        """
        self._cancelled = True
        logger.info(f"Cancellation requested for job {self.job_id}")

    def _load_processor(self):
        """
        Dynamically load the processor module for the specified operation.

        This method uses importlib to dynamically import the appropriate processor
        module based on the operation type. This allows adding new processors
        without modifying the worker code.

        Returns:
            module: The processor module containing process_document() function
            None: If operation is unknown

        Supported operations:
            - search_replace: Search and replace text operations
            - metadata: Document metadata management
        """
        # Map operation names to module paths
        processor_map = {
            'search_replace': 'src.processors.search_replace',
            'metadata': 'src.processors.metadata',
        }

        module_name = processor_map.get(self.operation)

        if module_name:
            try:
                module = importlib.import_module(module_name)
                logger.info(f"Loaded processor module: {module_name}")
                return module
            except ImportError as e:
                logger.error(f"Failed to import processor module {module_name}: {e}")
                return None
        else:
            logger.error(f"Unknown operation: {self.operation}")
            return None

    def _update_job_status(self, status: str, **kwargs):
        """
        Update job record in database with new status and optional fields.

        Args:
            status: New job status ('running', 'completed', 'cancelled', 'failed')
            **kwargs: Additional fields to update (e.g., started_at, duration_seconds)

        Example:
            self._update_job_status('running', started_at=time.time())
            self._update_job_status('completed', completed_at=time.time(),
                                   duration_seconds=123.45, success_count=10)
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Build dynamic UPDATE query
                updates = ['status = ?']
                values = [status]

                # Add any additional fields from kwargs
                for key, value in kwargs.items():
                    updates.append(f'{key} = ?')
                    values.append(value)

                # Add job_id as final parameter for WHERE clause
                values.append(self.job_id)

                # Execute UPDATE query
                query = f'UPDATE jobs SET {", ".join(updates)} WHERE id = ?'
                cursor.execute(query, values)
                conn.commit()

                logger.debug(f"Updated job {self.job_id} status to '{status}' with {len(kwargs)} fields")

        except Exception as e:
            logger.error(f"Failed to update job status: {e}", exc_info=True)

    def _store_result(self, result, backup_path: Optional[str] = None):
        """
        Store a successful or failed processing result in the database.

        Args:
            result: ProcessorResult object from document processor
            backup_path: Optional path to backup file for this result

        The result is stored in the job_results table with all relevant details
        including success/failure status, changes made, duration, and error message.
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Determine status based on result.success
                status = 'success' if result.success else 'failed'

                # Insert job result record
                cursor.execute(
                    '''
                    INSERT INTO job_results (
                        id, job_id, file_path, status, duration_seconds,
                        changes_made, error_message, backup_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        self.db_manager.generate_id(),
                        self.job_id,
                        result.file_path,
                        status,
                        result.duration_seconds,
                        result.changes_made,
                        result.error_message,
                        backup_path
                    )
                )
                conn.commit()

                logger.debug(
                    f"Stored result for {result.file_path}: "
                    f"status={status}, changes={result.changes_made}"
                )

        except Exception as e:
            logger.error(f"Failed to store result for {result.file_path}: {e}", exc_info=True)

    def _store_error_result(self, file_path: str, error_message: str):
        """
        Store an error result when processing fails completely.

        This is used when processing fails before a ProcessorResult can be created,
        such as timeouts or unexpected exceptions during job execution.

        Args:
            file_path: Path to file that failed
            error_message: Description of the error
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Insert failed job result record
                cursor.execute(
                    '''
                    INSERT INTO job_results (
                        id, job_id, file_path, status, error_message
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (
                        self.db_manager.generate_id(),
                        self.job_id,
                        file_path,
                        'failed',
                        error_message
                    )
                )
                conn.commit()

                logger.debug(f"Stored error result for {file_path}: {error_message}")

        except Exception as e:
            logger.error(
                f"Failed to store error result for {file_path}: {e}",
                exc_info=True
            )
