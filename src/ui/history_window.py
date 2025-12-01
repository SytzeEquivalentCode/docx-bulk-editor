"""
Job History window for DOCX Bulk Editor.

Displays past processing jobs with filtering, details view, and export capability.
"""

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QGroupBox, QTextEdit,
    QHeaderView, QMessageBox, QFileDialog, QSplitter
)
from PySide6.QtCore import Qt

from src.database.db_manager import DatabaseManager
from src.core.logger import setup_logger

logger = setup_logger()


class HistoryWindow(QDialog):
    """
    Job history window with filtering and details view.

    Shows all past jobs in a table with the ability to:
    - Filter by operation type or status
    - View detailed job results
    - Export results to CSV
    """

    def __init__(self, db_manager: DatabaseManager, parent=None):
        """
        Initialize history window.

        Args:
            db_manager: DatabaseManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self._init_ui()
        self._load_jobs()

    def _init_ui(self):
        """Initialize user interface components."""
        self.setWindowTitle('Job History')
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)

        layout = QVBoxLayout(self)

        # Filter row
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel('Operation:'))
        self.operation_filter = QComboBox()
        self.operation_filter.addItems([
            'All Operations',
            'search_replace',
            'metadata',
            'table_format',
            'style_enforce',
            'validate'
        ])
        self.operation_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.operation_filter)

        filter_layout.addSpacing(20)

        filter_layout.addWidget(QLabel('Status:'))
        self.status_filter = QComboBox()
        self.status_filter.addItems([
            'All Statuses',
            'completed',
            'failed',
            'cancelled',
            'running',
            'pending'
        ])
        self.status_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addStretch()

        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self._load_jobs)
        filter_layout.addWidget(refresh_btn)

        layout.addLayout(filter_layout)

        # Splitter for jobs table and details
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Jobs table
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(7)
        self.jobs_table.setHorizontalHeaderLabels([
            'Date/Time', 'Operation', 'Files', 'Success', 'Failed', 'Duration', 'Status'
        ])
        self.jobs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.jobs_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.jobs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.jobs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.jobs_table.selectionModel().selectionChanged.connect(self._on_job_selected)
        splitter.addWidget(self.jobs_table)

        # Details panel
        details_group = QGroupBox('Job Details')
        details_layout = QVBoxLayout(details_group)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText('Select a job to view details...')
        details_layout.addWidget(self.details_text)

        splitter.addWidget(details_group)

        # Set initial splitter sizes (70% table, 30% details)
        splitter.setSizes([400, 200])
        layout.addWidget(splitter)

        # Button row
        button_layout = QHBoxLayout()

        export_btn = QPushButton('Export to CSV')
        export_btn.clicked.connect(self._on_export)
        button_layout.addWidget(export_btn)

        button_layout.addStretch()

        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _load_jobs(self):
        """Load jobs from database with current filters."""
        self.jobs_table.setRowCount(0)

        # Build query with filters
        query = "SELECT * FROM jobs"
        conditions = []
        params = []

        op_filter = self.operation_filter.currentText()
        if op_filter != 'All Operations':
            conditions.append("operation = ?")
            params.append(op_filter)

        status_filter = self.status_filter.currentText()
        if status_filter != 'All Statuses':
            conditions.append("status = ?")
            params.append(status_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT 100"

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                jobs = cursor.fetchall()

                self.jobs_table.setRowCount(len(jobs))
                self._job_ids = []  # Store job IDs for later lookup

                for row_idx, job in enumerate(jobs):
                    self._job_ids.append(job['id'])

                    # Date/Time
                    created = job['created_at']
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d %H:%M')
                    except (ValueError, AttributeError):
                        date_str = str(created)[:16] if created else 'N/A'
                    self.jobs_table.setItem(row_idx, 0, QTableWidgetItem(date_str))

                    # Operation
                    op_display = {
                        'search_replace': 'Search & Replace',
                        'metadata': 'Metadata',
                        'table_format': 'Table Format',
                        'style_enforce': 'Style Enforce',
                        'validate': 'Validate'
                    }.get(job['operation'], job['operation'])
                    self.jobs_table.setItem(row_idx, 1, QTableWidgetItem(op_display))

                    # Files
                    self.jobs_table.setItem(
                        row_idx, 2,
                        QTableWidgetItem(str(job['total_files'] or 0))
                    )

                    # Success
                    success_item = QTableWidgetItem(str(job['successful_files'] or 0))
                    success_item.setForeground(Qt.GlobalColor.darkGreen)
                    self.jobs_table.setItem(row_idx, 3, success_item)

                    # Failed
                    failed_count = job['failed_files'] or 0
                    failed_item = QTableWidgetItem(str(failed_count))
                    if failed_count > 0:
                        failed_item.setForeground(Qt.GlobalColor.red)
                    self.jobs_table.setItem(row_idx, 4, failed_item)

                    # Duration
                    duration = job['duration_seconds'] or 0
                    if duration >= 60:
                        duration_str = f"{duration / 60:.1f}m"
                    else:
                        duration_str = f"{duration:.1f}s"
                    self.jobs_table.setItem(row_idx, 5, QTableWidgetItem(duration_str))

                    # Status
                    status = job['status'] or 'unknown'
                    status_item = QTableWidgetItem(status.title())
                    if status == 'completed':
                        status_item.setForeground(Qt.GlobalColor.darkGreen)
                    elif status == 'failed':
                        status_item.setForeground(Qt.GlobalColor.red)
                    elif status == 'cancelled':
                        status_item.setForeground(Qt.GlobalColor.darkYellow)
                    self.jobs_table.setItem(row_idx, 6, status_item)

            logger.debug(f"Loaded {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"Failed to load jobs: {e}", exc_info=True)
            QMessageBox.warning(self, 'Error', f'Failed to load job history: {e}')

    def _on_filter_changed(self):
        """Handle filter change."""
        self._load_jobs()
        self.details_text.clear()

    def _on_job_selected(self):
        """Handle job selection - load and display details."""
        selected_rows = self.jobs_table.selectedIndexes()
        if not selected_rows:
            return

        row_idx = selected_rows[0].row()
        if row_idx >= len(self._job_ids):
            return

        job_id = self._job_ids[row_idx]
        self._load_job_details(job_id)

    def _load_job_details(self, job_id: str):
        """Load and display job details."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Get job info
                cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
                job = cursor.fetchone()

                if not job:
                    self.details_text.setText("Job not found")
                    return

                # Get job results
                cursor.execute(
                    "SELECT * FROM job_results WHERE job_id = ? ORDER BY created_at",
                    (job_id,)
                )
                results = cursor.fetchall()

                # Build details text
                details = []
                details.append(f"<h3>Job: {job['operation'].replace('_', ' ').title()}</h3>")

                # Job summary
                details.append("<p><b>Summary:</b></p>")
                details.append("<ul>")
                details.append(f"<li>Status: {job['status']}</li>")
                details.append(f"<li>Total files: {job['total_files']}</li>")
                details.append(f"<li>Successful: {job['successful_files']}</li>")
                details.append(f"<li>Failed: {job['failed_files']}</li>")
                details.append(f"<li>Total changes: {job['total_changes']}</li>")

                duration = job['duration_seconds'] or 0
                details.append(f"<li>Duration: {duration:.1f} seconds</li>")
                details.append("</ul>")

                # Configuration
                details.append("<p><b>Configuration:</b></p>")
                details.append(f"<pre>{job['config']}</pre>")

                # File results
                if results:
                    details.append(f"<p><b>File Results ({len(results)} files):</b></p>")
                    details.append("<table border='1' cellpadding='4' style='border-collapse: collapse;'>")
                    details.append("<tr><th>File</th><th>Status</th><th>Changes</th><th>Error</th></tr>")

                    for result in results[:50]:  # Limit to 50 files
                        file_name = Path(result['file_path']).name
                        status = result['status']
                        changes = result['changes_made'] or 0
                        error = result['error_message'] or ''

                        status_color = 'green' if status == 'success' else 'red'
                        details.append(
                            f"<tr>"
                            f"<td>{file_name}</td>"
                            f"<td style='color: {status_color}'>{status}</td>"
                            f"<td>{changes}</td>"
                            f"<td>{error[:50]}{'...' if len(error) > 50 else ''}</td>"
                            f"</tr>"
                        )

                    details.append("</table>")

                    if len(results) > 50:
                        details.append(f"<p><i>... and {len(results) - 50} more files</i></p>")

                self.details_text.setHtml('\n'.join(details))

        except Exception as e:
            logger.error(f"Failed to load job details: {e}", exc_info=True)
            self.details_text.setText(f"Error loading details: {e}")

    def _on_export(self):
        """Export job history to CSV."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            'Export to CSV',
            'job_history.csv',
            'CSV Files (*.csv)'
        )

        if not file_path:
            return

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC"
                )
                jobs = cursor.fetchall()

            # Write CSV with UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                import csv
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    'ID', 'Created At', 'Operation', 'Status',
                    'Total Files', 'Successful', 'Failed',
                    'Total Changes', 'Duration (s)', 'Error Message'
                ])

                # Data rows
                for job in jobs:
                    writer.writerow([
                        job['id'],
                        job['created_at'],
                        job['operation'],
                        job['status'],
                        job['total_files'],
                        job['successful_files'],
                        job['failed_files'],
                        job['total_changes'],
                        job['duration_seconds'],
                        job['error_message'] or ''
                    ])

            QMessageBox.information(
                self,
                'Export Complete',
                f'Exported {len(jobs)} jobs to:\n{file_path}'
            )
            logger.info(f"Exported {len(jobs)} jobs to {file_path}")

        except Exception as e:
            logger.error(f"Failed to export: {e}", exc_info=True)
            QMessageBox.critical(self, 'Export Error', f'Failed to export: {e}')
