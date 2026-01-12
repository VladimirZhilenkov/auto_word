"""
Listener form dialog for adding/editing listeners.
Extended with personal data fields including passport, contacts, and addresses.
Includes program selection with ability to add new programs.
"""

from datetime import date
from typing import Dict, Optional, Any, List

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QGroupBox,
    QMessageBox, QScrollArea, QWidget, QCheckBox, QDateEdit,
    QTabWidget, QComboBox, QInputDialog
)

from ...database.models import Listener, Program
from ...database.connection import DatabaseSession


class ListenerFormDialog(QDialog):
    """
    Dialog for adding or editing a listener.
    Includes extended personal data fields and program selection.
    """
    
    def __init__(
        self, 
        parent=None, 
        listener: Optional[Listener] = None,
        default_program_id: Optional[int] = None
    ):
        super().__init__(parent)
        
        self.listener = listener
        self.is_edit_mode = listener is not None
        self.default_program_id = default_program_id
        self.selected_program_id: Optional[int] = None
        
        self._setup_ui()
        self._load_programs()
        
        if self.is_edit_mode:
            self._load_data()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        title = "Редактирование слушателя" if self.is_edit_mode else "Добавление слушателя"
        self.setWindowTitle(title)
        self.setMinimumWidth(650)
        self.setMinimumHeight(600)
        self.setModal(True)
        
        main_layout = QVBoxLayout(self)
        
        # Create tab widget for organized data entry
        self.tab_widget = QTabWidget()
        
        # Tab 1: Basic info (ФИО и работа)
        self.tab_widget.addTab(self._create_basic_tab(), "Основные данные")
        
        # Tab 2: Contacts
        self.tab_widget.addTab(self._create_contacts_tab(), "Контакты")
        
        # Tab 3: Passport data
        self.tab_widget.addTab(self._create_passport_tab(), "Паспортные данные")
        
        # Tab 4: Addresses and IDs
        self.tab_widget.addTab(self._create_ids_tab(), "Адреса и идентификаторы")
        
        main_layout.addWidget(self.tab_widget)
        
        # Personal data consent checkbox
        consent_layout = QHBoxLayout()
        self.chk_consent = QCheckBox("Принимаю условия обработки персональных данных")
        self.chk_consent.setStyleSheet("font-weight: bold;")
        consent_layout.addWidget(self.chk_consent)
        main_layout.addLayout(consent_layout)
        
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
        
        main_layout.addLayout(button_layout)
        
        # Required fields label
        required_label = QLabel("* - обязательные поля")
        required_label.setStyleSheet("color: gray; font-size: 10px;")
        main_layout.addWidget(required_label)
    
    def _create_basic_tab(self) -> QWidget:
        """Create basic info tab (Name and work info)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
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
        
        # Birth date
        self.edit_birth_date = QDateEdit()
        self.edit_birth_date.setCalendarPopup(True)
        self.edit_birth_date.setDisplayFormat("dd.MM.yyyy")
        self.edit_birth_date.setDate(QDate(1980, 1, 1))
        self.edit_birth_date.setSpecialValueText(" ")  # Allow empty
        self.chk_birth_date = QCheckBox("Указать")
        birth_layout = QHBoxLayout()
        birth_layout.addWidget(self.edit_birth_date)
        birth_layout.addWidget(self.chk_birth_date)
        self.edit_birth_date.setEnabled(False)
        self.chk_birth_date.toggled.connect(self.edit_birth_date.setEnabled)
        name_layout.addRow("Дата рождения:", birth_layout)
        
        layout.addWidget(name_group)
        
        # Work info group
        work_group = QGroupBox("Рабочая информация")
        work_layout = QFormLayout(work_group)
        
        self.edit_workplace = QLineEdit()
        self.edit_workplace.setPlaceholderText("Введите наименование организации/суда")
        work_layout.addRow("Место работы:", self.edit_workplace)
        
        self.edit_position = QLineEdit()
        self.edit_position.setPlaceholderText("Введите должность")
        work_layout.addRow("Должность:", self.edit_position)
        
        self.edit_region = QLineEdit()
        self.edit_region.setPlaceholderText("Введите субъект РФ")
        work_layout.addRow("Субъект РФ:", self.edit_region)
        
        layout.addWidget(work_group)
        
        # Program group
        program_group = QGroupBox("Программа обучения")
        program_layout = QHBoxLayout(program_group)
        
        self.combo_program = QComboBox()
        self.combo_program.setMinimumWidth(300)
        self.combo_program.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        program_layout.addWidget(self.combo_program, stretch=1)
        
        self.btn_add_program = QPushButton("+")
        self.btn_add_program.setMaximumWidth(30)
        self.btn_add_program.setToolTip("Добавить новую программу")
        self.btn_add_program.clicked.connect(self._on_add_program)
        program_layout.addWidget(self.btn_add_program)
        
        layout.addWidget(program_group)
        
        # Notes group
        notes_group = QGroupBox("Примечания")
        notes_layout = QVBoxLayout(notes_group)
        
        self.edit_notes = QTextEdit()
        self.edit_notes.setMaximumHeight(80)
        self.edit_notes.setPlaceholderText("Дополнительная информация...")
        notes_layout.addWidget(self.edit_notes)
        
        layout.addWidget(notes_group)
        layout.addStretch()
        
        return widget
    
    def _create_contacts_tab(self) -> QWidget:
        """Create contacts tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Contacts group
        contacts_group = QGroupBox("Контактная информация")
        contacts_layout = QFormLayout(contacts_group)
        
        self.edit_mobile_phone = QLineEdit()
        self.edit_mobile_phone.setPlaceholderText("+7 (999) 123-45-67")
        contacts_layout.addRow("Мобильный телефон:", self.edit_mobile_phone)
        
        self.edit_work_phone = QLineEdit()
        self.edit_work_phone.setPlaceholderText("+7 (495) 123-45-67")
        contacts_layout.addRow("Рабочий телефон:", self.edit_work_phone)
        
        self.edit_email = QLineEdit()
        self.edit_email.setPlaceholderText("email@example.com")
        contacts_layout.addRow("Электронная почта:", self.edit_email)
        
        layout.addWidget(contacts_group)
        layout.addStretch()
        
        return widget
    
    def _create_passport_tab(self) -> QWidget:
        """Create passport data tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Passport group
        passport_group = QGroupBox("Паспортные данные")
        passport_layout = QFormLayout(passport_group)
        
        self.edit_passport_series_number = QLineEdit()
        self.edit_passport_series_number.setPlaceholderText("1234 567890")
        passport_layout.addRow("Серия и номер:", self.edit_passport_series_number)
        
        # Passport issue date
        self.edit_passport_issue_date = QDateEdit()
        self.edit_passport_issue_date.setCalendarPopup(True)
        self.edit_passport_issue_date.setDisplayFormat("dd.MM.yyyy")
        self.edit_passport_issue_date.setDate(QDate(2010, 1, 1))
        self.chk_passport_date = QCheckBox("Указать")
        passport_date_layout = QHBoxLayout()
        passport_date_layout.addWidget(self.edit_passport_issue_date)
        passport_date_layout.addWidget(self.chk_passport_date)
        self.edit_passport_issue_date.setEnabled(False)
        self.chk_passport_date.toggled.connect(self.edit_passport_issue_date.setEnabled)
        passport_layout.addRow("Дата выдачи:", passport_date_layout)
        
        self.edit_passport_issued_by = QLineEdit()
        self.edit_passport_issued_by.setPlaceholderText("Наименование органа, выдавшего паспорт")
        passport_layout.addRow("Кем выдан:", self.edit_passport_issued_by)
        
        self.edit_passport_dept_code = QLineEdit()
        self.edit_passport_dept_code.setPlaceholderText("123-456")
        self.edit_passport_dept_code.setMaximumWidth(150)
        passport_layout.addRow("Код подразделения:", self.edit_passport_dept_code)
        
        layout.addWidget(passport_group)
        layout.addStretch()
        
        return widget
    
    def _create_ids_tab(self) -> QWidget:
        """Create addresses and identifiers tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Addresses group
        address_group = QGroupBox("Адреса")
        address_layout = QFormLayout(address_group)
        
        self.edit_registration_address = QLineEdit()
        self.edit_registration_address.setPlaceholderText("Индекс, город, улица, дом, квартира")
        address_layout.addRow("Адрес регистрации:", self.edit_registration_address)
        
        self.edit_actual_address = QLineEdit()
        self.edit_actual_address.setPlaceholderText("Индекс, город, улица, дом, квартира (для корреспонденции)")
        address_layout.addRow("Фактический адрес:", self.edit_actual_address)
        
        layout.addWidget(address_group)
        
        # IDs group
        ids_group = QGroupBox("Идентификационные данные")
        ids_layout = QFormLayout(ids_group)
        
        self.edit_snils = QLineEdit()
        self.edit_snils.setPlaceholderText("123-456-789 00")
        self.edit_snils.setMaximumWidth(200)
        ids_layout.addRow("СНИЛС:", self.edit_snils)
        
        self.edit_inn = QLineEdit()
        self.edit_inn.setPlaceholderText("123456789012")
        self.edit_inn.setMaximumWidth(200)
        ids_layout.addRow("ИНН:", self.edit_inn)
        
        layout.addWidget(ids_group)
        layout.addStretch()
        
        return widget
    
    def _load_programs(self):
        """Load programs into combo box."""
        self.combo_program.clear()
        self.combo_program.addItem("-- Без программы --", None)
        
        try:
            with DatabaseSession() as session:
                programs = session.query(Program).order_by(Program.program_name).all()
                
                for program in programs:
                    # Use short name if available, otherwise truncate full name
                    if program.program_short_name:
                        display = program.program_short_name
                    else:
                        display = program.program_name[:60] + "..." if len(program.program_name) > 60 else program.program_name
                    
                    self.combo_program.addItem(display, program.id)
                
                # Set default program if specified
                if self.default_program_id:
                    for i in range(self.combo_program.count()):
                        if self.combo_program.itemData(i) == self.default_program_id:
                            self.combo_program.setCurrentIndex(i)
                            break
                            
        except Exception as e:
            print(f"Error loading programs: {e}")
    
    def _on_add_program(self):
        """Add a new program via quick dialog."""
        # First ask for short name
        short_name, ok1 = QInputDialog.getText(
            self,
            "Новая программа",
            "Краткое наименование программы:",
            QLineEdit.Normal,
            ""
        )
        
        if not ok1 or not short_name.strip():
            return
        
        short_name = short_name.strip()
        
        # Then ask for full name (optional, defaults to short name)
        full_name, ok2 = QInputDialog.getText(
            self,
            "Новая программа",
            "Полное наименование программы\n(оставьте пустым для использования краткого):",
            QLineEdit.Normal,
            short_name
        )
        
        if not ok2:
            return
        
        full_name = full_name.strip() or short_name
        
        try:
            with DatabaseSession() as session:
                # Check if program with this short name already exists
                existing = session.query(Program).filter(
                    Program.program_short_name == short_name
                ).first()
                
                if existing:
                    QMessageBox.warning(
                        self,
                        "Программа существует",
                        f"Программа с кратким названием '{short_name}' уже существует."
                    )
                    # Select existing program
                    for i in range(self.combo_program.count()):
                        if self.combo_program.itemData(i) == existing.id:
                            self.combo_program.setCurrentIndex(i)
                            break
                    return
                
                # Create new program
                new_program = Program(
                    program_name=full_name,
                    program_short_name=short_name
                )
                session.add(new_program)
                session.commit()
                
                # Reload programs and select the new one
                new_id = new_program.id
                self._load_programs()
                
                for i in range(self.combo_program.count()):
                    if self.combo_program.itemData(i) == new_id:
                        self.combo_program.setCurrentIndex(i)
                        break
                
                QMessageBox.information(
                    self,
                    "Программа создана",
                    f"Программа '{short_name}' успешно создана."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось создать программу: {e}"
            )
    
    def _load_data(self):
        """Load existing listener data into form."""
        if not self.listener:
            return
        
        # Basic info
        self.edit_last_name.setText(self.listener.last_name or '')
        self.edit_first_name.setText(self.listener.first_name or '')
        self.edit_middle_name.setText(self.listener.middle_name or '')
        
        if self.listener.birth_date:
            self.chk_birth_date.setChecked(True)
            self.edit_birth_date.setDate(QDate(
                self.listener.birth_date.year,
                self.listener.birth_date.month,
                self.listener.birth_date.day
            ))
        
        self.edit_position.setText(self.listener.position or '')
        self.edit_workplace.setText(self.listener.workplace or '')
        self.edit_region.setText(self.listener.region or '')
        self.edit_notes.setPlainText(self.listener.notes or '')
        
        # Load listener's program (first one if multiple)
        if self.listener.programs:
            program_id = self.listener.programs[0].id
            for i in range(self.combo_program.count()):
                if self.combo_program.itemData(i) == program_id:
                    self.combo_program.setCurrentIndex(i)
                    break
        
        # Contacts
        self.edit_mobile_phone.setText(self.listener.mobile_phone or '')
        self.edit_work_phone.setText(self.listener.work_phone or '')
        self.edit_email.setText(self.listener.email or '')
        
        # Passport
        self.edit_passport_series_number.setText(self.listener.passport_series_number or '')
        
        if self.listener.passport_issue_date:
            self.chk_passport_date.setChecked(True)
            self.edit_passport_issue_date.setDate(QDate(
                self.listener.passport_issue_date.year,
                self.listener.passport_issue_date.month,
                self.listener.passport_issue_date.day
            ))
        
        self.edit_passport_issued_by.setText(self.listener.passport_issued_by or '')
        self.edit_passport_dept_code.setText(self.listener.passport_department_code or '')
        
        # Addresses and IDs
        self.edit_registration_address.setText(self.listener.registration_address or '')
        self.edit_actual_address.setText(self.listener.actual_address or '')
        self.edit_snils.setText(self.listener.snils or '')
        self.edit_inn.setText(self.listener.inn or '')
        
        # Consent
        self.chk_consent.setChecked(bool(self.listener.personal_data_consent))
    
    def _validate(self) -> bool:
        """Validate form data."""
        if not self.edit_last_name.text().strip():
            QMessageBox.warning(
                self, "Ошибка валидации",
                "Фамилия обязательна для заполнения"
            )
            self.tab_widget.setCurrentIndex(0)
            self.edit_last_name.setFocus()
            return False
        
        if not self.edit_first_name.text().strip():
            QMessageBox.warning(
                self, "Ошибка валидации",
                "Имя обязательно для заполнения"
            )
            self.tab_widget.setCurrentIndex(0)
            self.edit_first_name.setFocus()
            return False
        
        # Validate email format if provided
        email = self.edit_email.text().strip()
        if email and '@' not in email:
            QMessageBox.warning(
                self, "Ошибка валидации",
                "Некорректный формат электронной почты"
            )
            self.tab_widget.setCurrentIndex(1)
            self.edit_email.setFocus()
            return False
        
        return True
    
    def _on_save(self):
        """Handle save button click."""
        if self._validate():
            self.accept()
    
    def get_data(self) -> Dict[str, Any]:
        """Get form data as dictionary."""
        data = {
            # Basic info
            'last_name': self.edit_last_name.text().strip(),
            'first_name': self.edit_first_name.text().strip(),
            'middle_name': self.edit_middle_name.text().strip() or None,
            'birth_date': None,
            'position': self.edit_position.text().strip() or None,
            'workplace': self.edit_workplace.text().strip() or None,
            'region': self.edit_region.text().strip() or None,
            'notes': self.edit_notes.toPlainText().strip() or None,
            
            # Contacts
            'mobile_phone': self.edit_mobile_phone.text().strip() or None,
            'work_phone': self.edit_work_phone.text().strip() or None,
            'email': self.edit_email.text().strip() or None,
            
            # Passport
            'passport_series_number': self.edit_passport_series_number.text().strip() or None,
            'passport_issue_date': None,
            'passport_issued_by': self.edit_passport_issued_by.text().strip() or None,
            'passport_department_code': self.edit_passport_dept_code.text().strip() or None,
            
            # Addresses
            'registration_address': self.edit_registration_address.text().strip() or None,
            'actual_address': self.edit_actual_address.text().strip() or None,
            
            # IDs
            'snils': self.edit_snils.text().strip() or None,
            'inn': self.edit_inn.text().strip() or None,
            
            # Consent
            'personal_data_consent': self.chk_consent.isChecked(),
            
            # Program
            'program_id': self.combo_program.currentData(),
        }
        
        # Handle dates
        if self.chk_birth_date.isChecked():
            qdate = self.edit_birth_date.date()
            data['birth_date'] = date(qdate.year(), qdate.month(), qdate.day())
        
        if self.chk_passport_date.isChecked():
            qdate = self.edit_passport_issue_date.date()
            data['passport_issue_date'] = date(qdate.year(), qdate.month(), qdate.day())
        
        return data
