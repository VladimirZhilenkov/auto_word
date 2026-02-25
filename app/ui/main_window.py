"""
Main application window with tabbed interface.
"""

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QAction, QStatusBar,
    QMessageBox, QFileDialog, QWidget, QVBoxLayout, QApplication
)

from .listeners_tab import ListenersTab
from .programs_tab import ProgramsTab
from .journals_tab import JournalsTab
from .dialogs import ImportDialog, GenerateDialog
from .dialogs.order_dialog import OrderGenerateDialog
from .dialogs.backup_dialog import BackupDialog
from .dialogs.database_config_dialog import DatabaseConfigDialog
from .dialogs.update_dialog import UpdateDialog


class MainWindow(QMainWindow):
    """
    Main application window with tabs for Listeners and Programs management.
    """
    
    APP_TITLE = "Генератор документов"
    APP_VERSION = "2.4.0"
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setWindowTitle(self.APP_TITLE)
        self.setMinimumSize(1200, 700)
        
        # Initialize UI components
        self._setup_ui()
        self._setup_toolbar()
        self._setup_menu()
        self._setup_statusbar()
        
        # Load initial data
        self._refresh_all()
    
    def _setup_ui(self):
        """Set up the main UI layout with tabs."""
        # Create central widget with tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setDocumentMode(True)
        
        # Create tabs
        self.listeners_tab = ListenersTab(self)
        self.programs_tab = ProgramsTab(self)
        self.journals_tab = JournalsTab(self)
        
        # Add tabs
        self.tab_widget.addTab(self.listeners_tab, "Слушатели")
        self.tab_widget.addTab(self.programs_tab, "Программы")
        self.tab_widget.addTab(self.journals_tab, "Журналы")
        
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # Set central widget
        self.setCentralWidget(self.tab_widget)
    
    def _setup_toolbar(self):
        """Set up the main toolbar."""
        toolbar = QToolBar("Главная панель")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Import Excel action
        self.action_import = QAction("Импорт из Excel", self)
        self.action_import.setShortcut(QKeySequence("Ctrl+I"))
        self.action_import.setStatusTip("Импортировать данные из Excel файла")
        self.action_import.triggered.connect(self._on_import)
        toolbar.addAction(self.action_import)
        
        toolbar.addSeparator()
        
        # Generate documents action
        self.action_generate = QAction("Создать документы", self)
        self.action_generate.setShortcut(QKeySequence("Ctrl+G"))
        self.action_generate.setStatusTip("Сгенерировать документы по шаблону")
        self.action_generate.triggered.connect(self._on_generate)
        toolbar.addAction(self.action_generate)
        
        # Generate order action
        self.action_generate_order = QAction("Создать приказ", self)
        self.action_generate_order.setShortcut(QKeySequence("Ctrl+Shift+G"))
        self.action_generate_order.setStatusTip("Сгенерировать приказ со списком слушателей")
        self.action_generate_order.triggered.connect(self._on_generate_order)
        toolbar.addAction(self.action_generate_order)
        
        toolbar.addSeparator()
        
        # Refresh action
        self.action_refresh = QAction("Обновить", self)
        self.action_refresh.setShortcut(QKeySequence.Refresh)
        self.action_refresh.setStatusTip("Обновить данные")
        self.action_refresh.triggered.connect(self._refresh_all)
        toolbar.addAction(self.action_refresh)
        
        toolbar.addSeparator()
        
        # Add listener action
        self.action_add_listener = QAction("Добавить слушателя", self)
        self.action_add_listener.setShortcut(QKeySequence("Ctrl+N"))
        self.action_add_listener.setStatusTip("Добавить нового слушателя")
        self.action_add_listener.triggered.connect(self._on_add_listener)
        toolbar.addAction(self.action_add_listener)
        
        # Add program action
        self.action_add_program = QAction("Добавить программу", self)
        self.action_add_program.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self.action_add_program.setStatusTip("Добавить новую программу")
        self.action_add_program.triggered.connect(self._on_add_program)
        toolbar.addAction(self.action_add_program)
    
    def _setup_menu(self):
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("Файл")
        
        file_menu.addAction(self.action_import)
        file_menu.addAction(self.action_generate)
        file_menu.addAction(self.action_generate_order)
        file_menu.addSeparator()
        
        # Export journals action
        action_export_journals = QAction("Экспорт журналов", self)
        action_export_journals.triggered.connect(self._export_journals)
        file_menu.addAction(action_export_journals)
        
        file_menu.addSeparator()
        
        # Open templates folder
        action_open_templates = QAction("Открыть папку шаблонов", self)
        action_open_templates.triggered.connect(self._open_templates_folder)
        file_menu.addAction(action_open_templates)
        
        # Open output folder
        action_open_output = QAction("Открыть папку документов", self)
        action_open_output.triggered.connect(self._open_output_folder)
        file_menu.addAction(action_open_output)
        
        file_menu.addSeparator()
        
        # Backup action
        action_backup = QAction("Управление резервными копиями", self)
        action_backup.triggered.connect(self._on_backup)
        file_menu.addAction(action_backup)
        
        # Database settings action
        action_db_settings = QAction("Настройки базы данных", self)
        action_db_settings.triggered.connect(self._on_database_settings)
        file_menu.addAction(action_db_settings)
        
        file_menu.addSeparator()
        
        # Exit
        action_exit = QAction("Выход", self)
        action_exit.setShortcut(QKeySequence.Quit)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # Edit menu
        edit_menu = menubar.addMenu("Редактирование")
        
        edit_menu.addAction(self.action_add_listener)
        edit_menu.addAction(self.action_add_program)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_refresh)
        
        # Help menu
        help_menu = menubar.addMenu("Справка")

        action_check_updates = QAction("Проверить обновления", self)
        action_check_updates.triggered.connect(self._on_check_updates)
        help_menu.addAction(action_check_updates)
        
        action_about = QAction("О программе", self)
        action_about.triggered.connect(self._show_about)
        help_menu.addAction(action_about)
        
        action_help = QAction("Справка по шаблонам", self)
        action_help.triggered.connect(self._show_template_help)
        help_menu.addAction(action_help)
    
    def _setup_statusbar(self):
        """Set up the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Готово")
    
    def _on_tab_changed(self, index: int):
        """Handle tab change."""
        tab_names = ["Слушатели", "Программы", "Журналы"]
        if 0 <= index < len(tab_names):
            self.statusbar.showMessage(f"Раздел: {tab_names[index]}")
        # Refresh data when switching to Journals tab
        if index == 2:
            self.journals_tab.refresh_data()
    
    def _on_import(self):
        """Handle import action."""
        dialog = ImportDialog(self)
        if dialog.exec_():
            self._refresh_all()
            self.statusbar.showMessage("Импорт завершен")
    
    def _on_generate(self):
        """Handle document generation action."""
        # Get selected listeners if on listeners tab
        selected_listeners = []
        if self.tab_widget.currentWidget() == self.listeners_tab:
            selected_listeners = self.listeners_tab.get_selected_listeners()
        
        # Get selected program if on programs tab
        selected_program = None
        if self.tab_widget.currentWidget() == self.programs_tab:
            selected_program = self.programs_tab.get_selected_program()
        
        dialog = GenerateDialog(
            parent=self,
            selected_listeners=selected_listeners,
            selected_program=selected_program
        )
        
        if dialog.exec_():
            self.statusbar.showMessage("Документы созданы")
    
    def _on_generate_order(self):
        """Handle order generation action."""
        # Get selected listeners if on listeners tab
        selected_listeners = []
        if self.tab_widget.currentWidget() == self.listeners_tab:
            selected_listeners = self.listeners_tab.get_selected_listeners()
        
        # Get selected program if on programs tab
        selected_program = None
        if self.tab_widget.currentWidget() == self.programs_tab:
            selected_program = self.programs_tab.get_selected_program()
        
        dialog = OrderGenerateDialog(
            parent=self,
            selected_listeners=selected_listeners,
            selected_program=selected_program
        )
        
        if dialog.exec_():
            self.statusbar.showMessage("Приказ создан")
    
    def _on_backup(self):
        """Handle backup management action."""
        dialog = BackupDialog(self)
        dialog.exec_()
    
    def _on_database_settings(self):
        """Handle database settings action."""
        dialog = DatabaseConfigDialog(self)
        dialog.connection_changed.connect(self._on_database_changed)
        dialog.exec_()
    
    def _on_database_changed(self):
        """Handle database connection change."""
        self._refresh_all()
        self.statusbar.showMessage("База данных переключена")
    
    def _on_add_listener(self):
        """Handle add listener action."""
        self.tab_widget.setCurrentWidget(self.listeners_tab)
        self.listeners_tab.add_listener()
    
    def _on_add_program(self):
        """Handle add program action."""
        self.tab_widget.setCurrentWidget(self.programs_tab)
        self.programs_tab.add_program()
    
    def _refresh_all(self):
        """Refresh all data in tabs."""
        self.listeners_tab.refresh_data()
        self.programs_tab.refresh_data()
        self.journals_tab.refresh_data()
        self.statusbar.showMessage("Данные обновлены")
    
    def _export_journals(self):
        """Switch to Journals tab and trigger export."""
        self.tab_widget.setCurrentWidget(self.journals_tab)
        self.journals_tab._export_excel()
    
    def _open_templates_folder(self):
        """Open templates folder in file manager."""
        import subprocess
        import sys
        
        templates_path = Path("templates")
        templates_path.mkdir(exist_ok=True)
        
        try:
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', str(templates_path)])
            elif sys.platform == 'win32':  # Windows
                subprocess.run(['explorer', str(templates_path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(templates_path)])
        except Exception as e:
            QMessageBox.warning(
                self, "Ошибка",
                f"Не удалось открыть папку: {e}"
            )
    
    def _open_output_folder(self):
        """Open output folder in file manager."""
        import subprocess
        import sys
        
        output_path = Path("output")
        output_path.mkdir(exist_ok=True)
        
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', str(output_path)])
            elif sys.platform == 'win32':
                subprocess.run(['explorer', str(output_path)])
            else:
                subprocess.run(['xdg-open', str(output_path)])
        except Exception as e:
            QMessageBox.warning(
                self, "Ошибка",
                f"Не удалось открыть папку: {e}"
            )
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "О программе",
            f"<h3>{self.APP_TITLE}</h3>"
            f"<p>Версия: {self.APP_VERSION}</p>"
            "<p>Приложение для автоматической генерации документов Word "
            "на основе шаблонов и базы данных слушателей.</p>"
            "<p><b>Основные возможности:</b></p>"
            "<ul>"
            "<li>Импорт данных из Excel</li>"
            "<li>Управление списком слушателей</li>"
            "<li>Управление программами обучения</li>"
            "<li>Генерация документов по шаблонам</li>"
            "<li>Автоматическое склонение ФИО</li>"
            "</ul>"
        )
    
    def _show_template_help(self):
        """Show template creation instructions."""
        from .dialogs.template_help_dialog import TemplateHelpDialog
        dialog = TemplateHelpDialog(self)
        dialog.exec_()

    def _on_check_updates(self):
        """Open update dialog."""
        dialog = UpdateDialog(self, current_version=self.APP_VERSION)
        dialog.exec_()
    
    def closeEvent(self, event):
        """Handle window close event."""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите выйти?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
