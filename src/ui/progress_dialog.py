"""
Progress dialog for real-time job monitoring.

This module provides a modal dialog that displays real-time progress updates
during document processing jobs, including:
- Progress percentage and current file
- Elapsed and estimated remaining time
- Processing speed (files/min)
- Success/failure counters
- Scrollable log output
- Cancellation support
"""

import time

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QTextEdit
)
from PySide6.QtCore import Qt, Signal


class ProgressDialog(QDialog):
    """
    Modal dialog for real-time progress monitoring.

    Displays live updates during job processing with visual indicators
    for progress, time estimates, and success/failure counts.

    Signals:
        cancelled: Emitted when user clicks the Cancel button

    Attributes:
        start_time: Timestamp when dialog was created (for elapsed time calculation)
        progress_bar: QProgressBar showing overall progress (0-100%)
        current_file_label: QLabel displaying current file being processed
        elapsed_label: QLabel showing elapsed time
        remaining_label: QLabel showing estimated remaining time
        speed_label: QLabel showing processing speed
        success_label: QLabel showing successful file count
        failure_label: QLabel showing failed file count
        log_text: QTextEdit showing scrollable log of processed files
        cancel_button: QPushButton for job cancellation
    """

    # Signal emitted when user requests cancellation
    cancelled = Signal()

    def __init__(self, parent=None):
        """
        Initialize progress dialog.

        Args:
            parent: Parent widget (typically MainWindow)
        """
        super().__init__(parent)

        # Record start time for elapsed/remaining calculations
        self.start_time = time.time()

        # Build UI
        self._init_ui()

    def _init_ui(self):
        """Initialize progress dialog user interface."""
        # Window properties
        self.setWindowTitle('Processing...')
        self.setModal(True)  # Block interaction with parent window
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        # Main layout
        layout = QVBoxLayout()

        # Operation label
        self.operation_label = QLabel('Operation: Processing')
        self.operation_label.setStyleSheet('font-weight: bold; font-size: 12pt;')
        layout.addWidget(self.operation_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat('%p% Complete')
        layout.addWidget(self.progress_bar)

        # Current file label
        self.current_file_label = QLabel('Current: -')
        self.current_file_label.setWordWrap(True)
        layout.addWidget(self.current_file_label)

        # Time and speed metrics row
        metrics_layout = QHBoxLayout()
        self.elapsed_label = QLabel('Elapsed: 00:00:00')
        self.remaining_label = QLabel('Remaining: --:--:--')
        self.speed_label = QLabel('Speed: -- files/min')

        metrics_layout.addWidget(self.elapsed_label)
        metrics_layout.addWidget(self.remaining_label)
        metrics_layout.addWidget(self.speed_label)
        metrics_layout.addStretch()
        layout.addLayout(metrics_layout)

        # Success/failure counters row
        counters_layout = QHBoxLayout()
        self.success_label = QLabel('✓ Success: 0')
        self.success_label.setStyleSheet('color: #10B981; font-weight: bold;')
        self.failure_label = QLabel('✗ Failed: 0')
        self.failure_label.setStyleSheet('color: #EF4444; font-weight: bold;')

        counters_layout.addWidget(self.success_label)
        counters_layout.addWidget(self.failure_label)
        counters_layout.addStretch()
        layout.addLayout(counters_layout)

        # Log output section
        log_label = QLabel('Log Output:')
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)

        # Buttons row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # Set main layout
        self.setLayout(layout)

    def update_progress(
        self,
        percentage: int,
        current_file: str,
        success_count: int,
        failure_count: int
    ):
        """
        Update progress dialog with new values.

        This method is called by the JobWorker via signal connection to update
        the UI with real-time progress information.

        Args:
            percentage: Overall completion percentage (0-100)
            current_file: Path of file currently being processed
            success_count: Number of successfully processed files
            failure_count: Number of failed files
        """
        # Update progress bar
        self.progress_bar.setValue(percentage)

        # Update current file (truncate if too long)
        file_display = current_file
        if len(file_display) > 80:
            file_display = '...' + file_display[-77:]
        self.current_file_label.setText(f'Current: {file_display}')

        # Update success/failure counters
        self.success_label.setText(f'✓ Success: {success_count}')
        self.failure_label.setText(f'✗ Failed: {failure_count}')

        # Calculate and update time metrics
        elapsed = time.time() - self.start_time
        self.elapsed_label.setText(f'Elapsed: {self._format_time(elapsed)}')

        # Calculate ETA (only if percentage > 0 to avoid division by zero)
        if percentage > 0:
            total_time = elapsed * 100 / percentage
            remaining = total_time - elapsed
            self.remaining_label.setText(f'Remaining: {self._format_time(remaining)}')

            # Calculate processing speed
            files_processed = success_count + failure_count
            if elapsed > 0:
                speed = (files_processed / elapsed) * 60  # files per minute
                self.speed_label.setText(f'Speed: {speed:.1f} files/min')
        else:
            self.remaining_label.setText('Remaining: --:--:--')
            self.speed_label.setText('Speed: -- files/min')

        # Add to log with status icon
        if success_count + failure_count > 0:
            # Choose icon based on latest result (inferred from counts)
            status_icon = '✓'  # Assume success by default
            file_name = current_file.split('/')[-1].split('\\')[-1]  # Get filename only
            self.log_text.append(f'{status_icon} {file_name}')

            # Auto-scroll to bottom
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _format_time(self, seconds: float) -> str:
        """
        Format seconds as HH:MM:SS.

        Args:
            seconds: Time in seconds (may be negative for remaining time calculations)

        Returns:
            Formatted time string in HH:MM:SS format
        """
        # Handle negative values (shouldn't happen, but be safe)
        if seconds < 0:
            seconds = 0

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        return f'{hours:02d}:{minutes:02d}:{secs:02d}'

    def _on_cancel(self):
        """
        Handle cancel button click.

        Disables the button and emits the cancelled signal to notify
        the JobWorker to stop processing.
        """
        # Disable button to prevent double-clicks
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText('Cancelling...')

        # Emit cancellation signal
        self.cancelled.emit()

        # Update UI to show cancellation in progress
        self.operation_label.setText('Operation: Cancelling...')
