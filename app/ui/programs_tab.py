"""
Programs tab - table view and management of training programs.
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
from ..database.models import Program
from .dialogs import ProgramFormDialog


class ProgramsTab(QWidget):
    """
    Tab widget for managing training programs (программы обучения).
    """
    
    # Table column configuration
    COLUMNS = [
        ('id', 'ID', 50),
        ('program_name', 'Наименование', 300),
        ('program_short_name', 'Краткое название', 150),
        ('training_period', 'Период обучения', 120),
        ('education_form', 'Форма', 100),
        ('expulsion_date', 'Дата отчисления', 120),
        ('listener_count', 'Слушателей', 80),
    ]
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._programs: List[Program] = []
        
        self._setup_ui()
        self._setup_context_menu()
    
    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        
        search_label = QLabel("Поиск:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите название программы...")
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setClearButtonEnabled(True)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # Table view
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
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
        self.proxy_model.setFilterKeyColumn(-1)
        
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
        self.btn_add.clicked.connect(self.add_program)
        
        self.btn_edit = QPushButton("Редактировать")
        self.btn_edit.clicked.connect(self._edit_selected)
        
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete_selected)
        
        self.btn_manage_listeners = QPushButton("Управление слушателями")
        self.btn_manage_listeners.clicked.connect(self._manage_listeners)

        self.btn_import_grades = QPushButton("📊 Импорт оценок")
        self.btn_import_grades.setToolTip("Импортировать оценки слушателей из XLSX")
        self.btn_import_grades.clicked.connect(self._import_grades)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh_data)

        # Statistics label
        self.stats_label = QLabel("Всего: 0")

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addWidget(self.btn_manage_listeners)
        button_layout.addWidget(self.btn_import_grades)
        button_layout.addStretch()
        button_layout.addWidget(self.stats_label)
        button_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(button_layout)
    
    def _setup_context_menu(self):
        """Set up the context menu."""
        self.context_menu = QMenu(self)
        
        action_edit = QAction("Редактировать", self)
        action_edit.triggered.connect(self._edit_selected)
        self.context_menu.addAction(action_edit)
        
        action_manage = QAction("Управление слушателями", self)
        action_manage.triggered.connect(self._manage_listeners)
        self.context_menu.addAction(action_manage)
        
        self.context_menu.addSeparator()
        
        action_delete = QAction("Удалить", self)
        action_delete.triggered.connect(self._delete_selected)
        self.context_menu.addAction(action_delete)
    
    def _show_context_menu(self, position):
        """Show context menu."""
        if self.table_view.selectionModel().hasSelection():
            self.context_menu.exec_(self.table_view.viewport().mapToGlobal(position))
    
    def refresh_data(self):
        """Refresh data from database."""
        self._programs.clear()
        self.model.removeRows(0, self.model.rowCount())
        
        try:
            with DatabaseSession() as session:
                programs = session.query(Program).order_by(
                    Program.expulsion_date.desc().nulls_last()
                ).all()
                
                for program in programs:
                    # Get listener count
                    listener_count = len(program.listeners)
                    self._add_program_to_model(program, listener_count)
                    self._programs.append(program)
            
            self._update_stats()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка загрузки данных: {e}"
            )
    
    def _add_program_to_model(self, program: Program, listener_count: int = 0):
        """Add a program to the table model."""
        row = []
        
        for col_name, _, _ in self.COLUMNS:
            if col_name == 'id':
                item = QStandardItem(str(program.id))
            elif col_name == 'program_name':
                # Truncate long names for display
                name = program.program_name or ''
                if len(name) > 80:
                    name = name[:80] + '...'
                item = QStandardItem(name)
                item.setToolTip(program.program_name or '')
            elif col_name == 'expulsion_date':
                item = QStandardItem(program.formatted_expulsion_date)
            elif col_name == 'listener_count':
                item = QStandardItem(str(listener_count))
            else:
                value = getattr(program, col_name, '') or ''
                item = QStandardItem(str(value))
            
            item.setEditable(False)
            item.setData(program.id, Qt.UserRole)
            row.append(item)
        
        self.model.appendRow(row)
    
    def _update_stats(self):
        """Update statistics label."""
        total = len(self._programs)
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
    
    def add_program(self):
        """Open dialog to add new program."""
        dialog = ProgramFormDialog(parent=self)
        
        if dialog.exec_():
            data = dialog.get_data()
            
            try:
                with DatabaseSession() as session:
                    program = Program(**data)
                    session.add(program)
                    session.commit()
                
                self.refresh_data()
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка",
                    f"Ошибка добавления программы: {e}"
                )
    
    def _edit_selected(self):
        """Edit selected program."""
        program_id = self._get_selected_id()
        
        if program_id is None:
            QMessageBox.information(
                self, "Информация",
                "Выберите программу для редактирования"
            )
            return
        
        try:
            with DatabaseSession() as session:
                program = session.query(Program).get(program_id)
                
                if not program:
                    QMessageBox.warning(
                        self, "Ошибка",
                        "Программа не найдена"
                    )
                    return
                
                dialog = ProgramFormDialog(parent=self, program=program)
                
                if dialog.exec_():
                    data = dialog.get_data()
                    
                    for key, value in data.items():
                        setattr(program, key, value)
                    
                    session.commit()
                    self.refresh_data()
                    
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка редактирования: {e}"
            )
    
    def _delete_selected(self):
        """Delete selected program."""
        program_id = self._get_selected_id()
        
        if program_id is None:
            QMessageBox.information(
                self, "Информация",
                "Выберите программу для удаления"
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить эту программу?\n"
            "Связи со слушателями также будут удалены.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                with DatabaseSession() as session:
                    program = session.query(Program).get(program_id)
                    if program:
                        session.delete(program)
                        session.commit()
                
                self.refresh_data()
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка",
                    f"Ошибка удаления: {e}"
                )
    
    def _import_grades(self):
        """Open dialog to import grades from XLSX into the selected program."""
        program_id = self._get_selected_id()
        from .dialogs import GradesImportDialog
        dialog = GradesImportDialog(parent=self, preselect_program_id=program_id)
        dialog.exec_()

    def _manage_listeners(self):
        """Open dialog to manage listeners for the selected program."""
        program_id = self._get_selected_id()

        if program_id is None:
            QMessageBox.information(
                self, "Информация",
                "Выберите программу для управления слушателями"
            )
            return

        from .dialogs import ProgramListenersDialog
        
        try:
            with DatabaseSession() as session:
                program = session.query(Program).get(program_id)
                
                if program:
                    dialog = ProgramListenersDialog(parent=self, program=program)
                    dialog.exec_()
                    self.refresh_data()
                    
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка: {e}"
            )
    
    def _get_selected_id(self) -> Optional[int]:
        """Get ID of the selected program."""
        indexes = self.table_view.selectionModel().selectedRows()
        
        if indexes:
            proxy_index = indexes[0]
            source_index = self.proxy_model.mapToSource(proxy_index)
            item = self.model.item(source_index.row(), 0)
            
            if item:
                return item.data(Qt.UserRole)
        
        return None
    
    def get_selected_program(self) -> Optional[Program]:
        """Get the selected Program object."""
        program_id = self._get_selected_id()
        
        if program_id:
            for program in self._programs:
                if program.id == program_id:
                    return program
        
        return None
    
    def get_all_programs(self) -> List[Program]:
        """Get all programs."""
        return list(self._programs)
