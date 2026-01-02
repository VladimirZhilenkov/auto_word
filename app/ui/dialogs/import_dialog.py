"""
Excel import dialog for importing listeners and programs from Excel files.
"""

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QGroupBox, QMessageBox,
    QFileDialog, QComboBox, QLineEdit, QTextEdit,
    QRadioButton, QButtonGroup, QProgressBar
)

from ...services.excel_importer import ExcelImporter


class ImportDialog(QDialog):
    """
    Dialog for importing data from Excel files.
    Supports importing both listeners and programs.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.file_path: Optional[str] = None
        self.sheet_names = []
        self.importer = ExcelImporter()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Импорт из Excel")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
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
        
        # Import type group
        type_group = QGroupBox("Тип импорта")
        type_layout = QVBoxLayout(type_group)
        
        self.btn_group = QButtonGroup(self)
        
        self.radio_listeners = QRadioButton("Импорт слушателей")
        self.radio_listeners.setChecked(True)
        self.btn_group.addButton(self.radio_listeners)
        
        self.radio_programs = QRadioButton("Импорт программ")
        self.btn_group.addButton(self.radio_programs)
        
        type_layout.addWidget(self.radio_listeners)
        type_layout.addWidget(self.radio_programs)
        
        layout.addWidget(type_group)
        
        # Sheet selection group
        sheet_group = QGroupBox("Лист Excel")
        sheet_layout = QFormLayout(sheet_group)
        
        self.combo_sheet = QComboBox()
        self.combo_sheet.setEnabled(False)
        sheet_layout.addRow("Выберите лист:", self.combo_sheet)
        
        layout.addWidget(sheet_group)
        
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
            "Файл должен содержать заголовки столбцов в первой строке."
        )
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)
    
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
            self.btn_import.setEnabled(True)
            
            self.text_results.setText(
                f"Файл загружен: {Path(self.file_path).name}\n"
                f"Найдено листов: {len(self.sheet_names)}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка чтения файла: {e}"
            )
            self.combo_sheet.setEnabled(False)
            self.btn_import.setEnabled(False)
    
    def _do_import(self):
        """Perform the import."""
        if not self.file_path:
            QMessageBox.warning(
                self, "Предупреждение",
                "Выберите файл для импорта"
            )
            return
        
        sheet_name = self.combo_sheet.currentText()
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.btn_import.setEnabled(False)
        
        try:
            if self.radio_listeners.isChecked():
                result = self.importer.import_listeners(
                    self.file_path,
                    sheet_name=sheet_name
                )
                import_type = "слушателей"
            else:
                result = self.importer.import_programs(
                    self.file_path,
                    sheet_name=sheet_name
                )
                import_type = "программ"
            
            # Display results
            self._display_results(result, import_type)
            
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка импорта: {e}"
            )
        
        finally:
            self.progress_bar.setVisible(False)
            self.btn_import.setEnabled(True)
    
    def _display_results(self, result: dict, import_type: str):
        """Display import results."""
        text = f"=== Результаты импорта {import_type} ===\n\n"
        
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
