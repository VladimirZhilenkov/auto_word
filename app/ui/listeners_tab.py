"""
Listeners tab - table view and management of listeners (слушатели).
"""

from typing import List, Optional

from PyQt5.QtCore import Qt, QSortFilterProxyModel
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QLineEdit, QLabel, QMessageBox, QHeaderView, QAbstractItemView,
    QMenu, QAction
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from ..database.connection import DatabaseSession
from ..database.models import Listener
from .dialogs import ListenerFormDialog


class ListenersTab(QWidget):
    """
    Tab widget for managing listeners (слушатели).
    Displays a table with search, add, edit, delete functionality.
    """
    
    # Table column configuration
    COLUMNS = [
        ('id', 'ID', 50),
        ('full_name', 'ФИО', 220),
        ('position', 'Должность', 150),
        ('workplace', 'Место работы', 200),
        ('region', 'Субъект РФ', 120),
        ('mobile_phone', 'Телефон', 120),
        ('email', 'Email', 150),
        ('notes', 'Примечания', 100),
    ]
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._listeners: List[Listener] = []
        
        self._setup_ui()
        self._setup_context_menu()
    
    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        
        search_label = QLabel("Поиск:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите ФИО, должность или место работы...")
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setClearButtonEnabled(True)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # Table view
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)
        self.table_view.doubleClicked.connect(self._on_double_click)
        
        # Set up model
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([col[1] for col in self.COLUMNS])
        
        # Set up proxy model for filtering
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)  # Search all columns
        
        self.table_view.setModel(self.proxy_model)
        
        # Configure column widths
        header = self.table_view.horizontalHeader()
        for i, (_, _, width) in enumerate(self.COLUMNS):
            self.table_view.setColumnWidth(i, width)
        header.setStretchLastSection(True)
        
        layout.addWidget(self.table_view)
        
        # Button bar
        button_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Добавить")
        self.btn_add.clicked.connect(self.add_listener)
        
        self.btn_edit = QPushButton("Редактировать")
        self.btn_edit.clicked.connect(self._edit_selected)
        
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete_selected)
        
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh_data)
        
        # Statistics label
        self.stats_label = QLabel("Всего: 0")
        
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addStretch()
        button_layout.addWidget(self.stats_label)
        button_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(button_layout)
    
    def _setup_context_menu(self):
        """Set up the context menu for the table."""
        self.context_menu = QMenu(self)
        
        action_edit = QAction("Редактировать", self)
        action_edit.triggered.connect(self._edit_selected)
        self.context_menu.addAction(action_edit)
        
        action_delete = QAction("Удалить", self)
        action_delete.triggered.connect(self._delete_selected)
        self.context_menu.addAction(action_delete)
        
        self.context_menu.addSeparator()
        
        action_copy_name = QAction("Копировать ФИО", self)
        action_copy_name.triggered.connect(self._copy_name)
        self.context_menu.addAction(action_copy_name)
    
    def _show_context_menu(self, position):
        """Show context menu at position."""
        if self.table_view.selectionModel().hasSelection():
            self.context_menu.exec_(self.table_view.viewport().mapToGlobal(position))
    
    def refresh_data(self):
        """Refresh data from database."""
        self._listeners.clear()
        self.model.removeRows(0, self.model.rowCount())
        
        try:
            with DatabaseSession() as session:
                listeners = session.query(Listener).order_by(Listener.last_name).all()
                
                for listener in listeners:
                    self._add_listener_to_model(listener)
                    self._listeners.append(listener)
            
            self._update_stats()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка загрузки данных: {e}"
            )
    
    def _add_listener_to_model(self, listener: Listener):
        """Add a listener to the table model."""
        row = []
        
        for col_name, _, _ in self.COLUMNS:
            if col_name == 'id':
                item = QStandardItem(str(listener.id))
            elif col_name == 'full_name':
                item = QStandardItem(listener.full_name)
            else:
                value = getattr(listener, col_name, '') or ''
                item = QStandardItem(str(value))
            
            item.setEditable(False)
            item.setData(listener.id, Qt.UserRole)  # Store ID for reference
            row.append(item)
        
        self.model.appendRow(row)
    
    def _update_stats(self):
        """Update statistics label."""
        total = len(self._listeners)
        visible = self.proxy_model.rowCount()
        
        if total == visible:
            self.stats_label.setText(f"Всего: {total}")
        else:
            self.stats_label.setText(f"Показано: {visible} из {total}")
    
    def _on_search(self, text: str):
        """Handle search input change."""
        self.proxy_model.setFilterRegularExpression(text)
        self._update_stats()
    
    def _on_double_click(self, index):
        """Handle double-click on table row."""
        self._edit_selected()
    
    def add_listener(self):
        """Open dialog to add new listener."""
        dialog = ListenerFormDialog(parent=self)
        
        if dialog.exec_():
            data = dialog.get_data()
            
            try:
                with DatabaseSession() as session:
                    listener = Listener(**data)
                    session.add(listener)
                    session.commit()
                
                self.refresh_data()
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка",
                    f"Ошибка добавления слушателя: {e}"
                )
    
    def _edit_selected(self):
        """Edit selected listener."""
        listener_id = self._get_selected_id()
        
        if listener_id is None:
            QMessageBox.information(
                self, "Информация",
                "Выберите слушателя для редактирования"
            )
            return
        
        try:
            with DatabaseSession() as session:
                listener = session.query(Listener).get(listener_id)
                
                if not listener:
                    QMessageBox.warning(
                        self, "Ошибка",
                        "Слушатель не найден"
                    )
                    return
                
                dialog = ListenerFormDialog(parent=self, listener=listener)
                
                if dialog.exec_():
                    data = dialog.get_data()
                    
                    for key, value in data.items():
                        setattr(listener, key, value)
                    
                    session.commit()
                    self.refresh_data()
                    
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка редактирования: {e}"
            )
    
    def _delete_selected(self):
        """Delete selected listeners."""
        selected_ids = self._get_selected_ids()
        
        if not selected_ids:
            QMessageBox.information(
                self, "Информация",
                "Выберите слушателей для удаления"
            )
            return
        
        count = len(selected_ids)
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить {count} слушател{'я' if count == 1 else 'ей'}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                with DatabaseSession() as session:
                    session.query(Listener).filter(
                        Listener.id.in_(selected_ids)
                    ).delete(synchronize_session=False)
                    session.commit()
                
                self.refresh_data()
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка",
                    f"Ошибка удаления: {e}"
                )
    
    def _copy_name(self):
        """Copy selected listener's name to clipboard."""
        listener_id = self._get_selected_id()
        
        if listener_id:
            for listener in self._listeners:
                if listener.id == listener_id:
                    from PyQt5.QtWidgets import QApplication
                    QApplication.clipboard().setText(listener.full_name)
                    break
    
    def _get_selected_id(self) -> Optional[int]:
        """Get ID of the first selected listener."""
        indexes = self.table_view.selectionModel().selectedRows()
        
        if indexes:
            proxy_index = indexes[0]
            source_index = self.proxy_model.mapToSource(proxy_index)
            item = self.model.item(source_index.row(), 0)
            
            if item:
                return item.data(Qt.UserRole)
        
        return None
    
    def _get_selected_ids(self) -> List[int]:
        """Get IDs of all selected listeners."""
        ids = []
        indexes = self.table_view.selectionModel().selectedRows()
        
        for proxy_index in indexes:
            source_index = self.proxy_model.mapToSource(proxy_index)
            item = self.model.item(source_index.row(), 0)
            
            if item:
                listener_id = item.data(Qt.UserRole)
                if listener_id:
                    ids.append(listener_id)
        
        return ids
    
    def get_selected_listeners(self) -> List[Listener]:
        """Get list of selected Listener objects."""
        selected_ids = self._get_selected_ids()
        return [l for l in self._listeners if l.id in selected_ids]
    
    def get_all_listeners(self) -> List[Listener]:
        """Get all listeners."""
        return list(self._listeners)
