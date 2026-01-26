"""
Dialog for confirming contract generation parameters.
"""

from __future__ import annotations

from datetime import date
from typing import Dict

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QDateEdit,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QMessageBox,
)


class ContractCreateDialog(QDialog):
    def __init__(self, parent=None, listeners_count: int = 0, default_date: date | None = None):
        super().__init__(parent)
        self.listeners_count = listeners_count
        self.default_date = default_date or date.today()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Создание договоров")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"Будет создано договоров: {self.listeners_count}"))

        form = QFormLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate(self.default_date.year, self.default_date.month, self.default_date.day))
        form.addRow("Дата договора:", self.date_edit)

        self.edit_sum = QLineEdit()
        self.edit_sum.setPlaceholderText("Например: 25 000 руб.")
        form.addRow("Сумма:", self.edit_sum)

        self.edit_payment = QLineEdit()
        self.edit_payment.setPlaceholderText("Например: Безналичный расчет")
        form.addRow("Тип оплаты:", self.edit_payment)

        self.edit_notes = QTextEdit()
        self.edit_notes.setMaximumHeight(70)
        form.addRow("Примечания:", self.edit_notes)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_ok = QPushButton("Создать")
        self.btn_ok.clicked.connect(self._on_accept)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _on_accept(self):
        if not self.date_edit.date().isValid():
            QMessageBox.warning(self, "Ошибка", "Укажите корректную дату договора")
            return
        self.accept()

    def get_data(self) -> Dict:
        qd = self.date_edit.date()
        cdate = date(qd.year(), qd.month(), qd.day())
        return {
            "contract_date": cdate,
            "contract_sum": self.edit_sum.text().strip() or None,
            "payment_type": self.edit_payment.text().strip() or None,
            "notes": self.edit_notes.toPlainText().strip() or None,
        }
