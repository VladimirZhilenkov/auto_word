"""
Listener form dialog for adding/editing listeners.
"""

from typing import Dict, Optional, Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QGroupBox,
    QMessageBox
)

from ...database.models import Listener


class ListenerFormDialog(QDialog):
    """
    Dialog for adding or editing a listener.
    """
    
    def __init__(
        self, 
        parent=None, 
        listener: Optional[Listener] = None
    ):
        super().__init__(parent)
        
        self.listener = listener
        self.is_edit_mode = listener is not None
        
        self._setup_ui()
        
        if self.is_edit_mode:
            self._load_data()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        title = "Редактирование слушателя" if self.is_edit_mode else "Добавление слушателя"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Name group
        name_group = QGroupBox("ФИО")
        name_layout = QFormLayout(name_group)
        
        self.edit_last_name = QLineEdit()
        self.edit_last_name.setPlaceholderText("Введите фамилию")
        name_layout.addRow("Фамилия *:", self.edit_last_name)
        
        self.edit_first_name = QLineEdit()
        self.edit_first_name.setPlaceholderText("Введите имя")
        name_layout.addRow("Имя *:", self.edit_first_name)
        
        self.edit_middle_name = QLineEdit()
        self.edit_middle_name.setPlaceholderText("Введите отчество")
        name_layout.addRow("Отчество:", self.edit_middle_name)
        
        layout.addWidget(name_group)
        
        # Work info group
        work_group = QGroupBox("Рабочая информация")
        work_layout = QFormLayout(work_group)
        
        self.edit_position = QLineEdit()
        self.edit_position.setPlaceholderText("Введите должность")
        work_layout.addRow("Должность:", self.edit_position)
        
        self.edit_workplace = QLineEdit()
        self.edit_workplace.setPlaceholderText("Введите наименование суда/место работы")
        work_layout.addRow("Место работы:", self.edit_workplace)
        
        self.edit_region = QLineEdit()
        self.edit_region.setPlaceholderText("Введите субъект РФ")
        work_layout.addRow("Субъект РФ:", self.edit_region)
        
        layout.addWidget(work_group)
        
        # Notes group
        notes_group = QGroupBox("Примечания")
        notes_layout = QVBoxLayout(notes_group)
        
        self.edit_notes = QTextEdit()
        self.edit_notes.setMaximumHeight(80)
        self.edit_notes.setPlaceholderText("Дополнительная информация...")
        notes_layout.addWidget(self.edit_notes)
        
        layout.addWidget(notes_group)
        
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
    
    def _load_data(self):
        """Load existing listener data into form."""
        if not self.listener:
            return
        
        self.edit_last_name.setText(self.listener.last_name or '')
        self.edit_first_name.setText(self.listener.first_name or '')
        self.edit_middle_name.setText(self.listener.middle_name or '')
        self.edit_position.setText(self.listener.position or '')
        self.edit_workplace.setText(self.listener.workplace or '')
        self.edit_region.setText(self.listener.region or '')
        self.edit_notes.setPlainText(self.listener.notes or '')
    
    def _validate(self) -> bool:
        """Validate form data."""
        if not self.edit_last_name.text().strip():
            QMessageBox.warning(
                self, "Ошибка валидации",
                "Фамилия обязательна для заполнения"
            )
            self.edit_last_name.setFocus()
            return False
        
        if not self.edit_first_name.text().strip():
            QMessageBox.warning(
                self, "Ошибка валидации",
                "Имя обязательно для заполнения"
            )
            self.edit_first_name.setFocus()
            return False
        
        return True
    
    def _on_save(self):
        """Handle save button click."""
        if self._validate():
            self.accept()
    
    def get_data(self) -> Dict[str, Any]:
        """Get form data as dictionary."""
        data = {
            'last_name': self.edit_last_name.text().strip(),
            'first_name': self.edit_first_name.text().strip(),
            'middle_name': self.edit_middle_name.text().strip() or None,
            'position': self.edit_position.text().strip() or None,
            'workplace': self.edit_workplace.text().strip() or None,
            'region': self.edit_region.text().strip() or None,
            'notes': self.edit_notes.toPlainText().strip() or None,
        }
        
        return data
