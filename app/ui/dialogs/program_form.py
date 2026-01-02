"""
Program form dialog for adding/editing training programs.
"""

from datetime import datetime, date
from typing import Dict, Optional, Any

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QDateEdit, QPushButton,
    QLabel, QGroupBox, QMessageBox, QCheckBox
)

from ...database.models import Program


class ProgramFormDialog(QDialog):
    """
    Dialog for adding or editing a training program.
    """
    
    # Dropdown values
    EDUCATION_FORMS = [
        "",
        "очная",
        "заочная",
        "очно-заочная"
    ]
    
    TRAINING_BASIS = [
        "",
        "государственный контракт",
        "договор"
    ]
    
    EDUCATION_FORMATS = [
        "",
        "с применением электронного обучения",
        "с применением дистанционных образовательных технологий",
        "с применением электронного обучения и дистанционных образовательных технологий"
    ]
    
    def __init__(
        self, 
        parent=None, 
        program: Optional[Program] = None
    ):
        super().__init__(parent)
        
        self.program = program
        self.is_edit_mode = program is not None
        
        self._setup_ui()
        
        if self.is_edit_mode:
            self._load_data()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        title = "Редактирование программы" if self.is_edit_mode else "Добавление программы"
        self.setWindowTitle(title)
        self.setMinimumWidth(600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Program name group
        name_group = QGroupBox("Наименование")
        name_layout = QFormLayout(name_group)
        
        self.edit_program_name = QTextEdit()
        self.edit_program_name.setMaximumHeight(80)
        self.edit_program_name.setPlaceholderText("Полное наименование программы")
        name_layout.addRow("Наименование *:", self.edit_program_name)
        
        self.edit_short_name = QLineEdit()
        self.edit_short_name.setPlaceholderText("Краткое наименование")
        name_layout.addRow("Краткое название:", self.edit_short_name)
        
        layout.addWidget(name_group)
        
        # Program details group
        details_group = QGroupBox("Параметры программы")
        details_layout = QFormLayout(details_group)
        
        # Training basis (editable combobox)
        self.combo_training_basis = QComboBox()
        self.combo_training_basis.setEditable(True)
        self.combo_training_basis.addItems(self.TRAINING_BASIS)
        details_layout.addRow("Основание:", self.combo_training_basis)
        
        # Training period
        self.edit_training_period = QLineEdit()
        self.edit_training_period.setPlaceholderText("Например: 01.01.2026 - 31.01.2026")
        details_layout.addRow("Период обучения:", self.edit_training_period)
        
        # Program volume
        self.edit_program_volume = QLineEdit()
        self.edit_program_volume.setPlaceholderText("Например: 72 часа")
        details_layout.addRow("Объем программы:", self.edit_program_volume)
        
        # Education form
        self.combo_education_form = QComboBox()
        self.combo_education_form.addItems(self.EDUCATION_FORMS)
        details_layout.addRow("Форма обучения:", self.combo_education_form)
        
        # Education format
        self.combo_education_format = QComboBox()
        self.combo_education_format.addItems(self.EDUCATION_FORMATS)
        details_layout.addRow("Формат обучения:", self.combo_education_format)
        
        # Listener category
        self.edit_listener_category = QLineEdit()
        self.edit_listener_category.setPlaceholderText("Категория слушателей")
        details_layout.addRow("Категория:", self.edit_listener_category)
        
        # Expulsion date
        date_layout = QHBoxLayout()
        
        self.date_expulsion = QDateEdit()
        self.date_expulsion.setCalendarPopup(True)
        self.date_expulsion.setDisplayFormat("dd.MM.yyyy")
        self.date_expulsion.setDate(QDate.currentDate())
        
        self.check_no_date = QCheckBox("Не указана")
        self.check_no_date.setChecked(True)
        self.check_no_date.stateChanged.connect(self._on_date_checkbox_changed)
        
        date_layout.addWidget(self.date_expulsion)
        date_layout.addWidget(self.check_no_date)
        date_layout.addStretch()
        
        details_layout.addRow("Дата отчисления:", date_layout)
        
        # Initially disable date field
        self.date_expulsion.setEnabled(False)
        
        layout.addWidget(details_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._on_save)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_save)
        button_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(button_layout)
        
        # Required fields label
        required_label = QLabel("* - обязательные поля")
        required_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(required_label)
    
    def _on_date_checkbox_changed(self, state):
        """Handle date checkbox state change."""
        self.date_expulsion.setEnabled(state == Qt.Unchecked)
    
    def _load_data(self):
        """Load existing program data into form."""
        if not self.program:
            return
        
        self.edit_program_name.setPlainText(self.program.program_name or '')
        self.edit_short_name.setText(self.program.program_short_name or '')
        
        # Set training basis
        if self.program.training_basis:
            index = self.combo_training_basis.findText(self.program.training_basis)
            if index >= 0:
                self.combo_training_basis.setCurrentIndex(index)
            else:
                self.combo_training_basis.setEditText(self.program.training_basis)
        
        self.edit_training_period.setText(self.program.training_period or '')
        self.edit_program_volume.setText(self.program.program_volume or '')
        
        # Set education form
        if self.program.education_form:
            index = self.combo_education_form.findText(self.program.education_form)
            if index >= 0:
                self.combo_education_form.setCurrentIndex(index)
        
        # Set education format
        if self.program.education_format:
            index = self.combo_education_format.findText(self.program.education_format)
            if index >= 0:
                self.combo_education_format.setCurrentIndex(index)
        
        self.edit_listener_category.setText(self.program.listener_category or '')
        
        # Set expulsion date
        if self.program.expulsion_date:
            self.check_no_date.setChecked(False)
            self.date_expulsion.setEnabled(True)
            qdate = QDate(
                self.program.expulsion_date.year,
                self.program.expulsion_date.month,
                self.program.expulsion_date.day
            )
            self.date_expulsion.setDate(qdate)
        else:
            self.check_no_date.setChecked(True)
    
    def _validate(self) -> bool:
        """Validate form data."""
        if not self.edit_program_name.toPlainText().strip():
            QMessageBox.warning(
                self, "Ошибка валидации",
                "Наименование программы обязательно для заполнения"
            )
            self.edit_program_name.setFocus()
            return False
        
        return True
    
    def _on_save(self):
        """Handle save button click."""
        if self._validate():
            self.accept()
    
    def get_data(self) -> Dict[str, Any]:
        """Get form data as dictionary."""
        # Get expulsion date
        expulsion_date = None
        if not self.check_no_date.isChecked():
            qdate = self.date_expulsion.date()
            expulsion_date = date(qdate.year(), qdate.month(), qdate.day())
        
        data = {
            'program_name': self.edit_program_name.toPlainText().strip(),
            'program_short_name': self.edit_short_name.text().strip() or None,
            'training_basis': self.combo_training_basis.currentText().strip() or None,
            'training_period': self.edit_training_period.text().strip() or None,
            'program_volume': self.edit_program_volume.text().strip() or None,
            'education_form': self.combo_education_form.currentText() or None,
            'education_format': self.combo_education_format.currentText() or None,
            'listener_category': self.edit_listener_category.text().strip() or None,
            'expulsion_date': expulsion_date,
        }
        
        return data
