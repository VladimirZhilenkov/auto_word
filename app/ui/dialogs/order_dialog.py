"""
Order generation dialog for creating orders with a list of listeners.
Supports enrollment, admission, and graduation orders.
"""

from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QGroupBox, QMessageBox,
    QComboBox, QListWidget, QListWidgetItem, QTextEdit,
    QCheckBox, QLineEdit, QDateEdit, QSpinBox,
    QProgressBar, QAbstractItemView, QApplication
)

from ...database.connection import DatabaseSession
from ...database.models import Listener, Program
from ...services.document_generator import DocumentGenerator
from ...services.order_journal_service import OrderJournalService


class OrderGenerateDialog(QDialog):
    """
    Dialog for generating order documents (enrollment, admission, graduation).
    Creates a single document with a table of all selected listeners.
    """
    
    ORDER_TYPES = {
        'enrollment': 'О зачислении слушателей',
        'admission': 'О допуске слушателей к итоговой аттестации',
        'graduation': 'Об отчислении слушателей',
        'thesis_topics': 'Об утверждении тем итоговых (аттестационных) работ и рецензентов',
        'internship': 'О направлении на стажировку',
        'theory_exam': 'О допуске к сдаче теоретического экзамена',
        'theory_exam_retake': 'О допуске к повторной сдаче теоретического экзамена',
    }
    
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
        self.journal_service = OrderJournalService()
        
        self._all_listeners: List[Dict[str, Any]] = []
        self._all_programs: List[Dict[str, Any]] = []
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Генерация приказа")
        self.setMinimumWidth(800)
        self.setMinimumHeight(700)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Order type selection
        type_group = QGroupBox("Тип приказа")
        type_layout = QFormLayout(type_group)
        
        self.combo_order_type = QComboBox()
        for key, name in self.ORDER_TYPES.items():
            self.combo_order_type.addItem(name, key)
        self.combo_order_type.currentIndexChanged.connect(self._update_next_number)
        type_layout.addRow("Тип:", self.combo_order_type)
        
        layout.addWidget(type_group)
        
        # Order details
        details_group = QGroupBox("Реквизиты приказа")
        details_layout = QFormLayout(details_group)
        
        # Order number with hint
        number_layout = QVBoxLayout()
        self.edit_order_number = QLineEdit()
        self.edit_order_number.setPlaceholderText("Например: 111")
        number_layout.addWidget(self.edit_order_number)
        
        self.label_number_hint = QLabel("")
        self.label_number_hint.setStyleSheet("color: gray; font-size: 10px;")
        number_layout.addWidget(self.label_number_hint)
        
        details_layout.addRow("Номер приказа:", number_layout)
        
        self.edit_order_date = QDateEdit()
        self.edit_order_date.setCalendarPopup(True)
        self.edit_order_date.setDate(date.today())
        details_layout.addRow("Дата приказа:", self.edit_order_date)
        
        layout.addWidget(details_group)
        
        # Program details
        program_group = QGroupBox("Программа обучения")
        program_layout = QFormLayout(program_group)
        
        self.edit_program_name = QLineEdit()
        self.edit_program_name.setPlaceholderText("Название программы")
        program_layout.addRow("Название программы:", self.edit_program_name)
        
        self.edit_stream_name = QLineEdit()
        self.edit_stream_name.setPlaceholderText("Название потока")
        program_layout.addRow("Поток:", self.edit_stream_name)
        
        self.edit_contract_date = QLineEdit()
        self.edit_contract_date.setPlaceholderText("28 мая 2025 года")
        program_layout.addRow("Дата контракта:", self.edit_contract_date)
        
        self.edit_start_date = QDateEdit()
        self.edit_start_date.setCalendarPopup(True)
        self.edit_start_date.setDate(date.today())
        program_layout.addRow("Дата начала:", self.edit_start_date)
        
        self.edit_end_date = QDateEdit()
        self.edit_end_date.setCalendarPopup(True)
        self.edit_end_date.setDate(date.today())
        program_layout.addRow("Дата окончания:", self.edit_end_date)
        
        self.spin_hours = QSpinBox()
        self.spin_hours.setRange(1, 1000)
        self.spin_hours.setValue(16)
        program_layout.addRow("Объём (часов):", self.spin_hours)
        
        layout.addWidget(program_group)
        
        # Listeners selection
        listeners_group = QGroupBox("Слушатели")
        listeners_layout = QVBoxLayout(listeners_group)
        
        self.list_listeners = QListWidget()
        self.list_listeners.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_listeners.setMaximumHeight(200)
        listeners_layout.addWidget(self.list_listeners)
        
        # Selection buttons
        selection_layout = QHBoxLayout()
        btn_select_all = QPushButton("Выбрать все")
        btn_select_all.clicked.connect(self._select_all_listeners)
        btn_deselect_all = QPushButton("Снять выбор")
        btn_deselect_all.clicked.connect(self._deselect_all_listeners)
        
        self.label_count = QLabel("Выбрано: 0")
        
        selection_layout.addWidget(btn_select_all)
        selection_layout.addWidget(btn_deselect_all)
        selection_layout.addStretch()
        selection_layout.addWidget(self.label_count)
        
        listeners_layout.addLayout(selection_layout)
        layout.addWidget(listeners_group)
        
        # Options
        options_group = QGroupBox("Параметры")
        options_layout = QVBoxLayout(options_group)
        
        self.check_open_folder = QCheckBox("Открыть папку после генерации")
        self.check_open_folder.setChecked(True)
        options_layout.addWidget(self.check_open_folder)
        
        layout.addWidget(options_group)
        
        # Results
        self.text_results = QTextEdit()
        self.text_results.setReadOnly(True)
        self.text_results.setMaximumHeight(80)
        self.text_results.setVisible(False)
        layout.addWidget(self.text_results)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_generate = QPushButton("Сгенерировать приказ")
        self.btn_generate.setDefault(True)
        self.btn_generate.clicked.connect(self._do_generate)
        
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_generate)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.list_listeners.itemChanged.connect(self._update_count)
    
    def _load_data(self):
        """Load listeners from database."""
        try:
            with DatabaseSession() as session:
                listeners = session.query(Listener).order_by(
                    Listener.last_name
                ).all()
                
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
                        'court_name': l.workplace,  # Alias
                        'region': l.region,
                        'notes': l.notes,
                    })
                
                self._populate_listeners_list()
                
                # Auto-fill fields from selected program
                if self.selected_program:
                    self._fill_from_program(session)
                
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка загрузки данных: {e}"
            )
        
        # Pre-fetch next order number
        self._update_next_number()
    
    def _fill_from_program(self, session):
        """Auto-fill form fields from the selected program."""
        import re

        prog = self.selected_program
        # Re-fetch to ensure we have latest data (detached instance safety)
        prog = session.query(Program).get(prog.id) if prog else None
        if not prog:
            return

        # Program name
        name = prog.program_name or prog.program_short_name or ''
        if name:
            self.edit_program_name.setText(name)

        # Hours from program_volume (e.g. "72 часа" → 72)
        volume = (prog.program_volume or '').strip()
        if volume:
            match = re.search(r'(\d+)', volume)
            if match:
                self.spin_hours.setValue(int(match.group(1)))

        # Parse training period into start/end dates
        period = (prog.training_period or '').strip()
        if period:
            self._parse_and_set_period(period)

    def _parse_and_set_period(self, period: str):
        """Parse training period string into start/end date fields."""
        import re
        from datetime import datetime as _dt

        pattern = r'(\d{2}[./]\d{2}[./]\d{4})\s*[-–—]\s*(\d{2}[./]\d{2}[./]\d{4})'
        match = re.search(pattern, period)
        if not match:
            pattern = r'с?\s*(\d{2}[./]\d{2}[./]\d{4})\s*(?:по|до)\s*(\d{2}[./]\d{2}[./]\d{4})'
            match = re.search(pattern, period)
        if match:
            try:
                d1 = _dt.strptime(match.group(1).replace('/', '.'), '%d.%m.%Y').date()
                d2 = _dt.strptime(match.group(2).replace('/', '.'), '%d.%m.%Y').date()
                self.edit_start_date.setDate(d1)
                self.edit_end_date.setDate(d2)
            except ValueError:
                pass

    def _update_next_number(self):
        """Fetch and display next order number for selected type."""
        order_type = self.combo_order_type.currentData()
        try:
            next_num = self.journal_service.get_next_order_number(order_type)
            self.label_number_hint.setText(f"Следующий номер в журнале: №{next_num}")
            # Autofill if empty
            if not self.edit_order_number.text().strip():
                self.edit_order_number.setText(str(next_num))
        except Exception:
            self.label_number_hint.setText("")
    
    def _populate_listeners_list(self):
        """Populate the listeners list widget."""
        self.list_listeners.clear()
        
        for listener in self._all_listeners:
            item = QListWidgetItem(
                f"{listener['full_name']} — {listener['position'] or 'Должность не указана'} "
                f"({listener['workplace'] or 'Место работы не указано'})"
            )
            item.setData(Qt.UserRole, listener['id'])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            
            # Check if listener was pre-selected
            is_selected = any(
                l.id == listener['id'] for l in self.selected_listeners
            )
            item.setCheckState(Qt.Checked if is_selected else Qt.Unchecked)
            
            self.list_listeners.addItem(item)
        
        self._update_count()
    
    def _select_all_listeners(self):
        """Select all listeners."""
        for i in range(self.list_listeners.count()):
            item = self.list_listeners.item(i)
            item.setCheckState(Qt.Checked)
    
    def _deselect_all_listeners(self):
        """Deselect all listeners."""
        for i in range(self.list_listeners.count()):
            item = self.list_listeners.item(i)
            item.setCheckState(Qt.Unchecked)
    
    def _update_count(self):
        """Update selected count label."""
        count = sum(
            1 for i in range(self.list_listeners.count())
            if self.list_listeners.item(i).checkState() == Qt.Checked
        )
        self.label_count.setText(f"Выбрано: {count}")
    
    def _get_selected_listeners(self) -> List[Dict[str, Any]]:
        """Get data of selected listeners."""
        selected = []
        
        for i in range(self.list_listeners.count()):
            item = self.list_listeners.item(i)
            if item.checkState() == Qt.Checked:
                listener_id = item.data(Qt.UserRole)
                for l in self._all_listeners:
                    if l['id'] == listener_id:
                        selected.append(l)
                        break
        
        return selected
    
    def _do_generate(self):
        """Generate the order document."""
        # Validate inputs
        order_number = self.edit_order_number.text().strip()
        if not order_number:
            QMessageBox.warning(self, "Предупреждение", "Введите номер приказа")
            return
        
        selected_listeners = self._get_selected_listeners()
        if not selected_listeners:
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы одного слушателя")
            return
        
        # Get order type
        order_type = self.combo_order_type.currentData()
        
        # Get dates
        order_date = self.edit_order_date.date().toPyDate()
        start_date = self.edit_start_date.date().toPyDate()
        end_date = self.edit_end_date.date().toPyDate()
        
        # Convert to datetime
        order_datetime = datetime.combine(order_date, datetime.min.time())
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.min.time())
        
        self.text_results.setVisible(True)
        self.text_results.clear()
        self.text_results.append(f"Генерация приказа «{self.ORDER_TYPES[order_type]}»...")
        self.text_results.append(f"Слушателей: {len(selected_listeners)}")
        QApplication.processEvents()
        
        self.btn_generate.setEnabled(False)
        
        try:
            file_path = self.generator.generate_order(
                order_type=order_type,
                listeners_data=selected_listeners,
                order_number=order_number,
                order_date=order_datetime,
                program_name=self.edit_program_name.text().strip(),
                stream_name=self.edit_stream_name.text().strip(),
                start_date=start_datetime,
                end_date=end_datetime,
                contract_date=self.edit_contract_date.text().strip(),
                hours=self.spin_hours.value(),
            )
            
            self.text_results.append(f"\n✓ Документ создан: {file_path}")
            
            # Register in journal
            try:
                assigned_num = self.journal_service.register_order(
                    journal_type=order_type,
                    title=f"Приказ {self.ORDER_TYPES[order_type]} №{order_number}",
                    program_name=self.edit_program_name.text().strip() or None,
                    executor="",  # Could add field if needed
                    order_date=order_date,
                    notes=f"Слушателей: {len(selected_listeners)}",
                    document_path=file_path,
                    order_number=int(order_number),
                )
                self.text_results.append(f"✓ Зарегистрирован в журнале под номером: {assigned_num}")
            except Exception as e:
                self.text_results.append(f"⚠ Предупреждение: не удалось зарегистрировать в журнале: {e}")
            
            QMessageBox.information(
                self, "Успех",
                f"Приказ создан и зарегистрирован в журнале!\n\nФайл: {Path(file_path).name}\nПапка: {self.generator.output_dir}"
            )
            
            if self.check_open_folder.isChecked():
                self._open_output_folder()
            
        except FileNotFoundError as e:
            self.text_results.append(f"\n✗ Ошибка: {e}")
            QMessageBox.critical(
                self, "Ошибка",
                f"Шаблон не найден!\n\n{e}\n\n"
                "Убедитесь, что файлы шаблонов находятся в папке templates/"
            )
        except Exception as e:
            self.text_results.append(f"\n✗ Ошибка: {e}")
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка генерации: {e}"
            )
        finally:
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
