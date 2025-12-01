"""
Settings dialog for DOCX Bulk Editor.

Provides a tabbed interface for configuring:
- Backup settings (directory, retention, auto-cleanup)
- Processing settings (pool size, timeout, file size limits)
- UI settings (theme, window position, tooltips)
- Logging settings (level, retention)
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QPushButton, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox
)
from PySide6.QtCore import Qt

from src.core.config import ConfigManager
from src.core.logger import setup_logger

logger = setup_logger()


class SettingsDialog(QDialog):
    """
    Settings dialog with tabbed interface.

    Allows users to modify application settings with immediate validation
    and optional apply/cancel workflow.
    """

    def __init__(self, config: ConfigManager, parent=None):
        """
        Initialize settings dialog.

        Args:
            config: ConfigManager instance for reading/writing settings
            parent: Parent widget
        """
        super().__init__(parent)
        self.config = config
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """Initialize user interface components."""
        self.setWindowTitle('Settings')
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Add tabs
        self.tabs.addTab(self._create_backup_tab(), 'Backup')
        self.tabs.addTab(self._create_processing_tab(), 'Processing')
        self.tabs.addTab(self._create_ui_tab(), 'Interface')
        self.tabs.addTab(self._create_logging_tab(), 'Logging')

        # Button row
        button_layout = QHBoxLayout()

        reset_btn = QPushButton('Reset to Defaults')
        reset_btn.clicked.connect(self._on_reset_defaults)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton('Save')
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_backup_tab(self) -> QWidget:
        """Create backup settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Backup directory
        dir_group = QGroupBox('Backup Location')
        dir_layout = QHBoxLayout(dir_group)

        self.backup_dir_input = QLineEdit()
        self.backup_dir_input.setPlaceholderText('Backup directory path...')
        dir_layout.addWidget(self.backup_dir_input)

        browse_btn = QPushButton('Browse...')
        browse_btn.clicked.connect(self._on_browse_backup_dir)
        dir_layout.addWidget(browse_btn)

        layout.addWidget(dir_group)

        # Retention settings
        retention_group = QGroupBox('Retention')
        retention_layout = QFormLayout(retention_group)

        self.retention_days_spin = QSpinBox()
        self.retention_days_spin.setRange(1, 365)
        self.retention_days_spin.setSuffix(' days')
        retention_layout.addRow('Keep backups for:', self.retention_days_spin)

        self.auto_cleanup_check = QCheckBox('Automatically delete old backups')
        retention_layout.addRow(self.auto_cleanup_check)

        self.compress_check = QCheckBox('Compress backups (saves space)')
        retention_layout.addRow(self.compress_check)

        layout.addWidget(retention_group)
        layout.addStretch()

        return tab

    def _create_processing_tab(self) -> QWidget:
        """Create processing settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Performance settings
        perf_group = QGroupBox('Performance')
        perf_layout = QFormLayout(perf_group)

        self.pool_size_spin = QSpinBox()
        self.pool_size_spin.setRange(0, 32)
        self.pool_size_spin.setSpecialValueText('Auto (CPU count - 1)')
        perf_layout.addRow('Worker processes:', self.pool_size_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 600)
        self.timeout_spin.setSuffix(' seconds')
        perf_layout.addRow('Timeout per file:', self.timeout_spin)

        layout.addWidget(perf_group)

        # File handling
        file_group = QGroupBox('File Handling')
        file_layout = QFormLayout(file_group)

        self.max_file_size_spin = QSpinBox()
        self.max_file_size_spin.setRange(1, 1000)
        self.max_file_size_spin.setSuffix(' MB')
        file_layout.addRow('Max file size:', self.max_file_size_spin)

        self.warn_large_files_check = QCheckBox('Warn when files exceed limit')
        file_layout.addRow(self.warn_large_files_check)

        self.skip_locked_check = QCheckBox('Skip locked files automatically')
        file_layout.addRow(self.skip_locked_check)

        layout.addWidget(file_group)
        layout.addStretch()

        return tab

    def _create_ui_tab(self) -> QWidget:
        """Create UI settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Appearance
        appearance_group = QGroupBox('Appearance')
        appearance_layout = QFormLayout(appearance_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['system', 'light', 'dark'])
        appearance_layout.addRow('Theme:', self.theme_combo)

        layout.addWidget(appearance_group)

        # Behavior
        behavior_group = QGroupBox('Behavior')
        behavior_layout = QFormLayout(behavior_group)

        self.remember_position_check = QCheckBox('Remember window position')
        behavior_layout.addRow(self.remember_position_check)

        self.show_tooltips_check = QCheckBox('Show tooltips')
        behavior_layout.addRow(self.show_tooltips_check)

        self.progress_interval_spin = QSpinBox()
        self.progress_interval_spin.setRange(50, 1000)
        self.progress_interval_spin.setSuffix(' ms')
        behavior_layout.addRow('Progress update interval:', self.progress_interval_spin)

        layout.addWidget(behavior_group)
        layout.addStretch()

        return tab

    def _create_logging_tab(self) -> QWidget:
        """Create logging settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        log_group = QGroupBox('Log Settings')
        log_layout = QFormLayout(log_group)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        log_layout.addRow('Log level:', self.log_level_combo)

        self.log_retention_spin = QSpinBox()
        self.log_retention_spin.setRange(1, 365)
        self.log_retention_spin.setSuffix(' days')
        log_layout.addRow('Keep logs for:', self.log_retention_spin)

        self.log_max_size_spin = QSpinBox()
        self.log_max_size_spin.setRange(1, 100)
        self.log_max_size_spin.setSuffix(' MB')
        log_layout.addRow('Max log file size:', self.log_max_size_spin)

        self.log_max_files_spin = QSpinBox()
        self.log_max_files_spin.setRange(1, 50)
        self.log_max_files_spin.setSuffix(' files')
        log_layout.addRow('Max log files:', self.log_max_files_spin)

        layout.addWidget(log_group)
        layout.addStretch()

        return tab

    def _load_settings(self):
        """Load current settings into UI widgets."""
        # Backup settings
        self.backup_dir_input.setText(
            self.config.get('backup.directory', './backups')
        )
        self.retention_days_spin.setValue(
            self.config.get('backup.retention_days', 7)
        )
        self.auto_cleanup_check.setChecked(
            self.config.get('backup.auto_cleanup', True)
        )
        self.compress_check.setChecked(
            self.config.get('backup.compress', False)
        )

        # Processing settings
        pool_size = self.config.get('processing.pool_size')
        self.pool_size_spin.setValue(pool_size if pool_size else 0)
        self.timeout_spin.setValue(
            self.config.get('processing.timeout_per_file_seconds', 60)
        )
        self.max_file_size_spin.setValue(
            self.config.get('processing.max_file_size_mb', 100)
        )
        self.warn_large_files_check.setChecked(
            self.config.get('processing.warn_large_files', True)
        )
        self.skip_locked_check.setChecked(
            self.config.get('processing.skip_locked_files', True)
        )

        # UI settings
        theme = self.config.get('ui.theme', 'system')
        index = self.theme_combo.findText(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        self.remember_position_check.setChecked(
            self.config.get('ui.remember_window_position', True)
        )
        self.show_tooltips_check.setChecked(
            self.config.get('ui.show_tooltips', True)
        )
        self.progress_interval_spin.setValue(
            self.config.get('ui.progress_update_interval_ms', 100)
        )

        # Logging settings
        log_level = self.config.get('logging.level', 'INFO')
        index = self.log_level_combo.findText(log_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)

        self.log_retention_spin.setValue(
            self.config.get('logging.retention_days', 30)
        )
        self.log_max_size_spin.setValue(
            self.config.get('logging.max_file_size_mb', 10)
        )
        self.log_max_files_spin.setValue(
            self.config.get('logging.max_files', 10)
        )

        logger.debug("Settings loaded into dialog")

    def _on_browse_backup_dir(self):
        """Browse for backup directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            'Select Backup Directory',
            self.backup_dir_input.text()
        )
        if directory:
            self.backup_dir_input.setText(directory)

    def _on_reset_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            'Reset Settings',
            'Are you sure you want to reset all settings to defaults?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            defaults = ConfigManager._get_defaults()

            # Backup
            self.backup_dir_input.setText(defaults['backup']['directory'])
            self.retention_days_spin.setValue(defaults['backup']['retention_days'])
            self.auto_cleanup_check.setChecked(defaults['backup']['auto_cleanup'])
            self.compress_check.setChecked(defaults['backup']['compress'])

            # Processing
            pool_size = defaults['processing']['pool_size']
            self.pool_size_spin.setValue(pool_size if pool_size else 0)
            self.timeout_spin.setValue(defaults['processing']['timeout_per_file_seconds'])
            self.max_file_size_spin.setValue(defaults['processing']['max_file_size_mb'])
            self.warn_large_files_check.setChecked(defaults['processing']['warn_large_files'])
            self.skip_locked_check.setChecked(defaults['processing']['skip_locked_files'])

            # UI
            self.theme_combo.setCurrentText(defaults['ui']['theme'])
            self.remember_position_check.setChecked(defaults['ui']['remember_window_position'])
            self.show_tooltips_check.setChecked(defaults['ui']['show_tooltips'])
            self.progress_interval_spin.setValue(defaults['ui']['progress_update_interval_ms'])

            # Logging
            self.log_level_combo.setCurrentText(defaults['logging']['level'])
            self.log_retention_spin.setValue(defaults['logging']['retention_days'])
            self.log_max_size_spin.setValue(defaults['logging']['max_file_size_mb'])
            self.log_max_files_spin.setValue(defaults['logging']['max_files'])

            logger.info("Settings reset to defaults")

    def _on_save(self):
        """Save settings and close dialog."""
        # Validate backup directory
        backup_dir = self.backup_dir_input.text().strip()
        if backup_dir:
            backup_path = Path(backup_dir)
            if not backup_path.exists():
                reply = QMessageBox.question(
                    self,
                    'Create Directory',
                    f'Backup directory does not exist:\n{backup_dir}\n\nCreate it?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        backup_path.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        QMessageBox.critical(
                            self,
                            'Error',
                            f'Failed to create directory: {e}'
                        )
                        return
                else:
                    return

        # Save backup settings
        self.config.set('backup.directory', backup_dir or './backups')
        self.config.set('backup.retention_days', self.retention_days_spin.value())
        self.config.set('backup.auto_cleanup', self.auto_cleanup_check.isChecked())
        self.config.set('backup.compress', self.compress_check.isChecked())

        # Save processing settings
        pool_size = self.pool_size_spin.value()
        self.config.set('processing.pool_size', pool_size if pool_size > 0 else None)
        self.config.set('processing.timeout_per_file_seconds', self.timeout_spin.value())
        self.config.set('processing.max_file_size_mb', self.max_file_size_spin.value())
        self.config.set('processing.warn_large_files', self.warn_large_files_check.isChecked())
        self.config.set('processing.skip_locked_files', self.skip_locked_check.isChecked())

        # Save UI settings
        self.config.set('ui.theme', self.theme_combo.currentText())
        self.config.set('ui.remember_window_position', self.remember_position_check.isChecked())
        self.config.set('ui.show_tooltips', self.show_tooltips_check.isChecked())
        self.config.set('ui.progress_update_interval_ms', self.progress_interval_spin.value())

        # Save logging settings
        self.config.set('logging.level', self.log_level_combo.currentText())
        self.config.set('logging.retention_days', self.log_retention_spin.value())
        self.config.set('logging.max_file_size_mb', self.log_max_size_spin.value())
        self.config.set('logging.max_files', self.log_max_files_spin.value())

        logger.info("Settings saved")

        self.accept()
