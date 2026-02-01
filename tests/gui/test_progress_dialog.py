"""
GUI tests for ProgressDialog using pytest-qt.

Tests cover:
- Dialog initialization and default state
- Progress updates (bar, labels, counters)
- Time formatting and ETA calculation
- Cancellation signal and button state
"""

import pytest
import time
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from src.ui.progress_dialog import ProgressDialog


@pytest.mark.gui
class TestProgressDialogInitialization:
    """Test ProgressDialog initialization state."""

    def test_dialog_creates_with_default_state(self, qtbot):
        """Test default widget values on creation."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        assert dialog.progress_bar.value() == 0
        assert dialog.current_file_label.text() == 'Current: -'
        assert 'Success: 0' in dialog.success_label.text()
        assert 'Failed: 0' in dialog.failure_label.text()

    def test_dialog_is_modal(self, qtbot):
        """Test dialog is modal (blocks parent interaction)."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        assert dialog.isModal() is True
        assert dialog.minimumWidth() >= 600
        assert dialog.minimumHeight() >= 400

    def test_cancel_button_enabled_initially(self, qtbot):
        """Test cancel button is clickable on start."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        assert dialog.cancel_button.isEnabled() is True
        assert dialog.cancel_button.text() == 'Cancel'


@pytest.mark.gui
class TestProgressDialogUpdates:
    """Test ProgressDialog progress update mechanism."""

    def test_update_progress_sets_bar_value(self, qtbot):
        """Test progress bar value updates correctly."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        dialog.update_progress(50, "test.docx", 5, 2)

        assert dialog.progress_bar.value() == 50

    def test_update_progress_truncates_long_filename(self, qtbot):
        """Test long filenames are truncated with ellipsis."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        long_filename = "x" * 100  # 100 characters
        dialog.update_progress(25, long_filename, 1, 0)

        # Should start with "..." and be <= 80 chars
        assert dialog.current_file_label.text().startswith('Current: ...')
        assert len(dialog.current_file_label.text()) <= 90  # "Current: " + 80 chars

    def test_update_progress_updates_success_counter(self, qtbot):
        """Test success counter displays correct count."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        dialog.update_progress(60, "file.docx", 15, 3)

        assert 'Success: 15' in dialog.success_label.text()

    def test_update_progress_updates_failure_counter(self, qtbot):
        """Test failure counter displays correct count."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        dialog.update_progress(60, "file.docx", 15, 3)

        assert 'Failed: 3' in dialog.failure_label.text()

    def test_update_progress_appends_to_log(self, qtbot):
        """Test log output contains processed filename."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        # Process first file (count goes from 0 to 1)
        dialog.update_progress(10, "C:/path/to/test.docx", 1, 0)

        log_content = dialog.log_text.toPlainText()
        assert "test.docx" in log_content
