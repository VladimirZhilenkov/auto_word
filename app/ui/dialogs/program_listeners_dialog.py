"""
Dialog for managing program-listener associations.
"""

from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QGroupBox, QMessageBox,
    QListWidget, QListWidgetItem, QAbstractItemView,
    QSpinBox, QDateEdit
)
from PyQt5.QtCore import QDate

from ...database.connection import DatabaseSession
from ...database.models import Listener, Program, ProgramListener


class ProgramListenersDialog(QDialog):
    """
    Dialog for managing which listeners are enrolled in a program.
    """
    
    def __init__(self, parent=None, program: Program = None):
        super().__init__(parent)
        
        self.program = program
        self.program_id = program.id if program else None
        
        self._all_listeners: List[Listener] = []
        self._enrolled_ids: List[int] = []
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        program_name = self.program.display_name if self.program else "Программа"
        self.setWindowTitle(f"Слушатели программы: {program_name}")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Program info
        info_label = QLabel(f"<b>Программа:</b> {self.program.program_name if self.program else ''}")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Main content - two lists
        lists_layout = QHBoxLayout()
        
        # Available listeners (left)
        available_group = QGroupBox("Доступные слушатели")
        available_layout = QVBoxLayout(available_group)
        
        self.list_available = QListWidget()
        self.list_available.setSelectionMode(QAbstractItemView.ExtendedSelection)
        available_layout.addWidget(self.list_available)
        
        lists_layout.addWidget(available_group)
        
        # Buttons in the middle
        buttons_layout = QVBoxLayout()
        buttons_layout.addStretch()
        
        self.btn_add = QPushButton("→ Добавить →")
        self.btn_add.clicked.connect(self._add_listeners)
        buttons_layout.addWidget(self.btn_add)
        
        self.btn_remove = QPushButton("← Удалить ←")
        self.btn_remove.clicked.connect(self._remove_listeners)
        buttons_layout.addWidget(self.btn_remove)
        
        buttons_layout.addStretch()
        
        self.btn_add_all = QPushButton("Добавить всех →")
        self.btn_add_all.clicked.connect(self._add_all_listeners)
        buttons_layout.addWidget(self.btn_add_all)
        
        self.btn_remove_all = QPushButton("← Удалить всех")
        self.btn_remove_all.clicked.connect(self._remove_all_listeners)
        buttons_layout.addWidget(self.btn_remove_all)
        
        buttons_layout.addStretch()
        
        lists_layout.addLayout(buttons_layout)
        
        # Enrolled listeners (right)
        enrolled_group = QGroupBox("Слушатели программы")
        enrolled_layout = QVBoxLayout(enrolled_group)
        
        self.list_enrolled = QListWidget()
        self.list_enrolled.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_enrolled.setDragDropMode(QAbstractItemView.InternalMove)
        enrolled_layout.addWidget(self.list_enrolled)
        
        # Enrolled count label
        self.label_count = QLabel("Слушателей: 0")
        enrolled_layout.addWidget(self.label_count)
        
        lists_layout.addWidget(enrolled_group)
        
        layout.addLayout(lists_layout)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.clicked.connect(self._save)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_save)
        button_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(button_layout)
    
    def _load_data(self):
        """Load listeners data."""
        if not self.program_id:
            return
        
        try:
            with DatabaseSession() as session:
                # Get all listeners
                self._all_listeners = session.query(Listener).order_by(
                    Listener.last_name
                ).all()
                
                # Get enrolled listener IDs
                enrolled = session.query(ProgramListener).filter(
                    ProgramListener.program_id == self.program_id
                ).order_by(ProgramListener.order_number).all()
                
                self._enrolled_ids = [pl.listener_id for pl in enrolled]
            
            self._refresh_lists()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка загрузки данных: {e}"
            )
    
    def _refresh_lists(self):
        """Refresh both list widgets."""
        self.list_available.clear()
        self.list_enrolled.clear()
        
        for listener in self._all_listeners:
            item = QListWidgetItem(
                f"{listener.full_name} ({listener.workplace or 'Не указано'})"
            )
            item.setData(Qt.UserRole, listener.id)
            
            if listener.id in self._enrolled_ids:
                self.list_enrolled.addItem(item)
            else:
                self.list_available.addItem(item)
        
        self._update_count()
    
    def _update_count(self):
        """Update enrolled count label."""
        count = self.list_enrolled.count()
        self.label_count.setText(f"Слушателей: {count}")
    
    def _add_listeners(self):
        """Add selected listeners to the program."""
        for item in self.list_available.selectedItems():
            listener_id = item.data(Qt.UserRole)
            if listener_id not in self._enrolled_ids:
                self._enrolled_ids.append(listener_id)
        
        self._refresh_lists()
    
    def _remove_listeners(self):
        """Remove selected listeners from the program."""
        for item in self.list_enrolled.selectedItems():
            listener_id = item.data(Qt.UserRole)
            if listener_id in self._enrolled_ids:
                self._enrolled_ids.remove(listener_id)
        
        self._refresh_lists()
    
    def _add_all_listeners(self):
        """Add all listeners to the program."""
        self._enrolled_ids = [l.id for l in self._all_listeners]
        self._refresh_lists()
    
    def _remove_all_listeners(self):
        """Remove all listeners from the program."""
        self._enrolled_ids.clear()
        self._refresh_lists()
    
    def _save(self):
        """Save changes to database."""
        if not self.program_id:
            self.reject()
            return
        
        try:
            with DatabaseSession() as session:
                # Delete existing associations
                session.query(ProgramListener).filter(
                    ProgramListener.program_id == self.program_id
                ).delete()
                
                # Create new associations with order numbers
                for idx, listener_id in enumerate(self._enrolled_ids, start=1):
                    assoc = ProgramListener(
                        program_id=self.program_id,
                        listener_id=listener_id,
                        order_number=idx
                    )
                    session.add(assoc)
                
                session.commit()
            
            QMessageBox.information(
                self, "Успех",
                f"Сохранено слушателей: {len(self._enrolled_ids)}"
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка сохранения: {e}"
            )
