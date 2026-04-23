"""
Generic sub-tab for statement journals (Ведомости ИА, Ведомости ПА, Протоколы ИА).

Mirrors the ContractJournalSubTab pattern: program + template + listener selection,
journal table with search, batch creation and document generation.
"""

from __future__ import annotations

import subprocess
import sys
from typing import List, Optional

from PyQt5.QtCore import Qt, QSortFilterProxyModel, QDate
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QLabel, QMessageBox, QAbstractItemView,
    QMenu, QAction, QComboBox, QDateEdit, QLineEdit, QGroupBox,
    QListWidget, QListWidgetItem,
)

from ..database.connection import DatabaseSession
from ..database.models import Program, ProgramListener, Listener
from ..services.statement_journal_service import StatementJournalService, STATEMENT_KINDS


class StatementJournalSubTab(QWidget):
    """Sub-tab for one kind of statement journal (vedomost_ia/vedomost_pa/protokol_ia)."""

    COLUMNS = [
        ('entry_number', '№', 60),
        ('entry_date', 'Дата', 100),
        ('listener_full_name', 'ФИО слушателя', 220),
        ('program_name', 'Программа', 260),
        ('notes', 'Примечания', 200),
    ]

    def __init__(self, kind: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.kind = kind
        self.config = STATEMENT_KINDS[kind]
        self.service = StatementJournalService(kind)
        self._entries: List = []
        self._program_listeners: List[int] = []
        self._setup_ui()
        self._setup_context_menu()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _setup_ui(self):
        layout = QVBoxLayout(self)

        top_group = QGroupBox(f"Создание: {self.config['label']}")
        top_layout = QVBoxLayout(top_group)

        prog_layout = QHBoxLayout()
        prog_layout.addWidget(QLabel("Программа:"))
        self.combo_program = QComboBox()
        self.combo_program.setMinimumWidth(350)
        prog_layout.addWidget(self.combo_program, stretch=1)

        self.btn_apply_program = QPushButton("Применить")
        self.btn_apply_program.clicked.connect(self._load_program_listeners)
        prog_layout.addWidget(self.btn_apply_program)

        self.btn_reset_program = QPushButton("Сбросить")
        self.btn_reset_program.clicked.connect(self._reset_program_selection)
        prog_layout.addWidget(self.btn_reset_program)
        top_layout.addLayout(prog_layout)

        tpl_layout = QHBoxLayout()
        tpl_layout.addWidget(QLabel("Шаблон:"))
        self.combo_template = QComboBox()
        self.combo_template.setMinimumWidth(300)
        tpl_layout.addWidget(self.combo_template, stretch=1)

        self.btn_open_templates_folder = QPushButton("📂 Папка шаблонов")
        self.btn_open_templates_folder.clicked.connect(self._open_templates_folder)
        tpl_layout.addWidget(self.btn_open_templates_folder)

        self.btn_refresh_templates = QPushButton("🔄")
        self.btn_refresh_templates.setMaximumWidth(40)
        self.btn_refresh_templates.setToolTip("Обновить список шаблонов")
        self.btn_refresh_templates.clicked.connect(self._load_templates)
        tpl_layout.addWidget(self.btn_refresh_templates)
        top_layout.addLayout(tpl_layout)

        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Дата:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(self.date_edit)

        date_layout.addWidget(QLabel("Примечания:"))
        self.edit_notes = QLineEdit()
        self.edit_notes.setPlaceholderText("(опционально)")
        date_layout.addWidget(self.edit_notes, stretch=1)
        top_layout.addLayout(date_layout)

        top_layout.addWidget(QLabel("Слушатели программы:"))
        self.listener_list = QListWidget()
        self.listener_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.listener_list.setMaximumHeight(140)
        top_layout.addWidget(self.listener_list)

        list_btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.clicked.connect(self._select_all_listeners)
        self.btn_deselect_all = QPushButton("Снять выделение")
        self.btn_deselect_all.clicked.connect(self._deselect_all_listeners)
        self.btn_create = QPushButton(f"🆕 Создать: {self.config['label']}")
        self.btn_create.clicked.connect(self._create_entries)

        list_btn_layout.addWidget(self.btn_select_all)
        list_btn_layout.addWidget(self.btn_deselect_all)
        list_btn_layout.addStretch()
        list_btn_layout.addWidget(self.btn_create)
        top_layout.addLayout(list_btn_layout)

        layout.addWidget(top_group)

        # Journal table
        journal_group = QGroupBox(f"Журнал: {self.config['label']}")
        journal_layout = QVBoxLayout(journal_group)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск:"))
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Номер, ФИО или программа...")
        self.edit_search.setClearButtonEnabled(True)
        self.edit_search.textChanged.connect(self._filter_entries)
        search_layout.addWidget(self.edit_search)
        journal_layout.addLayout(search_layout)

        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)
        self.table_view.doubleClicked.connect(self._open_document)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([col[1] for col in self.COLUMNS])

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)
        self.table_view.setModel(self.proxy_model)

        for i, (_, _, w) in enumerate(self.COLUMNS):
            self.table_view.setColumnWidth(i, w)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        journal_layout.addWidget(self.table_view)

        btn_layout = QHBoxLayout()
        self.btn_open_doc = QPushButton("Открыть документ")
        self.btn_open_doc.clicked.connect(self._open_document)
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete_selected)
        self.stats_label = QLabel("Всего: 0")
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh_data)

        btn_layout.addWidget(self.btn_open_doc)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(self.stats_label)
        btn_layout.addWidget(self.btn_refresh)
        journal_layout.addLayout(btn_layout)

        layout.addWidget(journal_group, stretch=1)

    def _setup_context_menu(self):
        self.context_menu = QMenu(self)
        act_open = QAction("Открыть документ", self)
        act_open.triggered.connect(self._open_document)
        self.context_menu.addAction(act_open)
        act_delete = QAction("Удалить", self)
        act_delete.triggered.connect(self._delete_selected)
        self.context_menu.addAction(act_delete)

    def _show_context_menu(self, pos):
        if self.table_view.selectionModel().hasSelection():
            self.context_menu.exec_(self.table_view.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def refresh_data(self):
        self._load_programs()
        self._load_templates()
        self._load_entries()

    def _load_programs(self):
        current = self.combo_program.currentData()
        self.combo_program.clear()
        self.combo_program.addItem("-- Выберите программу --", None)
        try:
            with DatabaseSession() as session:
                for p in session.query(Program).order_by(Program.program_name):
                    label = p.program_short_name or (p.program_name[:60] if p.program_name else '')
                    self.combo_program.addItem(label, p.id)
        except Exception:
            pass
        if current:
            idx = self.combo_program.findData(current)
            if idx >= 0:
                self.combo_program.setCurrentIndex(idx)

    def _load_templates(self):
        self.combo_template.clear()
        templates = self.service.get_available_templates()
        if not templates:
            self.combo_template.addItem("-- Нет шаблонов --", None)
        else:
            self.combo_template.addItem("-- Выберите шаблон --", None)
            for tpl in templates:
                self.combo_template.addItem(tpl, tpl)

    def _load_program_listeners(self):
        self.listener_list.clear()
        self._program_listeners.clear()
        prog_id = self.combo_program.currentData()
        if not prog_id:
            return
        try:
            with DatabaseSession() as session:
                assocs = session.query(ProgramListener).filter(
                    ProgramListener.program_id == prog_id
                ).order_by(ProgramListener.order_number).all()
                for a in assocs:
                    listener = session.query(Listener).get(a.listener_id)
                    if listener:
                        item = QListWidgetItem(listener.full_name)
                        item.setData(Qt.UserRole, listener.id)
                        self.listener_list.addItem(item)
                        self._program_listeners.append(listener.id)
        except Exception:
            pass

    def _reset_program_selection(self):
        self.combo_program.setCurrentIndex(0)
        self.listener_list.clear()
        self._program_listeners.clear()

    def _select_all_listeners(self):
        for i in range(self.listener_list.count()):
            self.listener_list.item(i).setSelected(True)

    def _deselect_all_listeners(self):
        self.listener_list.clearSelection()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _create_entries(self):
        selected = self.listener_list.selectedItems()
        if not selected:
            QMessageBox.information(self, "Информация", "Выберите слушателей")
            return

        template_name = self.combo_template.currentData()
        if not template_name:
            QMessageBox.warning(self, "Предупреждение", "Выберите шаблон")
            return

        prog_id = self.combo_program.currentData()
        listener_ids = [item.data(Qt.UserRole) for item in selected]
        qd = self.date_edit.date()
        from datetime import date as _date
        entry_date = _date(qd.year(), qd.month(), qd.day())
        notes = self.edit_notes.text().strip() or None

        try:
            created = self.service.create_batch(
                listener_ids=listener_ids,
                program_id=prog_id,
                entry_date=entry_date,
                template_name=template_name,
                notes=notes,
            )
            QMessageBox.information(self, "Готово", f"Создано записей: {len(created)}")
            self.refresh_data()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать записи: {exc}")

    def _load_entries(self):
        self._entries.clear()
        self.model.removeRows(0, self.model.rowCount())
        try:
            entries = self.service.get_entries()
            self._entries = entries
            for e in entries:
                self._add_row(e)
            self.stats_label.setText(f"Всего: {len(entries)}")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки журнала: {exc}")

    def _add_row(self, entry: dict):
        row = []
        for col_name, _, _ in self.COLUMNS:
            val = entry.get(col_name)
            if col_name == 'entry_date' and val:
                text = val.strftime('%d.%m.%Y')
            else:
                text = str(val or '')
            item = QStandardItem(text)
            item.setEditable(False)
            item.setData(entry['id'], Qt.UserRole)
            row.append(item)
        self.model.appendRow(row)

    def _filter_entries(self, text: str):
        self.proxy_model.setFilterRegularExpression(text)

    def _get_selected_id(self) -> Optional[int]:
        sel = self.table_view.selectionModel().selectedRows()
        if not sel:
            return None
        src_idx = self.proxy_model.mapToSource(sel[0])
        item = self.model.item(src_idx.row(), 0)
        return item.data(Qt.UserRole) if item else None

    def _open_document(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            return
        path = None
        for e in self._entries:
            if e['id'] == entry_id:
                path = e.get('document_path')
                break
        if not path:
            QMessageBox.information(self, "Информация", "У записи нет связанного документа")
            return
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', path])
            elif sys.platform == 'win32':
                import os
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.run(['xdg-open', path])
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть документ: {exc}")

    def _delete_selected(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            return
        reply = QMessageBox.question(
            self, "Удаление", "Удалить выбранную запись?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.service.delete_entry(entry_id)
            self.refresh_data()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить: {exc}")

    def _open_templates_folder(self):
        folder = self.service.templates_dir
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', str(folder)])
            elif sys.platform == 'win32':
                subprocess.run(['explorer', str(folder)])
            else:
                subprocess.run(['xdg-open', str(folder)])
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку: {exc}")
