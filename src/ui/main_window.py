"""
Main application window for DOCX Bulk Editor.

This module provides the primary user interface for the application, including:
- Operation selection (Search & Replace, Metadata, etc.)
- Dynamic configuration panels
- File selection with drag-and-drop support
- Job orchestration and progress monitoring
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QGroupBox, QLineEdit, QCheckBox,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from src.core.config import ConfigManager
from src.core.logger import setup_logger
from src.database.db_manager import DatabaseManager
from src.core.backup import BackupManager
from src.workers.job_worker import JobWorker
from src.ui.progress_dialog import ProgressDialog

logger = setup_logger()


class MainWindow(QMainWindow):
    """
    Main application window for DOCX Bulk Editor.

    Provides a complete UI for selecting operations, configuring parameters,
    selecting files, and monitoring processing jobs.

    Architecture:
        - Uses QMainWindow as base for menu/toolbar support
        - Dynamic configuration panels that change based on operation
        - Drag-and-drop file selection
        - Integrates with JobWorker for background processing
        - Persists window geometry in configuration

    Attributes:
        config: ConfigManager for application settings
        db_manager: DatabaseManager for job/result storage
        backup_manager: BackupManager for file backups
        selected_files: List of files to process
        current_operation: Currently selected operation type
        worker: Active JobWorker thread (if running)
    """

    def __init__(self, config: ConfigManager, db_manager: DatabaseManager):
        """
        Initialize main window.

        Args:
            config: Configuration manager instance
            db_manager: Database manager instance
        """
        super().__init__()

        # Store managers
        self.config = config
        self.db_manager = db_manager

        # Initialize backup manager from config
        self.backup_manager = BackupManager(
            Path(config.get('backup.directory', './backups')),
            db_manager,
            config.get('backup.retention_days', 7)
        )

        # Initialize state
        self.selected_files: List[Path] = []
        self.current_operation: str = 'search_replace'
        self.worker: Optional[JobWorker] = None
        self.progress_dialog: Optional[ProgressDialog] = None
        self.operation_buttons: dict = {}

        # Build UI
        self._init_ui()

        # Load saved window geometry
        self._load_window_geometry()

        logger.info("MainWindow initialized")

    def _init_ui(self):
        """Initialize user interface components."""
        # Set window properties
        self.setWindowTitle('DOCX Bulk Editor v1.0')

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Add operation selector
        operation_group = self._create_operation_selector()
        main_layout.addWidget(operation_group)

        # Add dynamic configuration panel
        self.config_panel = self._create_config_panel()
        main_layout.addWidget(self.config_panel)

        # Add file selection
        file_group = self._create_file_selection()
        main_layout.addWidget(file_group, stretch=1)

        # Add start button
        start_layout = QHBoxLayout()
        self.start_button = QPushButton('Start Processing')
        self.start_button.setFixedHeight(40)
        self.start_button.setEnabled(False)  # Disabled until files are selected
        self.start_button.clicked.connect(self._on_start_clicked)
        start_layout.addStretch()
        start_layout.addWidget(self.start_button)
        start_layout.addStretch()
        main_layout.addLayout(start_layout)

        # Enable drag and drop
        self.setAcceptDrops(True)

        logger.debug("UI initialized")

    def _create_operation_selector(self) -> QGroupBox:
        """
        Create operation selector with checkable buttons.

        Returns:
            QGroupBox containing operation selector buttons

        The buttons are mutually exclusive - only one can be checked at a time.
        """
        group = QGroupBox('Select Operation')
        layout = QHBoxLayout()

        # Define available operations
        operations = [
            ('search_replace', 'Search & Replace'),
            ('metadata', 'Metadata'),
            ('table_format', 'Table Format'),
            ('style_enforce', 'Style'),
            ('validate', 'Validate')
        ]

        # Create buttons
        for op_id, op_label in operations:
            btn = QPushButton(op_label)
            btn.setCheckable(True)
            btn.clicked.connect(
                lambda checked, oid=op_id: self._on_operation_selected(oid)
            )
            self.operation_buttons[op_id] = btn
            layout.addWidget(btn)

        # Select first operation by default
        self.operation_buttons['search_replace'].setChecked(True)
        self.current_operation = 'search_replace'

        layout.addStretch()
        group.setLayout(layout)

        return group

    def _on_operation_selected(self, operation: str):
        """
        Handle operation selection.

        Ensures only one operation button is checked at a time and updates
        the configuration panel to match the selected operation.

        Args:
            operation: Operation ID that was selected
        """
        # Uncheck all other buttons (mutually exclusive)
        for op_id, btn in self.operation_buttons.items():
            if op_id != operation:
                btn.setChecked(False)

        # Update current operation
        self.current_operation = operation

        # Update configuration panel
        if operation == 'search_replace':
            self._show_search_replace_config()
        else:
            # Clear config panel for unsupported operations
            self._clear_config_panel()
            # TODO: Add other operation configs (metadata, table_format, etc.)

        logger.debug(f"Operation selected: {operation}")

    def _create_config_panel(self) -> QGroupBox:
        """
        Create dynamic configuration panel.

        The panel content changes based on the selected operation.
        Widget lifecycle is managed to prevent memory leaks.

        Returns:
            QGroupBox containing operation configuration widgets
        """
        group = QGroupBox('Operation Configuration')
        self.config_layout = QVBoxLayout()

        # Show search & replace config by default
        self._show_search_replace_config()

        group.setLayout(self.config_layout)
        return group

    def _clear_config_panel(self):
        """
        Clear all widgets from the configuration panel.

        This removes and deletes all widgets to prevent memory leaks
        and prepares the panel for new content.
        """
        # Remove all widgets from layout
        while self.config_layout.count():
            item = self.config_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.deleteLater()

        # Remove attribute references for all known config widgets
        config_attrs = ['search_input', 'replace_input', 'regex_checkbox', 'case_checkbox']
        for attr in config_attrs:
            if hasattr(self, attr):
                delattr(self, attr)

        logger.debug("Config panel cleared")

    def _show_search_replace_config(self):
        """
        Show configuration widgets for search & replace operation.

        Clears existing widgets and creates:
        - Search term input with regex checkbox
        - Replace term input with case-sensitive checkbox
        - Scope checkboxes (body, tables, headers, footers, whole words)
        """
        # Clear existing widgets (prevent memory leaks)
        self._clear_config_panel()

        # Search term row
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel('Search for:'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Enter text or regex pattern...')
        search_layout.addWidget(self.search_input, stretch=1)
        self.regex_check = QCheckBox('Regex')
        search_layout.addWidget(self.regex_check)
        self.config_layout.addLayout(search_layout)

        # Replace term row
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel('Replace with:'))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText('Enter replacement text...')
        replace_layout.addWidget(self.replace_input, stretch=1)
        self.case_check = QCheckBox('Case Sensitive')
        replace_layout.addWidget(self.case_check)
        self.config_layout.addLayout(replace_layout)

        # Options row
        options_layout = QHBoxLayout()
        self.body_check = QCheckBox('Body')
        self.body_check.setChecked(True)
        self.tables_check = QCheckBox('Tables')
        self.tables_check.setChecked(True)
        self.headers_check = QCheckBox('Headers')
        self.headers_check.setChecked(True)
        self.footers_check = QCheckBox('Footers')
        self.footers_check.setChecked(True)
        self.whole_words_check = QCheckBox('Whole words only')

        options_layout.addWidget(self.body_check)
        options_layout.addWidget(self.tables_check)
        options_layout.addWidget(self.headers_check)
        options_layout.addWidget(self.footers_check)
        options_layout.addWidget(self.whole_words_check)
        options_layout.addStretch()
        self.config_layout.addLayout(options_layout)

    def _create_file_selection(self) -> QGroupBox:
        """
        Create file selection widget.

        Provides:
        - Add Files button (opens file dialog)
        - Add Folder button (recursive scan)
        - Clear All button
        - File list display
        - File count and total size label

        Returns:
            QGroupBox containing file selection UI
        """
        group = QGroupBox('File Selection')
        layout = QVBoxLayout()

        # Button row
        button_layout = QHBoxLayout()
        add_files_btn = QPushButton('Add Files')
        add_files_btn.clicked.connect(self._on_add_files)
        add_folder_btn = QPushButton('Add Folder')
        add_folder_btn.clicked.connect(self._on_add_folder)
        clear_btn = QPushButton('Clear All')
        clear_btn.clicked.connect(self._on_clear_files)

        button_layout.addWidget(add_files_btn)
        button_layout.addWidget(add_folder_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.file_list)

        # File count label
        self.file_count_label = QLabel('0 files selected | 0.0 MB total')
        layout.addWidget(self.file_count_label)

        group.setLayout(layout)
        return group

    def _on_add_files(self):
        """
        Add files via file dialog.

        Opens a file dialog allowing multiple .docx file selection.
        Prevents duplicate file additions.
        """
        files, _ = QFileDialog.getOpenFileNames(
            self,
            'Select DOCX Files',
            '',
            'Word Documents (*.docx)'
        )

        # Add selected files (avoiding duplicates)
        for file_path in files:
            path = Path(file_path)
            if path not in self.selected_files:
                self.selected_files.append(path)
                self.file_list.addItem(str(path))
                logger.debug(f"Added file: {path}")

        self._update_file_count()
        logger.info(f"Added {len(files)} files via dialog")

    def _on_add_folder(self):
        """
        Add folder via dialog with recursive .docx scan.

        Opens a folder dialog and recursively scans for all .docx files.
        Prevents duplicate file additions.
        """
        folder = QFileDialog.getExistingDirectory(self, 'Select Folder')

        if folder:
            folder_path = Path(folder)
            files_added = 0

            # Recursively find all .docx files
            for file_path in folder_path.rglob('*.docx'):
                if file_path not in self.selected_files:
                    self.selected_files.append(file_path)
                    self.file_list.addItem(str(file_path))
                    files_added += 1
                    logger.debug(f"Added file from folder: {file_path}")

            self._update_file_count()
            logger.info(f"Added {files_added} files from folder: {folder}")

    def _on_clear_files(self):
        """
        Clear all selected files.

        Removes all files from the selection list and updates the UI.
        """
        self.selected_files.clear()
        self.file_list.clear()
        self._update_file_count()
        logger.info("Cleared all selected files")

    def _update_file_count(self):
        """
        Update file count and total size label.

        Calculates total size of all selected files and updates the display label.
        """
        # Calculate total size
        total_size = 0
        for file_path in self.selected_files:
            if file_path.exists():
                total_size += file_path.stat().st_size

        # Convert to MB
        size_mb = total_size / (1024 * 1024)

        # Update label
        self.file_count_label.setText(
            f'{len(self.selected_files)} files selected | {size_mb:.1f} MB total'
        )

        # Update UI state (enable/disable buttons)
        self._update_ui_state()

    def _update_ui_state(self):
        """
        Update UI element states based on current application state.

        Syncs file list widget with selected_files and enables start button
        only when files are selected and no job is running.
        """
        # Sync file_list widget with selected_files
        self.file_list.clear()
        for file_path in self.selected_files:
            self.file_list.addItem(str(file_path))

        # Enable start button only if files are selected and no worker running
        has_files = len(self.selected_files) > 0
        no_worker = self.worker is None or not self.worker.isRunning()
        self.start_button.setEnabled(has_files and no_worker)

    def _on_start_clicked(self):
        """
        Start processing job.

        Validates inputs, creates database job record, instantiates JobWorker,
        connects signals, and starts background processing.
        """
        # Validate file selection
        if not self.selected_files:
            QMessageBox.warning(
                self,
                'No Files Selected',
                'Please select at least one file to process.'
            )
            return

        # Validate operation-specific requirements
        if self.current_operation == 'search_replace':
            if not self.search_input.text():
                QMessageBox.warning(
                    self,
                    'Missing Search Term',
                    'Please enter a search term.'
                )
                return

        # Get operation configuration
        operation_config = self._get_operation_config()

        # Create job record in database
        job_id = self.db_manager.generate_id()

        try:
            from datetime import datetime, timezone
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO jobs (id, created_at, operation, config, status, total_files)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        job_id,
                        datetime.now(timezone.utc).isoformat(),
                        self.current_operation,
                        str(operation_config),  # Store as string
                        'pending',
                        len(self.selected_files)
                    )
                )
                conn.commit()

            logger.info(
                f"Created job {job_id}: operation={self.current_operation}, "
                f"files={len(self.selected_files)}"
            )

        except Exception as e:
            logger.error(f"Failed to create job record: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                'Database Error',
                f'Failed to create job record: {e}'
            )
            return

        # Create and configure worker
        self.worker = JobWorker(
            job_id,
            [str(f) for f in self.selected_files],
            self.current_operation,
            operation_config,
            self.db_manager,
            self.backup_manager,
            self.config.get('processing.pool_size')
        )

        # Create progress dialog
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.cancelled.connect(self.worker.cancel)

        # Connect worker signals
        self.worker.progress_updated.connect(self.progress_dialog.update_progress)
        self.worker.job_completed.connect(self._on_job_completed)
        self.worker.error_occurred.connect(self._on_error)

        # Disable start button during processing
        self.start_button.setEnabled(False)

        # Start worker thread
        self.worker.start()

        # Show progress dialog
        self.progress_dialog.show()

        logger.info(f"Job {job_id} started with progress dialog")

    def _get_operation_config(self) -> dict:
        """
        Get current operation configuration as dictionary.

        Returns:
            Dictionary containing operation-specific configuration parameters
        """
        if self.current_operation == 'search_replace':
            return {
                'search_term': self.search_input.text(),
                'replace_term': self.replace_input.text(),
                'use_regex': self.regex_check.isChecked(),
                'case_sensitive': self.case_check.isChecked(),
                'whole_words': self.whole_words_check.isChecked(),
                'search_body': self.body_check.isChecked(),
                'search_tables': self.tables_check.isChecked(),
                'search_headers': self.headers_check.isChecked(),
                'search_footers': self.footers_check.isChecked()
            }

        # TODO: Add configurations for other operations
        return {}

    def _on_job_completed(self, results: dict):
        """
        Handle job completion signal from worker.

        Args:
            results: Dictionary containing job results (status, counts, duration)
        """
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.close()

        # Re-enable start button
        self.start_button.setEnabled(True)

        # Show completion dialog
        QMessageBox.information(
            self,
            'Job Complete',
            f"Processing completed!\n\n"
            f"Status: {results['status']}\n"
            f"Total files: {results['total_files']}\n"
            f"Successful: {results['success_count']}\n"
            f"Failed: {results['failure_count']}\n"
            f"Duration: {results['duration_seconds']:.1f}s"
        )

        logger.info(
            f"Job {results['job_id']} completed: "
            f"status={results['status']}, "
            f"success={results['success_count']}, "
            f"failed={results['failure_count']}"
        )

    def _on_error(self, error_message: str):
        """
        Handle job error signal from worker.

        Args:
            error_message: Error description
        """
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.close()

        # Re-enable start button
        self.start_button.setEnabled(True)

        # Show error dialog
        QMessageBox.critical(
            self,
            'Job Error',
            f'Job failed with error:\n\n{error_message}'
        )

        logger.error(f"Job error: {error_message}")

    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Accept drag events containing file URLs.

        Args:
            event: QDragEnterEvent
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            logger.debug("Drag enter event accepted")

    def dropEvent(self, event: QDropEvent):
        """
        Handle dropped files and folders.

        Processes both individual .docx files and folders (with recursive scan).
        Prevents duplicate file additions.

        Args:
            event: QDropEvent containing file URLs
        """
        files_added = 0

        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())

            if path.is_file() and path.suffix == '.docx':
                # Single file
                if path not in self.selected_files:
                    self.selected_files.append(path)
                    self.file_list.addItem(str(path))
                    files_added += 1

            elif path.is_dir():
                # Folder - recursive scan
                for file_path in path.rglob('*.docx'):
                    if file_path not in self.selected_files:
                        self.selected_files.append(file_path)
                        self.file_list.addItem(str(file_path))
                        files_added += 1

        self._update_file_count()
        logger.info(f"Added {files_added} files via drag-and-drop")

    def _on_progress_updated(
        self,
        percentage: int,
        current_file: str,
        success_count: int,
        failure_count: int
    ):
        """
        Handle progress update signal from worker.

        Args:
            percentage: Overall completion percentage
            current_file: Path of file currently being processed
            success_count: Number of successful files
            failure_count: Number of failed files
        """
        # Update progress dialog if it exists
        if self.progress_dialog:
            self.progress_dialog.update_progress(
                percentage, current_file, success_count, failure_count
            )

        # Also log for debugging
        logger.debug(
            f"Progress: {percentage}% - {current_file} "
            f"(success={success_count}, failed={failure_count})"
        )

    def _load_window_geometry(self):
        """Load window size and position from configuration."""
        width = self.config.get('ui.window_width', 1000)
        height = self.config.get('ui.window_height', 700)
        self.resize(width, height)

        logger.debug(f"Window geometry loaded: {width}x{height}")

    def closeEvent(self, event):
        """
        Save window geometry on close and cleanup resources.

        Overrides QWidget.closeEvent to persist window size to configuration
        and properly cleanup worker threads and multiprocessing pools.

        Args:
            event: QCloseEvent
        """
        # Stop and cleanup worker if running
        if self.worker is not None and self.worker.isRunning():
            logger.info("Stopping worker thread before closing...")
            self.worker.cancel()
            self.worker.wait(5000)  # Wait up to 5 seconds
            if self.worker.isRunning():
                logger.warning("Worker did not stop gracefully, terminating...")
                self.worker.terminate()
                self.worker.wait()

        # Save window geometry
        self.config.set('ui.window_width', self.width())
        self.config.set('ui.window_height', self.height())

        logger.info("Window closing, geometry saved")

        event.accept()
