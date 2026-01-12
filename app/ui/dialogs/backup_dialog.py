"""
Backup management dialog for creating and restoring backups.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QInputDialog, QMessageBox,
    QHeaderView, QFileDialog
)
from PyQt5.QtGui import QFont, QColor

from ...services.backup_manager import BackupManager


class BackupDialog(QDialog):
    """
    Dialog for managing database backups.
    """
    
    backup_restored = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Управление резервными копиями")
        self.setGeometry(100, 100, 800, 500)
        
        # Initialize backup manager
        self.backup_manager = BackupManager()
        
        # Setup UI
        self._setup_ui()
        
        # Load backups
        self._refresh_backups()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Управление резервными копиями базы данных")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Info about current backups
        info_label = QLabel("Доступные резервные копии:")
        layout.addWidget(info_label)
        
        # Backups table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Дата создания", "Размер (MB)", "Описание", ""])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # Create backup button
        btn_create = QPushButton("Создать копию")
        btn_create.clicked.connect(self._on_create_backup)
        button_layout.addWidget(btn_create)
        
        button_layout.addSpacing(10)
        
        # Restore button
        self.btn_restore = QPushButton("Восстановить")
        self.btn_restore.clicked.connect(self._on_restore)
        button_layout.addWidget(self.btn_restore)
        
        # Delete button
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._on_delete)
        button_layout.addWidget(self.btn_delete)
        
        button_layout.addSpacing(10)
        
        # Export backup button
        btn_export = QPushButton("Экспортировать")
        btn_export.clicked.connect(self._on_export)
        button_layout.addWidget(btn_export)
        
        # Close button
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        button_layout.addWidget(btn_close)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _refresh_backups(self):
        """Refresh the backups table."""
        self.table.setRowCount(0)
        
        backups = self.backup_manager.list_backups()
        
        for idx, backup in enumerate(backups):
            self.table.insertRow(idx)
            
            # Created date
            created_item = QTableWidgetItem(
                backup['created'].strftime("%Y-%m-%d %H:%M:%S")
            )
            self.table.setItem(idx, 0, created_item)
            
            # Size
            size_mb = self.backup_manager.get_backup_size_mb(backup['path'])
            size_item = QTableWidgetItem(f"{size_mb:.2f}")
            self.table.setItem(idx, 1, size_item)
            
            # Description
            desc_item = QTableWidgetItem(backup['description'])
            self.table.setItem(idx, 2, desc_item)
            
            # Store backup path as user data
            created_item.setData(Qt.UserRole, backup['path'])
        
        # Update button states
        self._update_button_states()
    
    def _update_button_states(self):
        """Update restore/delete button states based on selection."""
        has_selection = self.table.currentRow() >= 0
        self.btn_restore.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
    
    def _get_selected_backup_path(self) -> Optional[str]:
        """Get path of currently selected backup."""
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            return item.data(Qt.UserRole)
        return None
    
    def _on_create_backup(self):
        """Handle create backup button."""
        # Ask for description
        text, ok = QInputDialog.getText(
            self,
            "Создать резервную копию",
            "Введите описание (необязательно):",
            text=""
        )
        
        if ok:
            backup_path = self.backup_manager.create_backup(
                description=text if text else "Manual backup"
            )
            
            if backup_path:
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Резервная копия создана:\n{Path(backup_path).name}"
                )
                self._refresh_backups()
            else:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    "Не удалось создать резервную копию"
                )
    
    def _on_restore(self):
        """Handle restore backup button."""
        backup_path = self._get_selected_backup_path()
        
        if not backup_path:
            return
        
        # Confirm restoration
        reply = QMessageBox.warning(
            self,
            "Восстановление из резервной копии",
            "Это действие заменит текущую базу данных на резервную копию.\n"
            "Текущая база будет сохранена как backup_pre_restore_*.\n\n"
            "Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.backup_manager.restore_backup(backup_path):
                QMessageBox.information(
                    self,
                    "Успех",
                    "База данных восстановлена из резервной копии.\n"
                    "Приложение необходимо перезагрузить."
                )
                self.backup_restored.emit(backup_path)
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    "Не удалось восстановить базу данных"
                )
    
    def _on_delete(self):
        """Handle delete backup button."""
        backup_path = self._get_selected_backup_path()
        
        if not backup_path:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Удалить резервную копию",
            f"Удалить файл {Path(backup_path).name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.backup_manager.delete_backup(backup_path):
                QMessageBox.information(self, "Успех", "Резервная копия удалена")
                self._refresh_backups()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить резервную копию")
    
    def _on_export(self):
        """Handle export backup button."""
        backup_path = self._get_selected_backup_path()
        
        if not backup_path:
            return
        
        backup_file = Path(backup_path)
        
        # Ask where to save
        file_dialog = QFileDialog()
        save_path, _ = file_dialog.getSaveFileName(
            self,
            "Экспортировать резервную копию",
            backup_file.name,
            "Database Files (*.db)"
        )
        
        if save_path:
            try:
                import shutil
                shutil.copy2(str(backup_path), save_path)
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Резервная копия экспортирована в:\n{save_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось экспортировать резервную копию:\n{str(e)}"
                )
    
    def changeEvent(self, event):
        """Handle selection changes."""
        if event.type() == 3:  # QEvent.WindowDeactivate
            self._update_button_states()
