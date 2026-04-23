"""
Journals tab - view and manage Order Journal and Contract Journal entries.
"""

from datetime import date
from typing import List, Optional
import subprocess
import sys

from PyQt5.QtCore import Qt, QSortFilterProxyModel, QDate
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QLabel, QMessageBox, QHeaderView, QAbstractItemView,
    QMenu, QAction, QComboBox, QDateEdit, QLineEdit, QFormLayout, QGroupBox,
    QTabWidget, QListWidget, QListWidgetItem, QCheckBox, QFileDialog
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor

from ..database.connection import DatabaseSession
from ..database.models import Program, ProgramListener, Listener
from .dialogs.journal_entry_dialog import JournalEntryDialog
from .dialogs.order_create_dialog import OrderCreateDialog
from .dialogs.order_edit_dialog import OrderEditDialog
from .dialogs.contract_create_dialog import ContractCreateDialog
from .dialogs.contract_edit_dialog import ContractEditDialog
from ..services.order_journal_service import OrderJournalService, ORDER_TYPE_LABELS
from ..services.contract_journal_service import ContractJournalService
from .statement_journal_subtab import StatementJournalSubTab


class JournalsTab(QWidget):
    """Tab widget containing sub-tabs for Order Journal and Contract Journal."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.order_tab = OrderJournalSubTab(parent=self)
        self.contract_tab = ContractJournalSubTab(parent=self)
        self.vedomost_ia_tab = StatementJournalSubTab(kind='vedomost_ia', parent=self)
        self.vedomost_pa_tab = StatementJournalSubTab(kind='vedomost_pa', parent=self)
        self.protokol_ia_tab = StatementJournalSubTab(kind='protokol_ia', parent=self)

        self.tabs.addTab(self.order_tab, "Журнал приказов по ЛС")
        self.tabs.addTab(self.contract_tab, "Журнал договоров")
        self.tabs.addTab(self.vedomost_ia_tab, "Ведомости ИА")
        self.tabs.addTab(self.vedomost_pa_tab, "Ведомости ПА")
        self.tabs.addTab(self.protokol_ia_tab, "Протоколы ИА")

        layout.addWidget(self.tabs)

    def refresh_data(self):
        self.order_tab.refresh_data()
        self.contract_tab.refresh_data()
        self.vedomost_ia_tab.refresh_data()
        self.vedomost_pa_tab.refresh_data()
        self.protokol_ia_tab.refresh_data()


class OrderJournalSubTab(QWidget):
    """Sub-tab for order journal management."""

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

        # Journal type combobox (default: show all)
        self.combo_journal_type = QComboBox()
        self.combo_journal_type.addItem("Все журналы", None)
        for key, label in ORDER_TYPE_LABELS.items():
            self.combo_journal_type.addItem(label, key)

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
        self.table_view.doubleClicked.connect(self._edit_order)

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

        self.btn_create_order = QPushButton("📝 Создать приказ")
        self.btn_create_order.setStyleSheet("font-weight: bold;")
        self.btn_create_order.clicked.connect(self._create_order)

        self.btn_add = QPushButton("Добавить запись вручную")
        self.btn_add.clicked.connect(self._add_entry)

        self.btn_edit_order = QPushButton("✏️ Редактировать приказ")
        self.btn_edit_order.setStyleSheet("font-weight: bold;")
        self.btn_edit_order.clicked.connect(self._edit_order)

        self.btn_edit = QPushButton("Редактировать запись")
        self.btn_edit.clicked.connect(self._edit_selected)

        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete_selected)

        self.btn_export = QPushButton("Экспорт в Excel")
        self.btn_export.clicked.connect(self._export_excel)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh_data)

        self.stats_label = QLabel("Всего записей: 0")

        button_layout.addWidget(self.btn_create_order)
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit_order)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addWidget(self.btn_export)
        button_layout.addStretch()
        button_layout.addWidget(self.stats_label)
        button_layout.addWidget(self.btn_refresh)

        layout.addLayout(button_layout)

    def _setup_context_menu(self):
        self.context_menu = QMenu(self)

        action_edit_order = QAction("✏️ Редактировать приказ", self)
        action_edit_order.triggered.connect(self._edit_order)
        self.context_menu.addAction(action_edit_order)

        action_edit = QAction("Редактировать запись", self)
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

    def _create_order(self):
        """Open dialog to create a new order with Word document generation."""
        dialog = OrderCreateDialog(parent=self)
        dialog.exec_()
        # Refresh after dialog closes (even if cancelled, in case order was created)
        self.refresh_data()

    def _edit_order(self):
        """Open full order editing dialog with template preview and listener management."""
        entry_id = self._get_selected_id()
        if entry_id is None:
            QMessageBox.information(self, "Информация", "Выберите приказ для редактирования")
            return

        entry_dict = None
        for e in self._entries:
            if e['id'] == entry_id:
                entry_dict = e
                break
        if not entry_dict:
            return

        dialog = OrderEditDialog(parent=self, entry=entry_dict)
        dialog.exec_()
        self.refresh_data()

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
        type_label = ORDER_TYPE_LABELS.get(jtype, 'Журнал')
        filename = f"Журнал_приказов_директора_по_личному_составу_слушателей_{type_label.replace(' ', '_')}.xlsx"

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


# ==========================================================================
# Contract Journal Sub-Tab
# ==========================================================================


class ContractJournalSubTab(QWidget):
    """Sub-tab for contract journal management."""

    COLUMNS = [
        ('contract_number', '№ дог.', 70),
        ('contract_date', 'Дата', 100),
        ('listener_full_name', 'ФИО слушателя', 200),
        ('program_name', 'Программа', 250),
        ('contract_sum', 'Сумма', 100),
        ('notes', 'Примечания', 150),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = ContractJournalService()
        self._contracts: List = []
        self._program_listeners: List = []
        self._setup_ui()
        self._setup_context_menu()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ------------- Upper: Program Selection + Listeners -----------------
        top_group = QGroupBox("Создание договоров")
        top_layout = QVBoxLayout(top_group)

        # Program selection
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

        # Template selection
        tpl_layout = QHBoxLayout()
        tpl_layout.addWidget(QLabel("Шаблон договора:"))
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
        self.btn_create_contracts = QPushButton("🆕 Создать договоры")
        self.btn_create_contracts.clicked.connect(self._create_contracts)

        list_btn_layout.addWidget(self.btn_select_all)
        list_btn_layout.addWidget(self.btn_deselect_all)
        list_btn_layout.addStretch()
        list_btn_layout.addWidget(self.btn_create_contracts)

        top_layout.addLayout(list_btn_layout)
        layout.addWidget(top_group)

        # ------------- Middle: Journal Table + Search -----------------------
        journal_group = QGroupBox("Журнал договоров")
        journal_layout = QVBoxLayout(journal_group)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск:"))
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Номер, ФИО или программа...")
        self.edit_search.setClearButtonEnabled(True)
        self.edit_search.textChanged.connect(self._filter_contracts)
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
        self.btn_export = QPushButton("Экспорт в Excel")
        self.btn_export.clicked.connect(self._export_excel)
        self.btn_open_doc = QPushButton("Открыть договор")
        self.btn_open_doc.clicked.connect(self._open_document)
        self.btn_edit = QPushButton("Редактировать")
        self.btn_edit.clicked.connect(self._edit_contract)
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self._delete_selected)
        self.stats_label = QLabel("Всего: 0")
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh_data)

        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_open_doc)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(self.stats_label)
        btn_layout.addWidget(self.btn_refresh)

        journal_layout.addLayout(btn_layout)
        layout.addWidget(journal_group, stretch=1)

    def _setup_context_menu(self):
        self.context_menu = QMenu(self)
        act_open = QAction("Открыть договор", self)
        act_open.triggered.connect(self._open_document)
        self.context_menu.addAction(act_open)

        act_edit = QAction("Редактировать", self)
        act_edit.triggered.connect(self._edit_contract)
        self.context_menu.addAction(act_edit)

        self.context_menu.addSeparator()

        act_delete = QAction("Удалить", self)
        act_delete.triggered.connect(self._delete_selected)
        self.context_menu.addAction(act_delete)

    def _show_context_menu(self, pos):
        if self.table_view.selectionModel().hasSelection():
            self.context_menu.exec_(self.table_view.viewport().mapToGlobal(pos))

    def refresh_data(self):
        self._load_programs()
        self._load_templates()
        self._load_contracts()

    def _load_programs(self):
        self.combo_program.clear()
        self.combo_program.addItem("-- Выберите программу --", None)
        try:
            with DatabaseSession() as session:
                for p in session.query(Program).order_by(Program.program_name):
                    label = p.program_short_name or p.program_name[:60]
                    self.combo_program.addItem(label, p.id)
        except Exception:
            pass

    def _load_templates(self):
        self.combo_template.clear()
        templates = self.service.get_available_templates()
        if not templates:
            self.combo_template.addItem("-- Нет шаблонов --", None)
        else:
            for tpl in templates:
                self.combo_template.addItem(tpl, tpl)

    def _open_templates_folder(self):
        import subprocess
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

    def _create_contracts(self):
        selected = self.listener_list.selectedItems()
        if not selected:
            QMessageBox.information(self, "Информация", "Выберите слушателей для создания договоров")
            return

        template_name = self.combo_template.currentData()
        if not template_name:
            QMessageBox.warning(self, "Предупреждение", "Добавьте шаблон договора в папку шаблонов")
            return

        dialog = ContractCreateDialog(parent=self, listeners_count=len(selected))
        if not dialog.exec_():
            return

        data = dialog.get_data()
        prog_id = self.combo_program.currentData()
        listener_ids = [item.data(Qt.UserRole) for item in selected]

        try:
            nums = self.service.create_contracts_batch(
                listener_ids=listener_ids,
                program_id=prog_id,
                contract_date=data["contract_date"],
                template_name=template_name,
                contract_sum=data.get("contract_sum"),
                payment_type=data.get("payment_type"),
                notes=data.get("notes"),
            )
            QMessageBox.information(self, "Готово", f"Создано договоров: {len(nums)}")
            self.refresh_data()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать договоры: {exc}")

    def _load_contracts(self):
        self._contracts.clear()
        self.model.removeRows(0, self.model.rowCount())

        try:
            entries = self.service.get_contracts()
            self._contracts = entries
            for c in entries:
                self._add_row(c)
            self._update_stats()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки журнала: {exc}")

    def _add_row(self, entry: dict):
        row = []
        for col_name, _, _ in self.COLUMNS:
            val = entry.get(col_name)
            if col_name == 'contract_date' and val:
                text = val.strftime('%d.%m.%Y')
            else:
                text = str(val or '')
            item = QStandardItem(text)
            item.setEditable(False)
            item.setData(entry['id'], Qt.UserRole)
            row.append(item)
        self.model.appendRow(row)

    def _update_stats(self):
        self.stats_label.setText(f"Всего: {len(self._contracts)}")

    def _filter_contracts(self, text: str):
        self.proxy_model.setFilterRegularExpression(text)

    def _export_excel(self):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"Журнал_договоров_{timestamp}.xlsx"

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в Excel", filename, "Excel Files (*.xlsx)"
        )
        if not output_path:
            return

        try:
            ok = self.service.export_to_excel(output_path, filters={})
            if ok:
                QMessageBox.information(self, "Успех", f"Журнал экспортирован:\n{output_path}")
            else:
                QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {exc}")

    def _open_document(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            return

        entry = next((c for c in self._contracts if c['id'] == entry_id), None)
        if not entry:
            return

        doc_path = entry.get('document_path')
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
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть файл: {exc}")

    def _edit_contract(self):
        """Edit selected contract - change date, sum, regenerate document."""
        entry_id = self._get_selected_id()
        if entry_id is None:
            QMessageBox.information(self, "Информация", "Выберите договор для редактирования")
            return

        # Find contract data
        contract = next((c for c in self._contracts if c['id'] == entry_id), None)
        if not contract:
            QMessageBox.warning(self, "Ошибка", "Договор не найден")
            return

        # Get available templates
        templates = self.service.get_available_templates()

        # Try to detect current template from document path
        current_template = None
        doc_path = contract.get('document_path')
        if doc_path and templates:
            # Just use first template as default
            current_template = templates[0] if templates else None

        # Show edit dialog
        dialog = ContractEditDialog(
            parent=self,
            contract_data=contract,
            templates=templates,
            current_template=current_template,
        )

        if dialog.exec_():
            data = dialog.get_data()

            if dialog.should_regenerate():
                # Regenerate document with new parameters
                template = dialog.get_template()
                if not template:
                    QMessageBox.warning(self, "Ошибка", "Шаблон не выбран")
                    return

                try:
                    new_path = self.service.regenerate_contract(
                        contract_id=entry_id,
                        template_name=template,
                        contract_date=data['contract_date'],
                        contract_sum=data.get('contract_sum'),
                        payment_type=data.get('payment_type'),
                        notes=data.get('notes'),
                    )
                    QMessageBox.information(
                        self, "Готово",
                        f"Договор пересоздан:\n{new_path}"
                    )
                    self.refresh_data()
                except Exception as exc:
                    QMessageBox.critical(self, "Ошибка", f"Ошибка пересоздания договора: {exc}")
            else:
                # Just update journal entry without regenerating document
                try:
                    self.service.update_contract(
                        entry_id,
                        contract_date=data['contract_date'],
                        contract_sum=data.get('contract_sum'),
                        payment_type=data.get('payment_type'),
                        notes=data.get('notes'),
                    )
                    QMessageBox.information(self, "Готово", "Изменения сохранены")
                    self.refresh_data()
                except Exception as exc:
                    QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {exc}")

    def _delete_selected(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            QMessageBox.information(self, "Информация", "Выберите запись для удаления")
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить эту запись из журнала договоров?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                self.service.delete_contract(entry_id)
                self.refresh_data()
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", f"Ошибка удаления: {exc}")

    def _get_selected_id(self) -> Optional[int]:
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            proxy_idx = indexes[0]
            src_idx = self.proxy_model.mapToSource(proxy_idx)
            item = self.model.item(src_idx.row(), 0)
            if item:
                return item.data(Qt.UserRole)
        return None
