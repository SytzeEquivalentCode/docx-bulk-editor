"""
GUI tests for HistoryWindow using pytest-qt.

Tests cover:
- Window initialization and table structure
- Job listing from database
- Filtering by operation and status
- Job detail viewing
- CSV export functionality
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from src.ui.history_window import HistoryWindow


def create_test_job(db_manager, operation='search_replace', status='completed',
                   total_files=10, successful_files=8, failed_files=2,
                   duration_seconds=30.5):
    """Helper to create a job record in the database."""
    job_id = db_manager.generate_id()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO jobs (id, created_at, operation, config, status,
               total_files, successful_files, failed_files, total_changes,
               duration_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (job_id, datetime.now(timezone.utc).isoformat(), operation,
             '{}', status, total_files, successful_files, failed_files,
             0, duration_seconds)
        )
        conn.commit()
    return job_id


@pytest.mark.gui
class TestHistoryWindowInitialization:
    """Test HistoryWindow initialization and structure."""

    def test_window_creates_with_correct_structure(self, qtbot, test_db):
        """Test window has expected widgets."""
        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # Table structure
        assert window.jobs_table.columnCount() == 7
        headers = [window.jobs_table.horizontalHeaderItem(i).text()
                   for i in range(7)]
        assert 'Operation' in headers
        assert 'Status' in headers
        assert 'Date/Time' in headers
        assert 'Files' in headers

        # Filter combos exist
        assert window.operation_filter is not None
        assert window.status_filter is not None

    def test_empty_database_shows_no_rows(self, qtbot, test_db):
        """Test empty database shows empty table."""
        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        assert window.jobs_table.rowCount() == 0

    def test_filter_combos_have_correct_options(self, qtbot, test_db):
        """Test filter combos contain expected options."""
        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # Operation filter (6 options: All + 5 operations)
        assert window.operation_filter.count() == 6
        assert window.operation_filter.itemText(0) == 'All Operations'
        assert 'search_replace' in [window.operation_filter.itemText(i)
                                     for i in range(window.operation_filter.count())]
        assert 'metadata' in [window.operation_filter.itemText(i)
                              for i in range(window.operation_filter.count())]

        # Status filter (6 options: All + 5 statuses)
        assert window.status_filter.count() == 6
        assert window.status_filter.itemText(0) == 'All Statuses'
        assert 'completed' in [window.status_filter.itemText(i)
                               for i in range(window.status_filter.count())]
        assert 'failed' in [window.status_filter.itemText(i)
                            for i in range(window.status_filter.count())]


@pytest.mark.gui
class TestHistoryWindowJobListing:
    """Test job listing in table."""

    def test_single_job_appears_in_table(self, qtbot, test_db):
        """Test single job shows in table."""
        create_test_job(test_db)

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        assert window.jobs_table.rowCount() == 1

    def test_multiple_jobs_appear_in_table(self, qtbot, test_db):
        """Test multiple jobs show in table."""
        create_test_job(test_db, operation='search_replace')
        create_test_job(test_db, operation='metadata')
        create_test_job(test_db, operation='validate')

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        assert window.jobs_table.rowCount() == 3

    def test_job_columns_display_correct_data(self, qtbot, test_db):
        """Test job data displays correctly in columns."""
        create_test_job(
            test_db,
            operation='metadata',
            status='completed',
            total_files=5,
            successful_files=4,
            failed_files=1
        )

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # Column 1 = Operation (search_replace -> Search & Replace)
        operation_text = window.jobs_table.item(0, 1).text()
        assert operation_text == 'Metadata'

        # Column 2 = Files
        assert window.jobs_table.item(0, 2).text() == '5'

        # Column 3 = Success
        assert window.jobs_table.item(0, 3).text() == '4'

        # Column 4 = Failed
        assert window.jobs_table.item(0, 4).text() == '1'

    def test_jobs_ordered_by_date_descending(self, qtbot, test_db):
        """Test jobs appear with newest first."""
        # Create jobs with different dates
        import time

        # Oldest job
        job1_id = create_test_job(test_db, operation='validate')
        time.sleep(0.1)

        # Middle job
        job2_id = create_test_job(test_db, operation='metadata')
        time.sleep(0.1)

        # Newest job
        job3_id = create_test_job(test_db, operation='search_replace')

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # First row should be search_replace (newest)
        first_op = window.jobs_table.item(0, 1).text()
        assert 'Search' in first_op or 'Replace' in first_op

        # Last row should be validate (oldest)
        last_op = window.jobs_table.item(2, 1).text()
        assert 'Validate' in last_op


@pytest.mark.gui
class TestHistoryWindowFiltering:
    """Test filtering functionality."""

    def test_filter_by_operation_shows_matching_jobs(self, qtbot, test_db):
        """Test operation filter shows only matching jobs."""
        create_test_job(test_db, operation='search_replace')
        create_test_job(test_db, operation='metadata')
        create_test_job(test_db, operation='search_replace')

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # Initially shows all 3
        assert window.jobs_table.rowCount() == 3

        # Filter by search_replace
        window.operation_filter.setCurrentText('search_replace')

        # Wait for filter to apply
        qtbot.waitUntil(lambda: window.jobs_table.rowCount() == 2, timeout=1000)

        assert window.jobs_table.rowCount() == 2

    def test_filter_by_status_shows_matching_jobs(self, qtbot, test_db):
        """Test status filter shows only matching jobs."""
        create_test_job(test_db, status='completed')
        create_test_job(test_db, status='failed')
        create_test_job(test_db, status='completed')

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # Filter by failed
        window.status_filter.setCurrentText('failed')

        qtbot.waitUntil(lambda: window.jobs_table.rowCount() == 1, timeout=1000)

        assert window.jobs_table.rowCount() == 1

    def test_combined_filters_intersect(self, qtbot, test_db):
        """Test combining operation and status filters."""
        create_test_job(test_db, operation='search_replace', status='completed')
        create_test_job(test_db, operation='search_replace', status='failed')
        create_test_job(test_db, operation='metadata', status='completed')

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # Filter by operation AND status
        window.operation_filter.setCurrentText('search_replace')
        qtbot.waitUntil(lambda: window.jobs_table.rowCount() == 2, timeout=1000)

        window.status_filter.setCurrentText('failed')
        qtbot.waitUntil(lambda: window.jobs_table.rowCount() == 1, timeout=1000)

        assert window.jobs_table.rowCount() == 1

    def test_filter_all_operations_shows_all(self, qtbot, test_db):
        """Test 'All Operations' filter shows all jobs."""
        create_test_job(test_db, operation='search_replace')
        create_test_job(test_db, operation='metadata')

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # Filter by specific operation first
        window.operation_filter.setCurrentText('metadata')
        qtbot.waitUntil(lambda: window.jobs_table.rowCount() == 1, timeout=1000)

        # Reset to All Operations
        window.operation_filter.setCurrentText('All Operations')
        qtbot.waitUntil(lambda: window.jobs_table.rowCount() == 2, timeout=1000)

        assert window.jobs_table.rowCount() == 2

    def test_filter_change_clears_details(self, qtbot, test_db):
        """Test changing filter clears detail panel."""
        create_test_job(test_db, operation='search_replace')
        create_test_job(test_db, operation='metadata')

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # Select a job to populate details
        window.jobs_table.selectRow(0)
        qtbot.waitUntil(
            lambda: len(window.details_text.toPlainText()) > 0,
            timeout=1000
        )

        # Change filter - should clear details
        window.operation_filter.setCurrentText('metadata')

        # Details should be cleared
        assert window.details_text.toPlainText() == ''


@pytest.mark.gui
class TestHistoryWindowDetails:
    """Test job detail viewing."""

    def test_selecting_job_shows_details(self, qtbot, test_db):
        """Test selecting job row shows details."""
        job_id = create_test_job(test_db, operation='validate')

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # Initially no details
        assert window.details_text.toPlainText() == ''

        # Select first row
        window.jobs_table.selectRow(0)

        # Wait for details to load
        qtbot.waitUntil(
            lambda: len(window.details_text.toPlainText()) > 0,
            timeout=1000
        )

        details = window.details_text.toPlainText().lower()
        assert 'validate' in details or 'validation' in details

    def test_details_show_job_summary(self, qtbot, test_db):
        """Test details contain job summary information."""
        create_test_job(
            test_db,
            operation='search_replace',
            status='completed',
            total_files=10,
            successful_files=8,
            failed_files=2
        )

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        window.jobs_table.selectRow(0)
        qtbot.waitUntil(
            lambda: len(window.details_text.toPlainText()) > 0,
            timeout=1000
        )

        details = window.details_text.toPlainText().lower()

        # Check for summary fields
        assert 'status' in details
        assert 'completed' in details
        assert 'total files' in details
        assert '10' in details
        assert 'successful' in details
        assert '8' in details
        assert 'failed' in details
        assert '2' in details

    def test_details_show_configuration(self, qtbot, test_db):
        """Test details contain configuration section."""
        create_test_job(test_db)

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        window.jobs_table.selectRow(0)
        qtbot.waitUntil(
            lambda: len(window.details_text.toPlainText()) > 0,
            timeout=1000
        )

        details = window.details_text.toPlainText().lower()
        assert 'configuration' in details

    def test_no_selection_shows_placeholder(self, qtbot, test_db):
        """Test placeholder text when no job selected."""
        create_test_job(test_db)

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # No selection yet
        placeholder = window.details_text.placeholderText()
        assert 'Select a job' in placeholder or 'select' in placeholder.lower()


@pytest.mark.gui
class TestHistoryWindowExport:
    """Test CSV export functionality."""

    def test_export_creates_csv_file(self, qtbot, test_db, tmp_path, monkeypatch):
        """Test export creates valid CSV file."""
        create_test_job(test_db, operation='search_replace')
        create_test_job(test_db, operation='metadata')

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        export_path = tmp_path / "export.csv"

        # Mock file dialog
        monkeypatch.setattr(
            QFileDialog, 'getSaveFileName',
            lambda *args, **kwargs: (str(export_path), 'CSV Files (*.csv)')
        )

        # Mock success message
        monkeypatch.setattr(QMessageBox, 'information', lambda *args: None)

        window._on_export()

        assert export_path.exists()

        # Verify content
        content = export_path.read_text(encoding='utf-8')
        assert 'search_replace' in content
        assert 'metadata' in content

    def test_export_includes_all_columns(self, qtbot, test_db, tmp_path, monkeypatch):
        """Test CSV header has all expected columns."""
        create_test_job(test_db)

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        export_path = tmp_path / "export.csv"

        monkeypatch.setattr(
            QFileDialog, 'getSaveFileName',
            lambda *args, **kwargs: (str(export_path), 'CSV Files (*.csv)')
        )
        monkeypatch.setattr(QMessageBox, 'information', lambda *args: None)

        window._on_export()

        # Read CSV header
        with open(export_path, 'r', encoding='utf-8') as f:
            header = f.readline()

        # Check for key columns
        assert 'ID' in header
        assert 'Operation' in header
        assert 'Status' in header
        assert 'Total Files' in header
        assert 'Successful' in header
        assert 'Failed' in header
        assert 'Duration' in header

    def test_export_cancelled_does_nothing(self, qtbot, test_db, tmp_path, monkeypatch):
        """Test cancelling export doesn't create file."""
        create_test_job(test_db)

        window = HistoryWindow(test_db)
        qtbot.addWidget(window)

        # Mock dialog to return empty string (user cancelled)
        monkeypatch.setattr(
            QFileDialog, 'getSaveFileName',
            lambda *args, **kwargs: ('', '')
        )

        window._on_export()

        # No files should be created in tmp_path
        csv_files = list(tmp_path.glob('*.csv'))
        assert len(csv_files) == 0
