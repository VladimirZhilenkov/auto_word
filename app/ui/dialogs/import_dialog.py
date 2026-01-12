"""
Excel import dialog for importing listeners and programs from Excel files.
Supports flexible column detection and manual mapping.
"""

from pathlib import Path
from typing import Optional, Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QGroupBox, QMessageBox,
    QFileDialog, QComboBox, QLineEdit, QTextEdit,
    QRadioButton, QButtonGroup, QProgressBar, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QWidget, QScrollArea
)

from ...services.excel_importer import ExcelImporter
from ...services.backup_manager import BackupManager
from ...database.connection import DatabaseSession
from ...database.models import Program


class ImportDialog(QDialog):
    """
    Dialog for importing data from Excel files.
    Supports importing both listeners and programs with flexible column detection.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.file_path: Optional[str] = None
        self.sheet_names = []
        self.importer = ExcelImporter()
        self.backup_manager = BackupManager()
        self.column_mapping: Dict[str, str] = {}
        self.excel_columns: List[str] = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Импорт из Excel")
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # File selection group
        file_group = QGroupBox("Выбор файла")
        file_layout = QHBoxLayout(file_group)
        
        self.edit_file_path = QLineEdit()
        self.edit_file_path.setReadOnly(True)
        self.edit_file_path.setPlaceholderText("Выберите файл Excel...")
        
        self.btn_browse = QPushButton("Обзор...")
        self.btn_browse.clicked.connect(self._browse_file)
        
        file_layout.addWidget(self.edit_file_path)
        file_layout.addWidget(self.btn_browse)
        
        layout.addWidget(file_group)
        
        # Settings row
        settings_layout = QHBoxLayout()
        
        # Import type group
        type_group = QGroupBox("Тип импорта")
        type_layout = QVBoxLayout(type_group)
        
        self.btn_group = QButtonGroup(self)
        
        self.radio_listeners = QRadioButton("Импорт слушателей")
        self.radio_listeners.setChecked(True)
        self.radio_listeners.toggled.connect(self._on_import_type_changed)
        self.btn_group.addButton(self.radio_listeners)
        
        self.radio_programs = QRadioButton("Импорт программ")
        self.btn_group.addButton(self.radio_programs)
        
        type_layout.addWidget(self.radio_listeners)
        type_layout.addWidget(self.radio_programs)
        
        settings_layout.addWidget(type_group)
        
        # Sheet selection group
        sheet_group = QGroupBox("Лист Excel")
        sheet_layout = QFormLayout(sheet_group)
        
        self.combo_sheet = QComboBox()
        self.combo_sheet.setEnabled(False)
        self.combo_sheet.currentIndexChanged.connect(self._on_sheet_changed)
        sheet_layout.addRow("Выберите лист:", self.combo_sheet)
        
        settings_layout.addWidget(sheet_group)
        
        # Program selection (for listeners import)
        program_group = QGroupBox("Программа обучения")
        program_layout = QFormLayout(program_group)
        
        self.combo_program = QComboBox()
        self.combo_program.setMinimumWidth(250)
        self.combo_program.addItem("-- Определить из данных --", None)
        self._load_programs()
        program_layout.addRow("Привязать к программе:", self.combo_program)
        
        settings_layout.addWidget(program_group)
        
        layout.addLayout(settings_layout)
        
        # Column mapping group
        mapping_group = QGroupBox("Сопоставление столбцов (автоопределение)")
        mapping_layout = QVBoxLayout(mapping_group)
        
        mapping_info = QLabel(
            "Программа автоматически определяет столбцы по заголовкам. "
            "Вы можете изменить сопоставление вручную."
        )
        mapping_info.setStyleSheet("color: gray; font-style: italic;")
        mapping_info.setWordWrap(True)
        mapping_layout.addWidget(mapping_info)
        
        # Mapping table
        self.table_mapping = QTableWidget()
        self.table_mapping.setColumnCount(3)
        self.table_mapping.setHorizontalHeaderLabels([
            "Столбец Excel", "Пример данных", "Поле в базе"
        ])
        self.table_mapping.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_mapping.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_mapping.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_mapping.setMaximumHeight(200)
        
        mapping_layout.addWidget(self.table_mapping)
        
        layout.addWidget(mapping_group)
        
        # Options
        options_layout = QHBoxLayout()
        
        self.checkbox_backup = QCheckBox("Создать резервную копию перед импортом")
        self.checkbox_backup.setChecked(True)
        options_layout.addWidget(self.checkbox_backup)
        
        options_layout.addStretch()
        
        self.btn_analyze = QPushButton("Анализировать файл")
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self._analyze_file)
        options_layout.addWidget(self.btn_analyze)
        
        layout.addLayout(options_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results group
        results_group = QGroupBox("Результаты")
        results_layout = QVBoxLayout(results_group)
        
        self.text_results = QTextEdit()
        self.text_results.setReadOnly(True)
        self.text_results.setMaximumHeight(150)
        results_layout.addWidget(self.text_results)
        
        layout.addWidget(results_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_import = QPushButton("Импортировать")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self._do_import)
        
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_import)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
        
        # Info label
        info_label = QLabel(
            "Поддерживаемые форматы: .xlsx, .xls\n"
            "Файл должен содержать заголовки столбцов в первой строке.\n"
            "Столбцы определяются автоматически по ключевым словам в заголовках."
        )
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)
    
    def _load_programs(self):
        """Load programs into combo box."""
        try:
            with DatabaseSession() as session:
                programs = session.query(Program).order_by(Program.program_name).all()
                for program in programs:
                    display = program.program_short_name or program.program_name[:50]
                    self.combo_program.addItem(display, program.id)
        except Exception:
            pass
    
    def _browse_file(self):
        """Browse for Excel file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл Excel",
            "",
            "Excel файлы (*.xlsx *.xls);;Все файлы (*.*)"
        )
        
        if file_path:
            self.file_path = file_path
            self.edit_file_path.setText(file_path)
            self._load_sheets()
    
    def _load_sheets(self):
        """Load sheet names from Excel file."""
        if not self.file_path:
            return
        
        try:
            self.sheet_names = self.importer.get_sheet_names(self.file_path)
            
            self.combo_sheet.clear()
            self.combo_sheet.addItems(self.sheet_names)
            self.combo_sheet.setEnabled(True)
            self.btn_analyze.setEnabled(True)
            
            self.text_results.setText(
                f"Файл загружен: {Path(self.file_path).name}\n"
                f"Найдено листов: {len(self.sheet_names)}\n\n"
                f"Нажмите 'Анализировать файл' для определения столбцов."
            )
            
            # Auto-analyze first sheet
            self._analyze_file()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка чтения файла: {e}"
            )
            self.combo_sheet.setEnabled(False)
            self.btn_analyze.setEnabled(False)
            self.btn_import.setEnabled(False)
    
    def _on_sheet_changed(self):
        """Handle sheet selection change."""
        if self.file_path and self.combo_sheet.currentText():
            self._analyze_file()
    
    def _on_import_type_changed(self):
        """Handle import type change."""
        if self.file_path and self.combo_sheet.currentText():
            self._analyze_file()
    
    def _analyze_file(self):
        """Analyze Excel file and detect column mapping."""
        if not self.file_path:
            return
        
        sheet_name = self.combo_sheet.currentText()
        import_type = 'listeners' if self.radio_listeners.isChecked() else 'programs'
        
        result = self.importer.analyze_excel(
            self.file_path, 
            sheet_name=sheet_name,
            import_type=import_type
        )
        
        if not result['success']:
            self.text_results.setText(f"Ошибка анализа: {result.get('error', 'Неизвестная ошибка')}")
            self.btn_import.setEnabled(False)
            return
        
        self.excel_columns = result['columns']
        self.column_mapping = result['detected_mapping']
        
        # Populate mapping table
        self._populate_mapping_table(result)
        
        # Show analysis results
        text = f"=== Анализ файла ===\n\n"
        text += f"Обнаружено столбцов: {len(result['columns'])}\n"
        text += f"Автоматически сопоставлено: {len(result['detected_mapping'])}\n"
        
        if result.get('unmapped_columns'):
            text += f"\nНесопоставленные столбцы:\n"
            for col in result['unmapped_columns'][:5]:
                text += f"  • {col}\n"
        
        text += f"\n✓ Готово к импорту"
        
        self.text_results.setText(text)
        self.btn_import.setEnabled(True)
    
    def _populate_mapping_table(self, analysis_result: dict):
        """Populate the column mapping table."""
        columns = analysis_result['columns']
        mapping = analysis_result['detected_mapping']
        sample_data = analysis_result.get('sample_data', [])
        
        self.table_mapping.setRowCount(len(columns))
        
        # Get available fields based on import type
        if self.radio_listeners.isChecked():
            available_fields = [
                ('', '-- Пропустить --'),
                ('full_name', 'ФИО (полностью)'),
                ('last_name', 'Фамилия'),
                ('first_name', 'Имя'),
                ('middle_name', 'Отчество'),
                ('position', 'Должность'),
                ('workplace', 'Место работы'),
                ('region', 'Субъект РФ'),
                ('program_name', 'Программа'),
                ('program_short_name', 'Краткое название программы'),
                ('mobile_phone', 'Мобильный телефон'),
                ('work_phone', 'Рабочий телефон'),
                ('email', 'Email'),
                ('birth_date', 'Дата рождения'),
                ('passport_series_number', 'Серия и номер паспорта'),
                ('passport_issue_date', 'Дата выдачи паспорта'),
                ('passport_issued_by', 'Кем выдан паспорт'),
                ('passport_department_code', 'Код подразделения'),
                ('registration_address', 'Адрес регистрации'),
                ('actual_address', 'Фактический адрес'),
                ('snils', 'СНИЛС'),
                ('inn', 'ИНН'),
                ('personal_data_consent', 'Согласие на обработку ПД'),
                ('notes', 'Примечания'),
            ]
        else:
            available_fields = [
                ('', '-- Пропустить --'),
                ('program_name', 'Наименование программы'),
                ('program_short_name', 'Краткое наименование'),
                ('training_basis', 'Основание обучения'),
                ('training_period', 'Период обучения'),
                ('program_volume', 'Объем программы'),
                ('education_form', 'Форма обучения'),
                ('education_format', 'Формат обучения'),
                ('listener_category', 'Категория слушателей'),
                ('expulsion_date', 'Дата отчисления'),
            ]
        
        for row_idx, col in enumerate(columns):
            # Column name
            item_col = QTableWidgetItem(str(col))
            item_col.setFlags(item_col.flags() & ~Qt.ItemIsEditable)
            self.table_mapping.setItem(row_idx, 0, item_col)
            
            # Sample data
            sample = ""
            if sample_data:
                sample = sample_data[0].get(col, "") if sample_data else ""
            item_sample = QTableWidgetItem(str(sample)[:30])
            item_sample.setFlags(item_sample.flags() & ~Qt.ItemIsEditable)
            item_sample.setToolTip(str(sample))
            self.table_mapping.setItem(row_idx, 1, item_sample)
            
            # Field combo
            combo = QComboBox()
            for field_key, field_name in available_fields:
                combo.addItem(field_name, field_key)
            
            # Set detected value
            detected_field = mapping.get(col, '')
            for i in range(combo.count()):
                if combo.itemData(i) == detected_field:
                    combo.setCurrentIndex(i)
                    break
            
            combo.currentIndexChanged.connect(
                lambda idx, c=col, cb=combo: self._on_mapping_changed(c, cb)
            )
            
            self.table_mapping.setCellWidget(row_idx, 2, combo)
    
    def _on_mapping_changed(self, excel_col: str, combo: QComboBox):
        """Handle mapping change in table."""
        field = combo.currentData()
        if field:
            self.column_mapping[excel_col] = field
        elif excel_col in self.column_mapping:
            del self.column_mapping[excel_col]
    
    def _get_current_mapping(self) -> Dict[str, str]:
        """Get current column mapping from table."""
        mapping = {}
        
        for row in range(self.table_mapping.rowCount()):
            col_item = self.table_mapping.item(row, 0)
            combo = self.table_mapping.cellWidget(row, 2)
            
            if col_item and combo:
                excel_col = col_item.text()
                field = combo.currentData()
                if field:
                    mapping[excel_col] = field
        
        return mapping
    
    def _do_import(self):
        """Perform the import."""
        if not self.file_path:
            QMessageBox.warning(
                self, "Предупреждение",
                "Выберите файл для импорта"
            )
            return
        
        sheet_name = self.combo_sheet.currentText()
        column_mapping = self._get_current_mapping()
        
        if not column_mapping:
            QMessageBox.warning(
                self, "Предупреждение",
                "Не сопоставлен ни один столбец. Укажите соответствие столбцов."
            )
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.btn_import.setEnabled(False)
        
        # Create backup if requested
        backup_path = None
        if self.checkbox_backup.isChecked():
            backup_path = self.backup_manager.auto_backup("Auto-backup before import")
        
        try:
            if self.radio_listeners.isChecked():
                # Get selected program
                program_id = self.combo_program.currentData()
                
                result = self.importer.import_listeners(
                    self.file_path,
                    sheet_name=sheet_name,
                    program_id=program_id,
                    column_mapping=column_mapping
                )
                import_type = "слушателей"
            else:
                result = self.importer.import_programs(
                    self.file_path,
                    sheet_name=sheet_name,
                    column_mapping=column_mapping
                )
                import_type = "программ"
            
            # Display results
            self._display_results(result, import_type, backup_path)
            
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка импорта: {e}"
            )
        
        finally:
            self.progress_bar.setVisible(False)
            self.btn_import.setEnabled(True)
    
    def _display_results(self, result: dict, import_type: str, backup_path: Optional[str] = None):
        """Display import results."""
        text = f"=== Результаты импорта {import_type} ===\n\n"
        
        if backup_path:
            text += f"📦 Резервная копия: {Path(backup_path).name}\n\n"
        
        if result['success']:
            text += f"✓ Импортировано: {result['imported']}\n"
            text += f"○ Пропущено: {result['skipped']}\n"
        else:
            text += "✗ Импорт не выполнен\n"
        
        if result.get('warnings'):
            text += f"\nПредупреждения ({len(result['warnings'])}):\n"
            for warning in result['warnings'][:10]:
                text += f"  • {warning}\n"
            if len(result['warnings']) > 10:
                text += f"  ... и ещё {len(result['warnings']) - 10}\n"
        
        if result.get('errors'):
            text += f"\nОшибки ({len(result['errors'])}):\n"
            for error in result['errors'][:10]:
                text += f"  ✗ {error}\n"
            if len(result['errors']) > 10:
                text += f"  ... и ещё {len(result['errors']) - 10}\n"
        
        self.text_results.setText(text)
        
        if result['success'] and result['imported'] > 0:
            QMessageBox.information(
                self, "Успех",
                f"Импорт завершен!\nИмпортировано: {result['imported']}"
            )
