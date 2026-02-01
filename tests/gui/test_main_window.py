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
from PySide6.QtWidgets import QMessageBox, QFileDialog
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


# ============================================================================
# TestMainWindowFileSelection - GUI-01 File Selection Tests
# ============================================================================

@pytest.mark.gui
class TestMainWindowFileSelection:
    """Tests for file selection dialogs, folder scanning, and file list management."""

    def test_add_files_via_dialog(self, qtbot, test_config, test_db, docx_factory, monkeypatch):
        """Test adding files via QFileDialog.getOpenFileNames."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Create test files
        test_files = [
            docx_factory(content="Test 1", filename="test1.docx"),
            docx_factory(content="Test 2", filename="test2.docx")
        ]

        # Mock file dialog to return test files (non-blocking)
        monkeypatch.setattr(
            QFileDialog, 'getOpenFileNames',
            lambda *args, **kwargs: ([str(f) for f in test_files], '')
        )

        # Trigger file dialog
        window._on_add_files()

        # Verify files added
        assert len(window.selected_files) == 2
        assert window.file_list.count() == 2
        assert window.start_button.isEnabled() is True

    def test_add_folder_via_dialog(self, qtbot, test_config, test_db, docx_factory, tmp_path, monkeypatch):
        """Test adding folder via QFileDialog.getExistingDirectory with recursive scan."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Create temp folder with .docx files
        test_folder = tmp_path / "test_docs"
        test_folder.mkdir()
        subfolder = test_folder / "subfolder"
        subfolder.mkdir()

        # Create test files at different levels
        file1 = docx_factory(content="Test 1", filename="file1.docx")
        file2 = docx_factory(content="Test 2", filename="file2.docx")

        # Move files to test folder structure
        import shutil
        dest1 = test_folder / "file1.docx"
        dest2 = subfolder / "file2.docx"
        shutil.copy(str(file1), str(dest1))
        shutil.copy(str(file2), str(dest2))

        # Mock folder dialog to return test folder
        monkeypatch.setattr(
            QFileDialog, 'getExistingDirectory',
            lambda *args, **kwargs: str(test_folder)
        )

        # Trigger folder dialog
        window._on_add_folder()

        # Verify files added (recursive scan should find both)
        assert len(window.selected_files) == 2
        assert window.file_list.count() == 2
        assert window.start_button.isEnabled() is True

    def test_clear_files_button(self, qtbot, test_config, test_db, docx_factory):
        """Test clear files button empties selection and disables start button."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Add files first
        test_files = [docx_factory(content="Test", filename="test.docx")]
        window.selected_files = test_files
        window._update_ui_state()

        assert len(window.selected_files) == 1
        assert window.start_button.isEnabled() is True

        # Clear files
        window._on_clear_files()

        # Verify cleared
        assert len(window.selected_files) == 0
        assert window.file_list.count() == 0
        assert window.start_button.isEnabled() is False

    def test_duplicate_files_not_added(self, qtbot, test_config, test_db, docx_factory, monkeypatch):
        """Test that adding same file twice only results in one entry."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Create test file
        test_file = docx_factory(content="Test", filename="test.docx")

        # Mock file dialog to return same file twice
        monkeypatch.setattr(
            QFileDialog, 'getOpenFileNames',
            lambda *args, **kwargs: ([str(test_file), str(test_file)], '')
        )

        # Add files (same file twice in dialog)
        window._on_add_files()

        # Should only have one entry (duplicate prevented)
        assert len(window.selected_files) == 1
        assert window.file_list.count() == 1

    def test_file_count_label_updates(self, qtbot, test_config, test_db, docx_factory):
        """Test that file count label shows correct count and size."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Initially empty
        assert '0 files' in window.file_count_label.text()

        # Add files
        test_files = [
            docx_factory(content="Test 1", filename="test1.docx"),
            docx_factory(content="Test 2", filename="test2.docx")
        ]
        window.selected_files = test_files
        window._update_file_count()

        # Verify label updated
        label_text = window.file_count_label.text()
        assert '2 files' in label_text
        assert 'MB' in label_text  # Shows size in MB


# ============================================================================
# TestMainWindowOperationSwitching - GUI-01 Operation Panel Tests
# ============================================================================

@pytest.mark.gui
class TestMainWindowOperationSwitching:
    """Tests for operation button switching and config panel display."""

    def test_validate_operation_shows_config(self, qtbot, test_config, test_db):
        """Test clicking validate button shows validate config panel."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Click validate operation button
        validate_button = window.operation_buttons['validate']
        QTest.mouseClick(validate_button, Qt.LeftButton)

        # Verify validate config panel shown
        assert window.current_operation == 'validate'
        assert hasattr(window, 'validate_heading_check')
        assert hasattr(window, 'validate_empty_check')

    def test_table_format_operation_shows_config(self, qtbot, test_config, test_db):
        """Test clicking table_format button shows table format config panel."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Click table_format operation button
        table_button = window.operation_buttons['table_format']
        QTest.mouseClick(table_button, Qt.LeftButton)

        # Verify table format config panel shown
        assert window.current_operation == 'table_format'
        assert hasattr(window, 'table_borders_check')
        assert hasattr(window, 'table_alignment_combo')

    def test_style_enforce_operation_shows_config(self, qtbot, test_config, test_db):
        """Test clicking style_enforce button shows style config panel."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Click style_enforce operation button
        style_button = window.operation_buttons['style_enforce']
        QTest.mouseClick(style_button, Qt.LeftButton)

        # Verify style config panel shown
        assert window.current_operation == 'style_enforce'
        assert hasattr(window, 'style_font_check')
        assert hasattr(window, 'style_font_name_input')

    def test_operation_buttons_mutually_exclusive(self, qtbot, test_config, test_db):
        """Test that only one operation button can be checked at a time."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Initially search_replace is checked
        assert window.operation_buttons['search_replace'].isChecked() is True
        assert window.operation_buttons['metadata'].isChecked() is False

        # Click metadata button
        QTest.mouseClick(window.operation_buttons['metadata'], Qt.LeftButton)

        # Verify only metadata is checked now
        assert window.operation_buttons['search_replace'].isChecked() is False
        assert window.operation_buttons['metadata'].isChecked() is True
        assert window.operation_buttons['validate'].isChecked() is False

        # Click validate button
        QTest.mouseClick(window.operation_buttons['validate'], Qt.LeftButton)

        # Verify only validate is checked now
        assert window.operation_buttons['search_replace'].isChecked() is False
        assert window.operation_buttons['metadata'].isChecked() is False
        assert window.operation_buttons['validate'].isChecked() is True


# ============================================================================
# TestMainWindowJobValidation - GUI-02 Job Validation Tests
# ============================================================================

@pytest.mark.gui
class TestMainWindowJobValidation:
    """Tests for job validation logic before starting processing."""

    def test_start_without_search_term_shows_warning(self, qtbot, test_config, test_db, docx_factory, monkeypatch):
        """Test that starting search/replace without search term shows warning."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Add file but leave search_input empty
        test_file = docx_factory(content="Test", filename="test.docx")
        window.selected_files = [test_file]
        window._update_ui_state()

        # Ensure search_replace operation selected (default)
        assert window.current_operation == 'search_replace'
        # Search input is empty
        window.search_input.setText("")

        # Mock QMessageBox.warning to capture calls
        warning_calls = []
        def mock_warning(parent, title, message):
            warning_calls.append((title, message))
            return QMessageBox.Ok

        monkeypatch.setattr(QMessageBox, 'warning', mock_warning)

        # Try to start
        window._on_start_clicked()

        # Verify warning shown
        assert len(warning_calls) == 1
        title, message = warning_calls[0]
        assert "Missing Search Term" in title
        assert "search term" in message.lower()

    def test_start_without_metadata_operations_shows_warning(self, qtbot, test_config, test_db, docx_factory, monkeypatch):
        """Test that starting metadata without any operations shows warning."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Add file
        test_file = docx_factory(content="Test", filename="test.docx")
        window.selected_files = [test_file]
        window._update_ui_state()

        # Switch to metadata operation
        QTest.mouseClick(window.operation_buttons['metadata'], Qt.LeftButton)
        assert window.current_operation == 'metadata'

        # Don't check any clear checkboxes or enter any set values
        # (verify all unchecked)
        for checkbox in window.metadata_clear_checks.values():
            assert checkbox.isChecked() is False

        for input_field in window.metadata_set_inputs.values():
            assert input_field.text().strip() == ""

        # Mock QMessageBox.warning
        warning_calls = []
        def mock_warning(parent, title, message):
            warning_calls.append((title, message))
            return QMessageBox.Ok

        monkeypatch.setattr(QMessageBox, 'warning', mock_warning)

        # Try to start
        window._on_start_clicked()

        # Verify warning shown
        assert len(warning_calls) == 1
        title, message = warning_calls[0]
        assert "No Metadata Operations" in title
        assert "at least one" in message.lower()

    def test_start_with_valid_search_term_creates_job(self, qtbot, test_config, test_db, docx_factory, monkeypatch):
        """Test that valid search/replace configuration creates job in database."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Add file and configure search/replace
        test_file = docx_factory(content="Test content", filename="test.docx")
        window.selected_files = [test_file]
        window._update_ui_state()

        window.search_input.setText("Test")
        window.replace_input.setText("Sample")

        # Mock ProgressDialog and worker to avoid actual processing
        mock_progress = MagicMock()
        monkeypatch.setattr('src.ui.main_window.ProgressDialog', lambda parent: mock_progress)

        # Click start
        window._on_start_clicked()

        # Verify job created in database
        with test_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE operation = 'search_replace'")
            job_count = cursor.fetchone()[0]

        assert job_count == 1

        # Verify worker created
        assert window.worker is not None

        # Cleanup
        if window.worker and window.worker.isRunning():
            window.worker.cancel()
            window.worker.wait(5000)

    def test_close_window_stops_running_worker(self, qtbot, test_config, test_db, docx_factory, monkeypatch):
        """Test that closing window cancels running worker thread."""
        window = MainWindow(test_config, test_db)
        qtbot.addWidget(window)

        # Add file and configure
        test_file = docx_factory(content="Test", filename="test.docx")
        window.selected_files = [test_file]
        window._update_ui_state()
        window.search_input.setText("Test")

        # Mock ProgressDialog
        mock_progress = MagicMock()
        monkeypatch.setattr('src.ui.main_window.ProgressDialog', lambda parent: mock_progress)

        # Start job
        window._on_start_clicked()

        # Verify worker running
        assert window.worker is not None
        worker = window.worker

        # Spy on worker.cancel to verify it's called
        cancel_spy = Mock()
        original_cancel = worker.cancel
        worker.cancel = lambda: (cancel_spy(), original_cancel())

        # Close window
        window.close()

        # Verify cancel was called
        cancel_spy.assert_called_once()

        # Wait for worker to finish
        if worker.isRunning():
            worker.wait(5000)
