#!/usr/bin/env python3
"""
Document Generator Application
==============================

Desktop application for automated Word document generation from templates.
Uses PyQt5 for GUI, SQLite for storage, and docxtpl for template processing.

Usage:
    python main.py

Author: Document Generator Team
License: MIT
"""

import sys
import os
from pathlib import Path

from PyQt5.QtCore import QTimer

from app.services.update_service import UpdateService

# Add the application root to Python path
APP_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(APP_ROOT))


def setup_environment():
    """Set up application environment and directories."""
    # Create required directories
    directories = [
        APP_ROOT / "data",
        APP_ROOT / "data" / "backups",  # For database backups
        APP_ROOT / "docx_files",
        APP_ROOT / "output",
        APP_ROOT / "templates",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def init_database():
    """Initialize the database from saved configuration or defaults."""
    from app.database.connection import init_from_config, init_database as db_init
    from app.database.config import get_config_manager
    
    config_manager = get_config_manager()
    config = config_manager.load_config()
    
    # Check if we have a saved configuration
    if config.db_type != "sqlite" or config.sqlite_path:
        try:
            init_from_config()
            print(f"Database initialized from config: {config.db_type}")
            if config.db_type == "sqlite":
                print(f"  Path: {config.sqlite_path}")
            else:
                print(f"  Host: {config.host}:{config.port}/{config.database}")
            return
        except Exception as e:
            print(f"Failed to initialize from config: {e}")
            print("Falling back to default SQLite database")
    
    # Default SQLite initialization
    db_path = APP_ROOT / "data" / "database.db"
    db_init(db_path)
    print(f"Database initialized at: {db_path}")


def create_application():
    """Create and configure the Qt application."""
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    
    # Enable High DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Генератор документов")
    app.setApplicationVersion("2.3.2")
    app.setOrganizationName("Document Generator")
    
    # Set application style
    app.setStyle("Fusion")
    
    return app


def create_main_window():
    """Create and show the main window."""
    from app.ui.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    
    return window




def check_updates_silently(window):
    """Background update check with statusbar notice."""
    try:
        svc = UpdateService(current_version=getattr(window, "APP_VERSION", "0.0.0"))
        result = svc.check_for_updates()
        if result.get("available") and hasattr(window, "statusbar"):
            window.statusbar.showMessage(
                f"Доступно обновление {result.get('version')} — откройте меню 'Справка'"
            )
    except Exception:
        # Silent failure
        pass


def main():
    """Main entry point."""
    print("=" * 50)
    print("Генератор документов v2.3.2")
    print("=" * 50)
    
    # Setup environment
    print("Настройка окружения...")
    setup_environment()
    
    # Initialize database
    print("Инициализация базы данных...")
    init_database()
    
    # Create Qt application
    print("Запуск приложения...")
    app = create_application()
    
    # Create and show main window
    window = create_main_window()

    # Background update check
    QTimer.singleShot(5000, lambda: check_updates_silently(window))
    
    # Run the application
    print("Приложение запущено")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
