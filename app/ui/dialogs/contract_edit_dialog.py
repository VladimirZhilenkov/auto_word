"""
Dialog for editing/regenerating contract.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Optional

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
    QComboBox,
    QGroupBox,
)


class ContractEditDialog(QDialog):
    """Dialog to edit/regenerate a contract with new parameters."""

    def __init__(
        self,
        parent=None,
        contract_data: Optional[Dict] = None,
        templates: Optional[list] = None,
        current_template: Optional[str] = None,
    ):
        super().__init__(parent)
        self.contract_data = contract_data or {}
        self.templates = templates or []
        self.current_template = current_template
        self._regenerate = False
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Редактирование договора")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        # Contract info (read-only)
        info_group = QGroupBox("Информация о договоре")
        info_layout = QFormLayout(info_group)

        self.lbl_number = QLabel(str(self.contract_data.get('contract_number', '')))
        self.lbl_number.setStyleSheet("font-weight: bold;")
        info_layout.addRow("Номер договора:", self.lbl_number)

        self.lbl_listener = QLabel(self.contract_data.get('listener_full_name', ''))
        info_layout.addRow("Слушатель:", self.lbl_listener)

        self.lbl_program = QLabel(self.contract_data.get('program_name', ''))
        info_layout.addRow("Программа:", self.lbl_program)

        layout.addWidget(info_group)

        # Editable fields
        edit_group = QGroupBox("Редактируемые параметры")
        edit_layout = QFormLayout(edit_group)

        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        contract_date = self.contract_data.get('contract_date')
        if isinstance(contract_date, date):
            self.date_edit.setDate(QDate(contract_date.year, contract_date.month, contract_date.day))
        else:
            self.date_edit.setDate(QDate.currentDate())
        edit_layout.addRow("Дата договора:", self.date_edit)

        # Sum
        self.edit_sum = QLineEdit()
        self.edit_sum.setText(self.contract_data.get('contract_sum') or '')
        self.edit_sum.setPlaceholderText("Например: 25 000 руб.")
        edit_layout.addRow("Сумма:", self.edit_sum)

        # Payment type
        self.edit_payment = QLineEdit()
        self.edit_payment.setText(self.contract_data.get('payment_type') or '')
        self.edit_payment.setPlaceholderText("Например: Безналичный расчет")
        edit_layout.addRow("Тип оплаты:", self.edit_payment)

        # Notes
        self.edit_notes = QTextEdit()
        self.edit_notes.setMaximumHeight(70)
        self.edit_notes.setPlainText(self.contract_data.get('notes') or '')
        edit_layout.addRow("Примечания:", self.edit_notes)

        layout.addWidget(edit_group)

        # Template selection for regeneration
        regen_group = QGroupBox("Пересоздание документа")
        regen_layout = QFormLayout(regen_group)

        self.combo_template = QComboBox()
        if self.templates:
            for tpl in self.templates:
                self.combo_template.addItem(tpl, tpl)
            # Try to select current template
            if self.current_template:
                idx = self.combo_template.findData(self.current_template)
                if idx >= 0:
                    self.combo_template.setCurrentIndex(idx)
        else:
            self.combo_template.addItem("-- Нет шаблонов --", None)
        regen_layout.addRow("Шаблон:", self.combo_template)

        self.lbl_regen_hint = QLabel(
            "Нажмите 'Пересоздать договор' для генерации нового документа\n"
            "с текущими параметрами (тем же номером, но новой суммой/датой)"
        )
        self.lbl_regen_hint.setStyleSheet("color: gray; font-size: 11px;")
        regen_layout.addRow("", self.lbl_regen_hint)

        layout.addWidget(regen_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_regenerate = QPushButton("🔄 Пересоздать договор")
        self.btn_regenerate.setToolTip("Создать новый документ Word с текущими параметрами")
        self.btn_regenerate.clicked.connect(self._on_regenerate)

        self.btn_save = QPushButton("💾 Сохранить изменения")
        self.btn_save.setToolTip("Сохранить изменения в журнале (без генерации документа)")
        self.btn_save.clicked.connect(self._on_save)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_regenerate)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _on_regenerate(self):
        """User wants to regenerate the document."""
        template = self.combo_template.currentData()
        if not template:
            QMessageBox.warning(self, "Предупреждение", "Выберите шаблон для генерации договора")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Создать новый документ договора с текущими параметрами?\n\n"
            "Старый документ будет заменён новым.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self._regenerate = True
            self.accept()

    def _on_save(self):
        """Save changes without regenerating document."""
        self._regenerate = False
        self.accept()

    def should_regenerate(self) -> bool:
        """Returns True if user clicked 'Regenerate'."""
        return self._regenerate

    def get_template(self) -> Optional[str]:
        """Get selected template name."""
        return self.combo_template.currentData()

    def get_data(self) -> Dict:
        """Get edited contract data."""
        qd = self.date_edit.date()
        cdate = date(qd.year(), qd.month(), qd.day())
        return {
            "contract_date": cdate,
            "contract_sum": self.edit_sum.text().strip() or None,
            "payment_type": self.edit_payment.text().strip() or None,
            "notes": self.edit_notes.toPlainText().strip() or None,
        }
