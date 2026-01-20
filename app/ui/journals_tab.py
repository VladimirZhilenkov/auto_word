"""
Journals tab - view and manage Order Journal entries.
"""

from datetime import date
from typing import List, Optional
import subprocess
import sys

from PyQt5.QtCore import Qt, QSortFilterProxyModel, QDate
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QLabel, QMessageBox, QHeaderView, QAbstractItemView,
    QMenu, QAction, QComboBox, QDateEdit, QLineEdit, QFormLayout, QGroupBox
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor

from ..database.connection import DatabaseSession
from .dialogs.journal_entry_dialog import JournalEntryDialog
from ..services.order_journal_service import OrderJournalService, ORDER_TYPE_LABELS


class JournalsTab(QWidget):
    """Tab widget for managing Order Journal entries."""

    COLUMNS = [
        ('order_number', '№', 60),
        ('order_date', 'Дата', 100),
        ('title', 'Наименование', 350),
        ('executor', 'Исполнитель', 150),
        ('program_name', 'Программа', 200),
        ('notes', 'Примечание', 200),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = OrderJournalService()
        self._entries: List = []
        self._setup_ui()
        self._setup_context_menu()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Filters group
        filter_group = QGroupBox("Фильтры")
        filter_layout = QFormLayout(filter_group)

        # Journal type combobox
        self.combo_journal_type = QComboBox()
        for key, label in ORDER_TYPE_LABELS.items():
            self.combo_journal_type.addItem(label, key)
        filter_layout.addRow("Тип журнала:", self.combo_journal_type)

        # Period
        period_layout = QHBoxLayout()
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        # Default: start of current year
        self.date_from.setDate(QDate(date.today().year, 1, 1))

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setDate(QDate.currentDate())

        period_layout.addWidget(QLabel("с"))
        period_layout.addWidget(self.date_from)
        period_layout.addWidget(QLabel("по"))
        period_layout.addWidget(self.date_to)
        period_layout.addStretch()

        filter_layout.addRow("Период:", period_layout)

        # Free-text search
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Поиск по всем полям...")
        self.edit_search.setClearButtonEnabled(True)
        filter_layout.addRow("Поиск:", self.edit_search)

        # Apply button
        btn_apply = QPushButton("Применить фильтр")
        btn_apply.clicked.connect(self.refresh_data)
        filter_layout.addRow("", btn_apply)

        layout.addWidget(filter_group)

        # Table
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.setSortingEnabled(False)  # Manual ordering newest first
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)
        self.table_view.doubleClicked.connect(self._edit_selected)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([col[1] for col in self.COLUMNS])

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)

        self.table_view.setModel(self.proxy_model)

        header = self.table_view.horizontalHeader()
        for i, (_, _, width) in enumerate(self.COLUMNS):
            self.table_view.setColumnWidth(i, width)
        header.setStretchLastSection(True)

        layout.addWidget(self.table_view)

        # Button bar
        button_layout = QHBoxLayout()

        self.btn_add = QPushButton("Добавить запись вручную")
        self.btn_add.clicked.connect(self._add_entry)

        self.btn_edit = QPushButton("Редактировать")
        self.btn_edit.clicked.connect(self._edit_selected)

        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete_selected)

        self.btn_export = QPushButton("Экспорт в Excel")
        self.btn_export.clicked.connect(self._export_excel)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh_data)

        self.stats_label = QLabel("Всего записей: 0")

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addWidget(self.btn_export)
        button_layout.addStretch()
        button_layout.addWidget(self.stats_label)
        button_layout.addWidget(self.btn_refresh)

        layout.addLayout(button_layout)

    def _setup_context_menu(self):
        self.context_menu = QMenu(self)
        action_edit = QAction("Редактировать", self)
        action_edit.triggered.connect(self._edit_selected)
        self.context_menu.addAction(action_edit)

        action_delete = QAction("Удалить", self)
        action_delete.triggered.connect(self._delete_selected)
        self.context_menu.addAction(action_delete)

        self.context_menu.addSeparator()

        action_open_doc = QAction("Открыть документ", self)
        action_open_doc.triggered.connect(self._open_document)
        self.context_menu.addAction(action_open_doc)

    def _show_context_menu(self, position):
        if self.table_view.selectionModel().hasSelection():
            self.context_menu.exec_(self.table_view.viewport().mapToGlobal(position))

    def refresh_data(self):
        """Load entries from DB with filters applied."""
        self._entries.clear()
        self.model.removeRows(0, self.model.rowCount())

        jtype = self.combo_journal_type.currentData()
        start = self.date_from.date().toPyDate()
        end = self.date_to.date().toPyDate()
        search_text = self.edit_search.text().strip() or None

        try:
            entries = self.service.get_journal_entries(
                journal_type=jtype,
                start_date=start,
                end_date=end,
                search=search_text,
            )
            self._entries = entries

            for entry in entries:
                self._add_entry_to_model(entry)

            self._update_stats()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки журнала: {e}")

    def _add_entry_to_model(self, entry: dict):
        row = []
        for col_name, _, _ in self.COLUMNS:
            if col_name == 'order_date':
                val = entry.get('order_date')
                text = val.strftime('%d.%m.%Y') if val else ''
            else:
                text = str(entry.get(col_name) or '')
            item = QStandardItem(text)
            item.setEditable(False)
            item.setData(entry['id'], Qt.UserRole)

            # Highlight today / last week
            od = entry.get('order_date')
            if od:
                delta = (date.today() - od).days
                if delta == 0:
                    item.setBackground(QBrush(QColor(200, 255, 200)))
                elif 0 < delta <= 7:
                    item.setBackground(QBrush(QColor(255, 255, 200)))
            row.append(item)
        self.model.appendRow(row)

    def _update_stats(self):
        count = len(self._entries)
        self.stats_label.setText(f"Всего записей: {count}")

    def _add_entry(self):
        """Open dialog to add new entry."""
        dialog = JournalEntryDialog(parent=self, service=self.service)
        if dialog.exec_():
            data = dialog.get_data()
            try:
                self.service.register_order(**data)
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить запись: {e}")

    def _edit_selected(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            QMessageBox.information(self, "Информация", "Выберите запись для редактирования")
            return

        # Find entry dict
        entry_dict = None
        for e in self._entries:
            if e['id'] == entry_id:
                entry_dict = e
                break
        if not entry_dict:
            return

        dialog = JournalEntryDialog(parent=self, service=self.service, entry=entry_dict)
        if dialog.exec_():
            data = dialog.get_data()
            try:
                self.service.update_order_entry(entry_id, **data)
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось обновить запись: {e}")

    def _delete_selected(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            QMessageBox.information(self, "Информация", "Выберите запись для удаления")
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить эту запись из журнала?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                if not self.service.delete_order_entry(entry_id):
                    QMessageBox.warning(
                        self, "Предупреждение",
                        "Не удалось удалить запись (возможно, связан документ)"
                    )
                else:
                    self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка удаления: {e}")

    def _export_excel(self):
        jtype = self.combo_journal_type.currentData()
        start = self.date_from.date().toPyDate()
        end = self.date_to.date().toPyDate()
        search_text = self.edit_search.text().strip() or None

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        type_label = ORDER_TYPE_LABELS.get(jtype, 'Журнал')
        filename = f"Журнал_{type_label.replace(' ', '_')}_{timestamp}.xlsx"

        from PyQt5.QtWidgets import QFileDialog
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в Excel", filename, "Excel Files (*.xlsx)"
        )
        if not output_path:
            return

        try:
            success = self.service.export_journal_to_excel(
                journal_type=jtype,
                output_path=output_path,
                start_date=start,
                end_date=end,
                search=search_text,
            )
            if success:
                QMessageBox.information(self, "Успех", f"Журнал экспортирован:\n{output_path}")
            else:
                QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {e}")

    def _open_document(self):
        """Open document file for selected entry."""
        entry_id = self._get_selected_id()
        if entry_id is None:
            return

        entry_dict = None
        for e in self._entries:
            if e['id'] == entry_id:
                entry_dict = e
                break
        if not entry_dict:
            return

        doc_path = entry_dict.get('document_path')
        if not doc_path:
            QMessageBox.information(self, "Информация", "Документ не привязан к этой записи")
            return

        from pathlib import Path
        p = Path(doc_path)
        if not p.exists():
            QMessageBox.warning(self, "Предупреждение", f"Файл не найден:\n{doc_path}")
            return

        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', str(p)])
            elif sys.platform == 'win32':
                subprocess.run(['start', '', str(p)], shell=True)
            else:
                subprocess.run(['xdg-open', str(p)])
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть файл: {e}")

    def _get_selected_id(self) -> Optional[int]:
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            proxy_index = indexes[0]
            source_index = self.proxy_model.mapToSource(proxy_index)
            item = self.model.item(source_index.row(), 0)
            if item:
                return item.data(Qt.UserRole)
        return None
