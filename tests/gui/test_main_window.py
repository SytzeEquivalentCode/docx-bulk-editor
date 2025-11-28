"""
GUI tests for MainWindow using pytest-qt.

Tests cover:
- Window initialization and UI state
- File selection and validation
- Button state management
- User interaction workflows
- Signal/slot connections

NOTE: GUI tests require a display. On CI/CD, use virtual display (Xvfb on Linux).
"""

import pytest
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox
from unittest.mock import Mock, patch, MagicMock

from src.ui.main_window import MainWindow


@pytest.mark.gui
def test_main_window_initialization(qtbot, test_config, test_db):
    """Test that MainWindow initializes with correct default state."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    # Verify initial UI state
    assert window.isVisible() is False  # Not shown until explicitly called
    assert window.start_button.isEnabled() is False  # No files selected yet
    assert window.selected_files == []
    assert window.windowTitle() == 'DOCX Bulk Editor v1.0'
    assert window.current_operation == 'search_replace'


@pytest.mark.gui
def test_file_selection_enables_start_button(qtbot, test_config, test_db, docx_factory):
    """Test that selecting files enables the start button."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)
    window.show()

    # Initially disabled
    assert window.start_button.isEnabled() is False

    # Add files to selection
    test_files = [
        docx_factory(content="Test 1", filename="file1.docx"),
        docx_factory(content="Test 2", filename="file2.docx")
    ]
    window.selected_files = test_files
    window._update_ui_state()

    # Should now be enabled
    assert window.start_button.isEnabled() is True
    assert window.file_list.count() == 2


@pytest.mark.gui
def test_start_button_click_creates_worker(qtbot, test_config, test_db, docx_factory):
    """Test that clicking start button initiates processing."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    # Set up files and configuration
    test_file = docx_factory(content="Test content", filename="test.docx")
    window.selected_files = [test_file]
    window._update_ui_state()

    # Configure search/replace
    window.search_input.setText("Test")
    window.replace_input.setText("Sample")

    # Mock ProgressDialog to avoid display issues
    with patch('src.ui.main_window.ProgressDialog') as mock_progress:
        mock_progress.return_value = MagicMock()

        # Click start button
        QTest.mouseClick(window.start_button, Qt.LeftButton)

        # Verify worker was created
        assert window.worker is not None
        assert window.start_button.isEnabled() is False  # Disabled during processing

        # Cleanup: Stop worker and wait for it to finish
        if window.worker.isRunning():
            window.worker.cancel()
            window.worker.wait(5000)


@pytest.mark.gui
def test_cancel_button_stops_worker(qtbot, test_config, test_db, docx_factory):
    """Test that clicking cancel stops the worker thread."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    # Set up and start job
    test_file = docx_factory(content="Test content", filename="test.docx")
    window.selected_files = [test_file]
    window._update_ui_state()
    window.search_input.setText("Test")
    window.replace_input.setText("Sample")

    # Mock ProgressDialog
    with patch('src.ui.main_window.ProgressDialog') as mock_progress:
        mock_dialog = MagicMock()
        mock_progress.return_value = mock_dialog

        # Start processing
        QTest.mouseClick(window.start_button, Qt.LeftButton)

        # Simulate cancel by calling worker.cancel() directly
        window.progress_dialog = mock_dialog
        window.worker.cancel()

        # Verify worker cancellation
        assert window.worker._cancelled is True

        # Cleanup: Wait for worker to finish
        if window.worker.isRunning():
            window.worker.wait(5000)


@pytest.mark.gui
def test_progress_signal_updates_ui(qtbot, test_config, test_db):
    """Test that progress signals from worker update the UI."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    # Create mock progress dialog
    window.progress_dialog = MagicMock()

    # Manually emit progress signal
    window._on_progress_updated(50, "file.docx", 10, 2)

    # Verify progress dialog updated
    window.progress_dialog.update_progress.assert_called_once_with(50, "file.docx", 10, 2)


@pytest.mark.gui
def test_job_completion_re_enables_ui(qtbot, test_config, test_db, docx_factory):
    """Test that job completion re-enables UI controls."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    # Set up files
    test_file = docx_factory(content="Test", filename="test.docx")
    window.selected_files = [test_file]
    window._update_ui_state()
    window.search_input.setText("Test")
    window.replace_input.setText("Sample")

    # Mock ProgressDialog and QMessageBox
    with patch('src.ui.main_window.ProgressDialog'), \
         patch('src.ui.main_window.QMessageBox'):
        # Start processing (disables UI)
        QTest.mouseClick(window.start_button, Qt.LeftButton)
        assert window.start_button.isEnabled() is False

        # Stop worker before calling completion
        if window.worker and window.worker.isRunning():
            window.worker.cancel()
            window.worker.wait(5000)

        # Complete job
        results = {
            "job_id": 1,
            "status": "completed",
            "success_count": 1,
            "failure_count": 0,
            "total_files": 1,
            "duration_seconds": 1.0
        }
        window._on_job_completed(results)

        # Verify UI re-enabled
        assert window.start_button.isEnabled() is True


@pytest.mark.gui
def test_error_signal_shows_error_dialog(qtbot, test_config, test_db):
    """Test that error signals display error dialog to user."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)

    # Mock QMessageBox
    with patch.object(QMessageBox, 'critical') as mock_msgbox:
        # Emit error signal
        error_message = "Failed to process file.docx"
        window._on_error(error_message)

        # Verify error dialog shown
        mock_msgbox.assert_called_once()
        call_args = mock_msgbox.call_args[0]
        assert error_message in call_args[2]


@pytest.mark.gui
def test_drag_and_drop_file_selection(qtbot, test_config, test_db, docx_factory, tmp_path):
    """Test that drag-and-drop adds files to selection."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)
    window.show()

    # Create test files
    test_files = [
        docx_factory(content="Test 1", filename="file1.docx"),
        docx_factory(content="Test 2", filename="file2.docx")
    ]

    # Simulate drag-and-drop
    from PySide6.QtCore import QMimeData, QUrl, QPoint
    from PySide6.QtGui import QDragEnterEvent, QDropEvent

    mime_data = QMimeData()
    urls = [QUrl.fromLocalFile(str(f)) for f in test_files]
    mime_data.setUrls(urls)

    # Simulate drag enter
    drag_enter_event = QDragEnterEvent(
        QPoint(10, 10),
        Qt.CopyAction,
        mime_data,
        Qt.LeftButton,
        Qt.NoModifier
    )
    window.dragEnterEvent(drag_enter_event)
    assert drag_enter_event.isAccepted()

    # Simulate drop
    drop_event = QDropEvent(
        QPoint(10, 10),
        Qt.CopyAction,
        mime_data,
        Qt.LeftButton,
        Qt.NoModifier
    )
    window.dropEvent(drop_event)

    # Verify files added
    assert len(window.selected_files) == 2
    assert window.start_button.isEnabled() is True


@pytest.mark.gui
def test_operation_selector_changes_config_panel(qtbot, test_config, test_db):
    """Test that selecting different operations changes the configuration panel."""
    window = MainWindow(test_config, test_db)
    qtbot.addWidget(window)
    window.show()

    # Initially shows search_replace panel
    assert window.current_operation == 'search_replace'
    assert hasattr(window, 'search_input')

    # Click metadata operation button
    metadata_button = window.operation_buttons['metadata']
    QTest.mouseClick(metadata_button, Qt.LeftButton)

    # Verify panel changed
    assert window.current_operation == 'metadata'
    # Old widgets should be cleaned up
    assert not hasattr(window, 'search_input')
