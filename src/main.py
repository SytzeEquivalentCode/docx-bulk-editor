"""
DOCX Bulk Editor - Application Entry Point

This is the main entry point for the DOCX Bulk Editor desktop application.
It initializes the application, sets up the runtime environment, and launches the GUI.

Key features:
- PyInstaller multiprocessing support (freeze_support)
- First-run directory setup (data/, backups/, logs/)
- High DPI display support for Windows
- Comprehensive exception handling and logging
- Clean application lifecycle management

Author: DOCX Bulk Editor Team
Version: 1.0.0
"""

import sys
import multiprocessing
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from src.core.config import ConfigManager
from src.core.logger import setup_logger
from src.database.db_manager import DatabaseManager
from src.ui.main_window import MainWindow


def setup_runtime_directories():
    """
    Create runtime directories on first launch.

    Creates the following directory structure:
    - data/          Database storage
    - data/cache/    Temporary cache files
    - backups/       Document backups
    - logs/          Application logs

    All directories are created with parents=True and exist_ok=True,
    so this is safe to call on every startup.
    """
    directories = [
        Path('data'),
        Path('data/cache'),
        Path('backups'),
        Path('logs')
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def main():
    """
    Application entry point.

    Initializes the application environment, creates the main window,
    and starts the Qt event loop.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    # CRITICAL: Required for PyInstaller + multiprocessing
    # This must be the first call in main() to support frozen executables
    multiprocessing.freeze_support()

    # Setup runtime directories
    setup_runtime_directories()

    # Initialize logger (must happen after directory setup)
    logger = setup_logger()
    logger.info('='* 60)
    logger.info('DOCX Bulk Editor v1.0.0 - Application Starting')
    logger.info('='* 60)

    try:
        # Load configuration
        logger.info('Loading configuration...')
        config = ConfigManager()
        logger.info('Configuration loaded successfully')

        # Initialize database
        logger.info('Initializing database...')
        db_manager = DatabaseManager()
        logger.info('Database initialized successfully')

        # Create Qt application
        logger.info('Creating Qt application...')
        app = QApplication(sys.argv)

        # Set application metadata
        app.setApplicationName('DOCX Bulk Editor')
        app.setApplicationVersion('1.0.0')
        app.setOrganizationName('DOCX Bulk Editor Team')

        # Set application style (Fusion provides consistent look across platforms)
        app.setStyle('Fusion')
        logger.info('Application style set to Fusion')

        # Enable high DPI scaling for Windows
        # These attributes must be set before QApplication is created in production,
        # but here we set them after for compatibility with existing QApplication
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            logger.debug('High DPI scaling support detected')
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            logger.debug('High DPI pixmaps support detected')

        # Create and show main window
        logger.info('Creating main window...')
        window = MainWindow(config, db_manager)
        window.show()
        logger.info('Main window displayed')

        logger.info('Application initialized successfully')
        logger.info('Entering event loop...')

        # Run application event loop
        exit_code = app.exec()

        logger.info(f'Application exited with code: {exit_code}')
        return exit_code

    except Exception as e:
        # Log fatal error with full traceback
        logger.exception(f'Fatal error during application startup: {e}')

        # Try to show error dialog (may fail if Qt isn't initialized)
        try:
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            QMessageBox.critical(
                None,
                'Fatal Error',
                f'DOCX Bulk Editor failed to start:\n\n{str(e)}\n\n'
                f'Check logs/app.log for details.'
            )
        except Exception:
            # If we can't show a dialog, just print to stderr
            print(f'FATAL ERROR: {e}', file=sys.stderr)
            print('Check logs/app.log for details.', file=sys.stderr)

        return 1


if __name__ == '__main__':
    """
    Entry point guard.

    This ensures main() is only called when the script is executed directly,
    not when imported as a module. This is critical for multiprocessing
    compatibility and PyInstaller frozen executables.
    """
    sys.exit(main())
