"""
Document generation dialog.
"""

import os
import re
import zipfile
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QGroupBox, QMessageBox,
    QComboBox, QListWidget, QListWidgetItem, QTextEdit,
    QCheckBox, QRadioButton, QButtonGroup, QProgressBar,
    QFileDialog, QAbstractItemView, QLineEdit, QSpinBox, QDateEdit,
    QScrollArea, QWidget, QSizePolicy, QApplication
)

from ...database.connection import DatabaseSession
from ...database.models import Listener, Program
from ...services.document_generator import DocumentGenerator


class GenerateDialog(QDialog):
    """
    Dialog for generating Word documents from templates.
    """
    
    def __init__(
        self,
        parent=None,
        selected_listeners: List[Listener] = None,
        selected_program: Program = None
    ):
        super().__init__(parent)
        
        self.selected_listeners = selected_listeners or []
        self.selected_program = selected_program
        self.generator = DocumentGenerator()
        
        self._all_listeners: List[Listener] = []
        self._all_programs: List[Program] = []
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Генерация документов")
        
        # Adaptive window size based on screen
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        width = min(int(screen.width() * 0.6), 1000)
        height = min(int(screen.height() * 0.85), 900)
        self.resize(width, height)
        self.setMinimumWidth(700)
        self.setMinimumHeight(650)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Template selection group
        template_group = QGroupBox("Шаблон документа")
        template_layout = QFormLayout(template_group)
        template_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        self.combo_template = QComboBox()
        self.combo_template.setMinimumHeight(30)
        self._load_templates()
        template_layout.addRow("Выберите шаблон:", self.combo_template)
        
        # Template buttons row
        template_buttons = QHBoxLayout()
        btn_refresh_templates = QPushButton("Обновить список")
        btn_refresh_templates.clicked.connect(self._load_templates)
        template_buttons.addWidget(btn_refresh_templates)
        
        btn_fix_template = QPushButton("🔧 Исправить шаблон")
        btn_fix_template.setToolTip("Добавить цикл для списка слушателей (если отсутствует)")
        btn_fix_template.clicked.connect(self._fix_template_loop)
        template_buttons.addWidget(btn_fix_template)
        
        template_buttons.addStretch()
        template_layout.addRow("", template_buttons)
        
        layout.addWidget(template_group)
        
        # Program selection group
        program_group = QGroupBox("Программа обучения (опционально)")
        program_layout = QFormLayout(program_group)
        program_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        self.combo_program = QComboBox()
        self.combo_program.setMinimumHeight(30)
        self.combo_program.addItem("-- Не выбрана --", None)
        self.combo_program.currentIndexChanged.connect(self._on_program_changed)
        program_layout.addRow("Программа:", self.combo_program)
        
        layout.addWidget(program_group)
        
        # Document details group (for templates with lists)
        details_group = QGroupBox("Реквизиты документа")
        details_layout = QFormLayout(details_group)
        details_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        details_layout.setLabelAlignment(Qt.AlignRight)
        
        # Helper to create styled line edit
        def create_line_edit(placeholder: str, min_height: int = 28) -> QLineEdit:
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setMinimumHeight(min_height)
            return edit
        
        self.edit_order_number = create_line_edit("Например: 111")
        details_layout.addRow("Номер приказа:", self.edit_order_number)
        
        self.edit_order_date = QDateEdit()
        self.edit_order_date.setCalendarPopup(True)
        self.edit_order_date.setDate(date.today())
        self.edit_order_date.setMinimumHeight(28)
        details_layout.addRow("Дата приказа:", self.edit_order_date)
        
        self.edit_contract_type = create_line_edit("государственным контрактом на оказание услуг по повышению квалификации")
        details_layout.addRow("Тип договора:", self.edit_contract_type)
        
        self.edit_contract_number = create_line_edit("б/н или № 123")
        details_layout.addRow("Номер договора:", self.edit_contract_number)
        
        self.edit_contract_date = create_line_edit("от 28 мая 2025 года")
        details_layout.addRow("Дата договора:", self.edit_contract_date)
        
        self.edit_stream_name = create_line_edit("государственных гражданских служащих")
        details_layout.addRow("Название потока:", self.edit_stream_name)
        
        self.edit_program_name = create_line_edit("Название программы")
        details_layout.addRow("Название программы:", self.edit_program_name)
        
        self.spin_hours = QSpinBox()
        self.spin_hours.setRange(1, 1000)
        self.spin_hours.setValue(16)
        self.spin_hours.setMinimumHeight(28)
        self.spin_hours.setMinimumWidth(100)
        details_layout.addRow("Объём (часов):", self.spin_hours)
        
        self.edit_education_form = create_line_edit("очной")
        details_layout.addRow("Форма обучения:", self.edit_education_form)
        
        self.edit_education_format = create_line_edit("с применением электронного обучения, дистанционных образовательных технологий")
        details_layout.addRow("Формат обучения:", self.edit_education_format)
        
        self.edit_start_date = QDateEdit()
        self.edit_start_date.setCalendarPopup(True)
        self.edit_start_date.setDate(date.today())
        self.edit_start_date.setMinimumHeight(28)
        details_layout.addRow("Дата начала:", self.edit_start_date)
        
        self.edit_end_date = QDateEdit()
        self.edit_end_date.setCalendarPopup(True)
        self.edit_end_date.setDate(date.today())
        self.edit_end_date.setMinimumHeight(28)
        details_layout.addRow("Дата окончания:", self.edit_end_date)
        
        layout.addWidget(details_group)
        
        # Listeners selection group
        listeners_group = QGroupBox("Слушатели")
        listeners_layout = QVBoxLayout(listeners_group)
        
        # Generation mode
        mode_layout = QHBoxLayout()
        self.btn_mode_group = QButtonGroup(self)
        
        self.radio_selected = QRadioButton("Выбранные слушатели")
        self.radio_all = QRadioButton("Все слушатели")
        self.radio_from_program = QRadioButton("Слушатели программы")
        
        self.btn_mode_group.addButton(self.radio_selected)
        self.btn_mode_group.addButton(self.radio_all)
        self.btn_mode_group.addButton(self.radio_from_program)
        
        self.radio_selected.setChecked(True)
        
        mode_layout.addWidget(self.radio_selected)
        mode_layout.addWidget(self.radio_all)
        mode_layout.addWidget(self.radio_from_program)
        
        listeners_layout.addLayout(mode_layout)
        
        # Listeners list
        self.list_listeners = QListWidget()
        self.list_listeners.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_listeners.setMaximumHeight(150)
        listeners_layout.addWidget(self.list_listeners)
        
        # Selection buttons
        selection_layout = QHBoxLayout()
        btn_select_all = QPushButton("Выбрать все")
        btn_select_all.clicked.connect(self._select_all_listeners)
        btn_deselect_all = QPushButton("Снять выбор")
        btn_deselect_all.clicked.connect(self._deselect_all_listeners)
        
        selection_layout.addWidget(btn_select_all)
        selection_layout.addWidget(btn_deselect_all)
        selection_layout.addStretch()
        
        listeners_layout.addLayout(selection_layout)
        
        layout.addWidget(listeners_group)
        
        # Options group
        options_group = QGroupBox("Параметры генерации")
        options_layout = QVBoxLayout(options_group)
        
        self.check_separate_files = QCheckBox("Отдельный файл для каждого слушателя")
        self.check_separate_files.setChecked(False)
        options_layout.addWidget(self.check_separate_files)
        
        self.check_open_folder = QCheckBox("Открыть папку после генерации")
        self.check_open_folder.setChecked(True)
        options_layout.addWidget(self.check_open_folder)
        
        layout.addWidget(options_group)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results
        self.text_results = QTextEdit()
        self.text_results.setReadOnly(True)
        self.text_results.setMaximumHeight(100)
        self.text_results.setVisible(False)
        layout.addWidget(self.text_results)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_generate = QPushButton("Сгенерировать")
        self.btn_generate.setDefault(True)
        self.btn_generate.clicked.connect(self._do_generate)
        
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_generate)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
    
    def _load_templates(self):
        """Load available templates."""
        self.combo_template.clear()
        
        templates = self.generator.get_available_templates()
        
        if templates:
            self.combo_template.addItems(templates)
        else:
            self.combo_template.addItem("-- Нет шаблонов --")
            QMessageBox.warning(
                self, "Предупреждение",
                "В папке templates/ не найдено шаблонов.\n"
                "Поместите файлы .docx в папку templates/"
            )
    
    def _fix_template_loop(self):
        """Add {% for listener in listeners %} loop to template if missing."""
        template_name = self.combo_template.currentText()
        if not template_name or template_name == "-- Нет шаблонов --":
            QMessageBox.warning(self, "Предупреждение", "Выберите шаблон")
            return
        
        tpl_path = self.generator.templates_dir / template_name
        
        if not tpl_path.exists():
            QMessageBox.critical(self, "Ошибка", f"Файл шаблона не найден: {tpl_path}")
            return
        
        try:
            with zipfile.ZipFile(tpl_path, 'r') as z:
                xml = z.read('word/document.xml').decode('utf-8')
            
            # Check if loop already exists
            if '{% for listener' in xml:
                QMessageBox.information(
                    self, "Информация", 
                    "✅ Цикл уже есть в шаблоне.\nШаблон готов к использованию."
                )
                return
            
            # Find table row with listener or loop variables
            tr_pattern = r'(<w:tr\b[^>]*>.*?</w:tr>)'
            matches = list(re.finditer(tr_pattern, xml, re.DOTALL))
            
            found = False
            for match in matches:
                tr_content = match.group(1)
                if 'loop' in tr_content or 'listener' in tr_content:
                    new_tr = '{% for listener in listeners %}' + tr_content + '{% endfor %}'
                    xml = xml.replace(tr_content, new_tr, 1)
                    found = True
                    break
            
            if not found:
                QMessageBox.warning(
                    self, "Предупреждение",
                    "Не найдена строка таблицы с переменными listener или loop.\n\n"
                    "Убедитесь, что в шаблоне есть строка таблицы с переменными:\n"
                    "• {{ loop.index }}\n"
                    "• {{ listener.full_name }}\n"
                    "• {{ listener.position }}\n"
                    "• и т.д."
                )
                return
            
            # Save modified template
            tmp_path = str(tpl_path) + '.tmp'
            with zipfile.ZipFile(tpl_path, 'r') as zin:
                with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                    for item in zin.infolist():
                        if item.filename == 'word/document.xml':
                            zout.writestr(item, xml.encode('utf-8'))
                        else:
                            zout.writestr(item, zin.read(item.filename))
            
            shutil.move(tmp_path, tpl_path)
            
            QMessageBox.information(
                self, "Успех",
                f"✅ Цикл добавлен в шаблон!\n\n"
                f"Теперь шаблон '{template_name}' готов к генерации документов со списком слушателей."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при исправлении шаблона:\n{e}")
    
    def _load_data(self):
        """Load listeners and programs from database."""
        try:
            with DatabaseSession() as session:
                # Load all listeners and detach them from session
                listeners = session.query(Listener).order_by(
                    Listener.last_name
                ).all()
                
                # Store listener data as dictionaries to avoid detached instance issues
                self._all_listeners = []
                for l in listeners:
                    self._all_listeners.append({
                        'id': l.id,
                        'full_name': l.full_name,
                        'last_name': l.last_name,
                        'first_name': l.first_name,
                        'middle_name': l.middle_name,
                        'position': l.position,
                        'workplace': l.workplace,
                        'region': l.region,
                        'notes': l.notes,
                    })
                
                # Load all programs
                programs = session.query(Program).order_by(
                    Program.program_name
                ).all()
                
                self._all_programs = []
                for p in programs:
                    self._all_programs.append({
                        'id': p.id,
                        'program_name': p.program_name,
                        'program_short_name': p.program_short_name,
                        'display_name': p.display_name,
                        'training_basis': p.training_basis,
                        'training_period': p.training_period,
                        'program_volume': p.program_volume,
                        'education_form': p.education_form,
                        'education_format': p.education_format,
                        'listener_category': p.listener_category,
                        'expulsion_date': p.expulsion_date,
                        'formatted_expulsion_date': p.formatted_expulsion_date,
                    })
                
                # Populate programs combo
                for program in self._all_programs:
                    self.combo_program.addItem(
                        program['display_name'],
                        program['id']
                    )
                
                # Pre-select program if provided
                if self.selected_program:
                    index = self.combo_program.findData(self.selected_program.id)
                    if index >= 0:
                        self.combo_program.setCurrentIndex(index)
                
                # Populate listeners list
                self._populate_listeners_list()
                
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка загрузки данных: {e}"
            )
    
    def _populate_listeners_list(self):
        """Populate the listeners list widget."""
        self.list_listeners.clear()
        
        for listener in self._all_listeners:
            item = QListWidgetItem(f"{listener['full_name']} ({listener['workplace'] or 'Не указано'})")
            item.setData(Qt.UserRole, listener['id'])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            
            # Check if listener was pre-selected
            is_selected = any(
                l.id == listener['id'] for l in self.selected_listeners
            )
            item.setCheckState(Qt.Checked if is_selected else Qt.Unchecked)
            
            self.list_listeners.addItem(item)
    
    def _select_all_listeners(self):
        """Select all listeners in the list."""
        for i in range(self.list_listeners.count()):
            item = self.list_listeners.item(i)
            item.setCheckState(Qt.Checked)
    
    def _deselect_all_listeners(self):
        """Deselect all listeners."""
        for i in range(self.list_listeners.count()):
            item = self.list_listeners.item(i)
            item.setCheckState(Qt.Unchecked)
    
    def _get_selected_listener_ids(self) -> List[int]:
        """Get IDs of selected listeners."""
        ids = []
        
        for i in range(self.list_listeners.count()):
            item = self.list_listeners.item(i)
            if item.checkState() == Qt.Checked:
                listener_id = item.data(Qt.UserRole)
                if listener_id:
                    ids.append(listener_id)
        
        return ids
    
    def _on_program_changed(self, index: int):
        """Handle program selection change - fill fields from program data."""
        program_id = self.combo_program.currentData()
        if not program_id:
            return
        
        for p in self._all_programs:
            if p['id'] == program_id:
                self.edit_program_name.setText(p.get('program_name') or '')
                self.edit_education_form.setText(p.get('education_form') or '')
                self.edit_education_format.setText(p.get('education_format') or '')
                if p.get('program_volume'):
                    try:
                        hours = int(str(p['program_volume']).split()[0])
                        self.spin_hours.setValue(hours)
                    except:
                        pass
                break
    
    def _do_generate(self):
        """Generate documents."""
        # Validate template selection
        template_name = self.combo_template.currentText()
        if not template_name or template_name.startswith("--"):
            QMessageBox.warning(
                self, "Предупреждение",
                "Выберите шаблон документа"
            )
            return
        
        # Get selected listeners
        selected_ids = self._get_selected_listener_ids()
        
        if not selected_ids:
            QMessageBox.warning(
                self, "Предупреждение",
                "Выберите хотя бы одного слушателя"
            )
            return
        
        # Get selected program
        program_id = self.combo_program.currentData()
        program_data = None
        
        if program_id:
            for p in self._all_programs:
                if p['id'] == program_id:
                    program_data = p
                    break
        
        # Get listeners data with court_name alias
        listeners_data = []
        for l in self._all_listeners:
            if l['id'] in selected_ids:
                listener = l.copy()
                listener['court_name'] = listener.get('workplace') or ''
                listeners_data.append(listener)
        
        # Show progress
        self.text_results.setVisible(True)
        self.text_results.clear()
        self.btn_generate.setEnabled(False)
        
        generated_files = []
        errors = []
        
        try:
            if self.check_separate_files.isChecked():
                # Generate separate file for each listener
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, len(listeners_data))
                self.progress_bar.setValue(0)
                
                for idx, listener_data in enumerate(listeners_data, start=1):
                    self.progress_bar.setValue(idx)
                    self.text_results.append(f"Обработка: {listener_data['full_name']}...")
                    QApplication.processEvents()
                    
                    try:
                        file_path = self.generator.generate_for_listener_dict(
                            listener_data=listener_data,
                            program_data=program_data,
                            template_name=template_name,
                            order_number=idx
                        )
                        generated_files.append(file_path)
                        
                    except Exception as e:
                        errors.append(f"{listener_data['full_name']}: {e}")
                
                self.progress_bar.setVisible(False)
            else:
                # Generate single document with all listeners (table)
                self.text_results.append(f"Генерация документа со списком из {len(listeners_data)} слушателей...")
                QApplication.processEvents()
                
                order_date = self.edit_order_date.date().toPyDate()
                start_date = self.edit_start_date.date().toPyDate()
                end_date = self.edit_end_date.date().toPyDate()
                
                order_datetime = datetime.combine(order_date, datetime.min.time())
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.min.time())
                
                try:
                    file_path = self.generator.generate_order(
                        order_type='custom',
                        listeners_data=listeners_data,
                        order_number=self.edit_order_number.text().strip() or '1',
                        order_date=order_datetime,
                        program_name=self.edit_program_name.text().strip(),
                        stream_name=self.edit_stream_name.text().strip(),
                        start_date=start_datetime,
                        end_date=end_datetime,
                        contract_date=self.edit_contract_date.text().strip(),
                        contract_type=self.edit_contract_type.text().strip(),
                        contract_number=self.edit_contract_number.text().strip(),
                        hours=self.spin_hours.value(),
                        education_form=self.edit_education_form.text().strip(),
                        education_format=self.edit_education_format.text().strip(),
                        template_name=template_name
                    )
                    generated_files.append(file_path)
                    self.text_results.append(f"✓ Создан: {file_path}")
                    
                except Exception as e:
                    errors.append(str(e))
            
            # Show results
            self.text_results.append(f"\n=== Завершено ===")
            self.text_results.append(f"Создано документов: {len(generated_files)}")
            
            if errors:
                self.text_results.append(f"Ошибок: {len(errors)}")
                for error in errors:
                    self.text_results.append(f"  ✗ {error}")
            
            if generated_files:
                QMessageBox.information(
                    self, "Успех",
                    f"Создано документов: {len(generated_files)}\n"
                    f"Папка: {self.generator.output_dir}"
                )
                
                # Open output folder if requested
                if self.check_open_folder.isChecked():
                    self._open_output_folder()
            
        except Exception as e:
            self.text_results.append(f"\n✗ Ошибка: {e}")
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка генерации: {e}"
            )
        
        finally:
            self.progress_bar.setVisible(False)
            self.btn_generate.setEnabled(True)
    
    def _open_output_folder(self):
        """Open the output folder in file manager."""
        import subprocess
        import sys
        
        output_path = self.generator.output_dir
        
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', str(output_path)])
            elif sys.platform == 'win32':
                subprocess.run(['explorer', str(output_path)])
            else:
                subprocess.run(['xdg-open', str(output_path)])
        except Exception:
            pass
