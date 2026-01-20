"""
Dialog for manual adding/editing of Order Journal entries.
"""

from datetime import date
from typing import Dict, Optional

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QTextEdit, QDateEdit, QPushButton,
    QLabel, QMessageBox
)

from ...database.connection import DatabaseSession
from ...database.models import Program
from ...services.order_journal_service import OrderJournalService, ORDER_TYPE_LABELS, REVERSE_ORDER_TYPE_LABELS


class JournalEntryDialog(QDialog):
    """Manual add/edit dialog for Order Journal entries."""

    def __init__(
        self,
        parent=None,
        service: Optional[OrderJournalService] = None,
        entry: Optional[Dict] = None,
    ):
        super().__init__(parent)
        self.service = service or OrderJournalService()
        self.entry = entry  # dict or None
        self.is_edit_mode = entry is not None

        self._setup_ui()
        self._load_programs()
        self._load_initial()

    def _setup_ui(self):
        title = "Редактирование записи журнала" if self.is_edit_mode else "Добавление записи в журнал"
        self.setWindowTitle(title)
        self.setMinimumWidth(600)
        self.setModal(True)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Journal type
        self.combo_type = QComboBox()
        for key, label in ORDER_TYPE_LABELS.items():
            self.combo_type.addItem(label, key)
        self.combo_type.currentIndexChanged.connect(self._update_next_number_hint)
        form.addRow("Тип журнала:", self.combo_type)

        # Order number + hint
        number_layout = QVBoxLayout()
        self.edit_number = QLineEdit()
        self.edit_number.setPlaceholderText("Например: 25")
        number_layout.addWidget(self.edit_number)
        self.label_hint = QLabel("")
        self.label_hint.setStyleSheet("color: gray;")
        number_layout.addWidget(self.label_hint)
        form.addRow("Номер приказа:", number_layout)

        # Order date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Дата приказа:", self.date_edit)

        # Title
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("Краткое содержание приказа")
        form.addRow("Наименование:", self.edit_title)

        # Executor
        self.edit_executor = QLineEdit()
        self.edit_executor.setPlaceholderText("Ответственный исполнитель")
        form.addRow("Исполнитель:", self.edit_executor)

        # Program combobox
        self.combo_program = QComboBox()
        form.addRow("Программа:", self.combo_program)

        # Notes
        self.edit_notes = QTextEdit()
        self.edit_notes.setMaximumHeight(80)
        form.addRow("Примечание:", self.edit_notes)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _load_programs(self):
        """Load programs into combobox (with 'Без программы' option)."""
        self.combo_program.clear()
        self.combo_program.addItem("Без программы", None)
        try:
            with DatabaseSession() as session:
                programs = session.query(Program).order_by(Program.program_name).all()
                for p in programs:
                    label = p.program_short_name or p.program_name
                    self.combo_program.addItem(label, p.id)
        except Exception:
            pass

    def _load_initial(self):
        if self.is_edit_mode and self.entry:
            # Set values from entry
            jtype = self.entry.get('journal_type')
            idx = self.combo_type.findData(jtype)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)
            self.edit_number.setText(str(self.entry.get('order_number', '')))

            od: Optional[date] = self.entry.get('order_date')
            if od:
                self.date_edit.setDate(QDate(od.year, od.month, od.day))

            self.edit_title.setText(self.entry.get('title') or "")
            self.edit_executor.setText(self.entry.get('executor') or "")

            # Program selection
            pid = self.entry.get('program_id')
            pidx = self.combo_program.findData(pid)
            if pidx >= 0:
                self.combo_program.setCurrentIndex(pidx)

            self.edit_notes.setPlainText(self.entry.get('notes') or "")
        else:
            # New: pre-fill next number hint and value
            self._update_next_number_hint()
            next_num = self.service.get_next_order_number(self.combo_type.currentData())
            self.edit_number.setText(str(next_num))

    def _update_next_number_hint(self):
        jtype = self.combo_type.currentData()
        try:
            next_num = self.service.get_next_order_number(jtype)
            self.label_hint.setText(f"Следующий номер в журнале: №{next_num}")
        except Exception:
            self.label_hint.setText("")

    def _validate(self) -> bool:
        if not self.edit_title.text().strip():
            QMessageBox.warning(self, "Ошибка валидации", "Укажите наименование (краткое содержание)")
            return False
        num_text = self.edit_number.text().strip()
        if not num_text.isdigit():
            QMessageBox.warning(self, "Ошибка валидации", "Номер приказа должен быть числом")
            return False
        return True

    def _on_save(self):
        if not self._validate():
            return
        # Let caller perform create/update using get_data()
        self.accept()

    def get_data(self) -> Dict:
        jtype = self.combo_type.currentData()
        num = int(self.edit_number.text().strip())
        qd = self.date_edit.date()
        od = date(qd.year(), qd.month(), qd.day())
        pid = self.combo_program.currentData()
        pname = None
        # Resolve program name to store history
        if pid:
            try:
                with DatabaseSession() as session:
                    p = session.query(Program).get(pid)
                    if p:
                        pname = p.program_short_name or p.program_name
            except Exception:
                pass
        return {
            'journal_type': jtype,
            'order_number': num,
            'order_date': od,
            'title': self.edit_title.text().strip(),
            'executor': self.edit_executor.text().strip(),
            'program_id': pid,
            'program_name': pname,
            'notes': self.edit_notes.toPlainText().strip() or None,
        }
