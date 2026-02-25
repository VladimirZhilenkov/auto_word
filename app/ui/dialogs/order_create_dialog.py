"""
Dialog for creating order documents from the journal tab.
Allows selecting program, order type, listeners, and generates Word document.
"""

from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QGroupBox, QMessageBox,
    QComboBox, QListWidget, QListWidgetItem, QTextEdit,
    QCheckBox, QLineEdit, QDateEdit, QSpinBox,
    QAbstractItemView, QApplication, QFileDialog
)
import subprocess
import sys

from ...database.connection import DatabaseSession
from ...database.models import Listener, Program, ProgramListener
from ...services.document_generator import DocumentGenerator
from ...services.order_journal_service import OrderJournalService, ORDER_TYPE_LABELS


class OrderCreateDialog(QDialog):
    """
    Dialog for creating order documents with listeners from a selected program.
    Creates Word document and registers in order journal.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.generator = DocumentGenerator()
        self.journal_service = OrderJournalService()

        self._all_programs: List[Dict[str, Any]] = []
        self._program_listeners: List[Dict[str, Any]] = []

        self._setup_ui()
        self._load_programs()
        self._load_templates()
        self._update_next_number()

    def _setup_ui(self):
        self.setWindowTitle("Создание приказа")
        self.setMinimumWidth(850)
        self.setMinimumHeight(750)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Order type selection
        type_group = QGroupBox("Тип приказа")
        type_layout = QFormLayout(type_group)

        self.combo_order_type = QComboBox()
        for key, name in ORDER_TYPE_LABELS.items():
            self.combo_order_type.addItem(name, key)
        self.combo_order_type.currentIndexChanged.connect(self._update_next_number)
        type_layout.addRow("Тип:", self.combo_order_type)

        layout.addWidget(type_group)

        # Order details
        details_group = QGroupBox("Реквизиты приказа")
        details_layout = QFormLayout(details_group)

        # Order number
        number_layout = QVBoxLayout()
        self.edit_order_number = QLineEdit()
        self.edit_order_number.setPlaceholderText("Автоматически")
        number_layout.addWidget(self.edit_order_number)

        self.label_number_hint = QLabel("")
        self.label_number_hint.setStyleSheet("color: gray; font-size: 10px;")
        number_layout.addWidget(self.label_number_hint)
        details_layout.addRow("Номер приказа:", number_layout)

        # Order date
        self.edit_order_date = QDateEdit()
        self.edit_order_date.setCalendarPopup(True)
        self.edit_order_date.setDisplayFormat("dd.MM.yyyy")
        self.edit_order_date.setDate(QDate.currentDate())
        details_layout.addRow("Дата приказа:", self.edit_order_date)

        # Program type
        self.combo_program_type = QComboBox()
        self.combo_program_type.addItem("повышения квалификации", "повышения квалификации")
        self.combo_program_type.addItem("профессиональной переподготовки", "профессиональной переподготовки")
        details_layout.addRow("Вид программы:", self.combo_program_type)

        # Education form
        self.combo_education_form = QComboBox()
        self.combo_education_form.addItem("очная", "очная")
        self.combo_education_form.addItem("заочная", "заочная")
        self.combo_education_form.addItem("очно-заочная", "очно-заочная")
        details_layout.addRow("Форма обучения:", self.combo_education_form)

        # Education format
        self.combo_education_format = QComboBox()
        self.combo_education_format.setEditable(True)
        self.combo_education_format.addItem("", "")
        self.combo_education_format.addItem(
            "с применением электронного обучения",
            "с применением электронного обучения"
        )
        self.combo_education_format.addItem(
            "с применением дистанционных образовательных технологий",
            "с применением дистанционных образовательных технологий"
        )
        self.combo_education_format.addItem(
            "с применением электронного обучения и дистанционных образовательных технологий",
            "с применением электронного обучения и дистанционных образовательных технологий"
        )
        details_layout.addRow("Формат обучения:", self.combo_education_format)

        # Executor position
        self.combo_executor_position = QComboBox()
        self.combo_executor_position.setEditable(True)
        self.combo_executor_position.addItem(
            "Диспетчер факультета повышения квалификации и переподготовки судей, "
            "государственных гражданских служащих судов и Судебного департамента "
            "(ФПК судей и госслужащих судов)"
        )
        self.combo_executor_position.addItem(
            "Специалист по учебной работе I категории факультета повышения квалификации и переподготовки судей, "
            "государственных гражданских служащих судов и Судебного департамента "
            "(ФПК судей и госслужащих судов)"
        )
        details_layout.addRow("Должность исполнителя:", self.combo_executor_position)

        # Executor name
        self.edit_executor = QLineEdit()
        self.edit_executor.setPlaceholderText("ФИО исполнителя")
        details_layout.addRow("Имя исполнителя:", self.edit_executor)

        layout.addWidget(details_group)

        # Template selection
        tpl_group = QGroupBox("Шаблон документа")
        tpl_layout = QHBoxLayout(tpl_group)

        tpl_layout.addWidget(QLabel("Шаблон:"))
        self.combo_template = QComboBox()
        self.combo_template.setMinimumWidth(350)
        tpl_layout.addWidget(self.combo_template, stretch=1)

        self.btn_open_templates_folder = QPushButton("📂 Папка шаблонов")
        self.btn_open_templates_folder.clicked.connect(self._open_templates_folder)
        tpl_layout.addWidget(self.btn_open_templates_folder)

        self.btn_refresh_templates = QPushButton("🔄")
        self.btn_refresh_templates.setMaximumWidth(40)
        self.btn_refresh_templates.setToolTip("Обновить список шаблонов")
        self.btn_refresh_templates.clicked.connect(self._load_templates)
        tpl_layout.addWidget(self.btn_refresh_templates)

        self.btn_fix_templates = QPushButton("🔧 Исправить все шаблоны")
        self.btn_fix_templates.setToolTip(
            "Добавить цикл {% for listener in listeners %} во все шаблоны,\n"
            "где он отсутствует (необходим для корректной генерации)"
        )
        self.btn_fix_templates.clicked.connect(self._fix_all_templates)
        tpl_layout.addWidget(self.btn_fix_templates)

        layout.addWidget(tpl_group)

        # Program selection
        program_group = QGroupBox("Программа обучения")
        program_layout = QVBoxLayout(program_group)

        prog_row = QHBoxLayout()
        prog_row.addWidget(QLabel("Программа:"))
        self.combo_program = QComboBox()
        self.combo_program.setMinimumWidth(400)
        self.combo_program.currentIndexChanged.connect(self._on_program_changed)
        prog_row.addWidget(self.combo_program, stretch=1)
        program_layout.addLayout(prog_row)

        # Additional program info
        info_row = QHBoxLayout()
        self.edit_start_date = QDateEdit()
        self.edit_start_date.setCalendarPopup(True)
        self.edit_start_date.setDisplayFormat("dd.MM.yyyy")
        self.edit_start_date.setDate(QDate.currentDate())
        info_row.addWidget(QLabel("Дата начала:"))
        info_row.addWidget(self.edit_start_date)

        self.edit_end_date = QDateEdit()
        self.edit_end_date.setCalendarPopup(True)
        self.edit_end_date.setDisplayFormat("dd.MM.yyyy")
        self.edit_end_date.setDate(QDate.currentDate())
        info_row.addWidget(QLabel("Дата окончания:"))
        info_row.addWidget(self.edit_end_date)

        self.spin_hours = QSpinBox()
        self.spin_hours.setRange(1, 2000)
        self.spin_hours.setValue(16)
        info_row.addWidget(QLabel("Часов:"))
        info_row.addWidget(self.spin_hours)

        program_layout.addLayout(info_row)

        layout.addWidget(program_group)

        # Listeners selection
        listeners_group = QGroupBox("Слушатели")
        listeners_layout = QVBoxLayout(listeners_group)

        self.list_listeners = QListWidget()
        self.list_listeners.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_listeners.setMaximumHeight(200)
        listeners_layout.addWidget(self.list_listeners)

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

        self.check_register = QCheckBox("Зарегистрировать в журнале приказов")
        self.check_register.setChecked(True)
        options_layout.addWidget(self.check_register)

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

    def _load_programs(self):
        """Load programs into combobox."""
        self.combo_program.clear()
        self.combo_program.addItem("-- Выберите программу --", None)
        try:
            with DatabaseSession() as session:
                programs = session.query(Program).order_by(Program.program_name).all()
                for p in programs:
                    label = p.program_short_name or p.program_name
                    if len(label) > 80:
                        label = label[:80] + "..."
                    self.combo_program.addItem(label, p.id)
                    self._all_programs.append({
                        'id': p.id,
                        'program_name': p.program_name,
                        'program_short_name': p.program_short_name,
                        'training_period': p.training_period,
                        'training_duration': p.training_duration,
                        'program_volume': p.program_volume,
                        'education_form': p.education_form,
                        'education_format': p.education_format,
                    })
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки программ: {e}")

    def _on_program_changed(self):
        """Load listeners for selected program and auto-fill fields from program data."""
        self.list_listeners.clear()
        self._program_listeners.clear()

        prog_id = self.combo_program.currentData()
        if not prog_id:
            self._update_count()
            return

        # Auto-fill fields from program data
        self._fill_fields_from_program(prog_id)

        try:
            with DatabaseSession() as session:
                assocs = session.query(ProgramListener).filter(
                    ProgramListener.program_id == prog_id
                ).order_by(ProgramListener.order_number).all()

                for a in assocs:
                    listener = session.query(Listener).get(a.listener_id)
                    if listener:
                        listener_data = {
                            'id': listener.id,
                            'full_name': listener.full_name,
                            'last_name': listener.last_name,
                            'first_name': listener.first_name,
                            'middle_name': listener.middle_name,
                            'position': listener.position,
                            'workplace': listener.workplace,
                            'court_name': listener.workplace,
                            'region': listener.region,
                            'notes': listener.notes,
                        }
                        self._program_listeners.append(listener_data)

                        item = QListWidgetItem(
                            f"{listener.full_name} — "
                            f"{listener.position or 'Должность не указана'} "
                            f"({listener.workplace or 'Место работы не указано'})"
                        )
                        item.setData(Qt.UserRole, listener.id)
                        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                        item.setCheckState(Qt.Checked)  # Select all by default
                        self.list_listeners.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки слушателей: {e}")

        self._update_count()

    def _fill_fields_from_program(self, prog_id: int):
        """Auto-fill form fields from the selected program's data."""
        import re

        program_data = None
        for p in self._all_programs:
            if p['id'] == prog_id:
                program_data = p
                break
        if not program_data:
            return

        # 1) Форма обучения
        edu_form = (program_data.get('education_form') or '').strip()
        if edu_form:
            idx = self.combo_education_form.findData(edu_form)
            if idx >= 0:
                self.combo_education_form.setCurrentIndex(idx)

        # 2) Формат обучения
        edu_format = (program_data.get('education_format') or '').strip()
        if edu_format:
            idx = self.combo_education_format.findData(edu_format)
            if idx >= 0:
                self.combo_education_format.setCurrentIndex(idx)
            else:
                self.combo_education_format.setEditText(edu_format)

        # 3) Количество часов из объёма программы (парсим число)
        volume = (program_data.get('program_volume') or '').strip()
        if volume:
            match = re.search(r'(\d+)', volume)
            if match:
                hours = int(match.group(1))
                self.spin_hours.setValue(hours)

        # 4) Период обучения → даты начала и окончания
        period = (program_data.get('training_period') or '').strip()
        if period:
            self._parse_training_period(period)

    def _parse_training_period(self, period: str):
        """Try to parse training period string into start/end dates."""
        import re
        from datetime import datetime as _dt

        # Try patterns: "dd.mm.yyyy - dd.mm.yyyy", "dd.mm.yyyy по dd.mm.yyyy",
        #               "с dd.mm.yyyy по dd.mm.yyyy"
        pattern = r'(\d{2}[./]\d{2}[./]\d{4})\s*[-–—]\s*(\d{2}[./]\d{2}[./]\d{4})'
        match = re.search(pattern, period)
        if not match:
            pattern = r'с?\s*(\d{2}[./]\d{2}[./]\d{4})\s*(?:по|до)\s*(\d{2}[./]\d{2}[./]\d{4})'
            match = re.search(pattern, period)

        if match:
            date_str1, date_str2 = match.group(1), match.group(2)
            for fmt in ('%d.%m.%Y', '%d/%m/%Y'):
                try:
                    d1 = _dt.strptime(date_str1.replace('/', '.'), '%d.%m.%Y').date()
                    d2 = _dt.strptime(date_str2.replace('/', '.'), '%d.%m.%Y').date()
                    self.edit_start_date.setDate(QDate(d1.year, d1.month, d1.day))
                    self.edit_end_date.setDate(QDate(d2.year, d2.month, d2.day))
                    return
                except ValueError:
                    continue

    def _load_templates(self):
        """Load available .docx templates into combobox."""
        self.combo_template.clear()
        # First item: auto-select by order type
        self.combo_template.addItem("-- Автоматически по типу приказа --", None)
        templates = self.generator.get_available_templates()
        for tpl in templates:
            self.combo_template.addItem(tpl, tpl)

    def _open_templates_folder(self):
        """Open the templates folder in file manager."""
        folder = self.generator.templates_dir
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', str(folder)])
            elif sys.platform == 'win32':
                subprocess.run(['explorer', str(folder)])
            else:
                subprocess.run(['xdg-open', str(folder)])
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку: {exc}")

    def _update_next_number(self):
        """Fetch and display next order number."""
        order_type = self.combo_order_type.currentData()
        if not order_type:
            return
        try:
            next_num = self.journal_service.get_next_order_number(order_type)
            self.label_number_hint.setText(f"Следующий свободный номер: №{next_num}")
            if not self.edit_order_number.text().strip():
                self.edit_order_number.setText(str(next_num))
        except Exception:
            self.label_number_hint.setText("")

    def _select_all_listeners(self):
        for i in range(self.list_listeners.count()):
            self.list_listeners.item(i).setCheckState(Qt.Checked)

    def _deselect_all_listeners(self):
        for i in range(self.list_listeners.count()):
            self.list_listeners.item(i).setCheckState(Qt.Unchecked)

    def _update_count(self):
        count = sum(
            1 for i in range(self.list_listeners.count())
            if self.list_listeners.item(i).checkState() == Qt.Checked
        )
        self.label_count.setText(f"Выбрано: {count}")

    def _get_selected_listeners(self) -> List[Dict[str, Any]]:
        selected = []
        for i in range(self.list_listeners.count()):
            item = self.list_listeners.item(i)
            if item.checkState() == Qt.Checked:
                listener_id = item.data(Qt.UserRole)
                for l in self._program_listeners:
                    if l['id'] == listener_id:
                        selected.append(l)
                        break
        return selected

    def _do_generate(self):
        """Generate the order document."""
        # Validate
        order_number = self.edit_order_number.text().strip()
        if not order_number:
            QMessageBox.warning(self, "Предупреждение", "Введите номер приказа")
            return

        if not order_number.isdigit():
            QMessageBox.warning(self, "Предупреждение", "Номер приказа должен быть числом")
            return

        selected_listeners = self._get_selected_listeners()
        if not selected_listeners:
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы одного слушателя")
            return

        prog_id = self.combo_program.currentData()
        if not prog_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите программу обучения")
            return

        order_type = self.combo_order_type.currentData()
        order_type_label = ORDER_TYPE_LABELS.get(order_type, '')

        order_date = self.edit_order_date.date().toPyDate()
        start_date = self.edit_start_date.date().toPyDate()
        end_date = self.edit_end_date.date().toPyDate()

        order_datetime = datetime.combine(order_date, datetime.min.time())
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.min.time())

        # Get program name
        program_name = ""
        for p in self._all_programs:
            if p['id'] == prog_id:
                program_name = p.get('program_short_name') or p.get('program_name', '')
                break

        self.text_results.setVisible(True)
        self.text_results.clear()
        self.text_results.append(f"Генерация приказа «{order_type_label}»...")
        self.text_results.append(f"Программа: {program_name}")
        self.text_results.append(f"Слушателей: {len(selected_listeners)}")
        QApplication.processEvents()

        self.btn_generate.setEnabled(False)

        # Determine template
        selected_template = self.combo_template.currentData()  # None = auto

        # Collect extra context from new fields
        education_form = self.combo_education_form.currentData() or ''
        education_format = self.combo_education_format.currentText().strip()
        program_type = self.combo_program_type.currentData() or ''
        executor_position = self.combo_executor_position.currentText().strip()
        executor_name = self.edit_executor.text().strip()
        executor_full = f"{executor_position} {executor_name}".strip() if executor_position else executor_name

        # Get training_period directly from program data
        training_period = ''
        training_duration = ''
        for p in self._all_programs:
            if p['id'] == prog_id:
                training_period = p.get('training_period') or ''
                training_duration = p.get('training_duration') or ''
                break

        try:
            file_path = self.generator.generate_order(
                order_type=order_type,
                listeners_data=selected_listeners,
                order_number=order_number,
                order_date=order_datetime,
                program_name=program_name,
                start_date=start_datetime,
                end_date=end_datetime,
                hours=self.spin_hours.value(),
                education_form=education_form,
                education_format=education_format,
                template_name=selected_template,
                custom_context={
                    'order_type_label': order_type_label,
                    'program_type': program_type,
                    'program_id': prog_id,
                    'executor_position': executor_position,
                    'executor_name': executor_name,
                    'executor_full': executor_full,
                    'training_period': training_period,
                    'training_duration': training_duration,
                },
            )

            self.text_results.append(f"\n✓ Документ создан: {file_path}")

            # Register in journal
            if self.check_register.isChecked():
                try:
                    assigned_num = self.journal_service.register_order(
                        journal_type=order_type,
                        title=f"Приказ «{order_type_label}» №{order_number}",
                        program_id=prog_id,
                        program_name=program_name,
                        executor=executor_full,
                        order_date=order_date,
                        notes=f"Слушателей: {len(selected_listeners)}",
                        document_path=file_path,
                        order_number=int(order_number),
                    )
                    self.text_results.append(
                        f"✓ Зарегистрирован в журнале под номером: {assigned_num}"
                    )
                except Exception as e:
                    self.text_results.append(
                        f"⚠ Не удалось зарегистрировать в журнале: {e}"
                    )

            QMessageBox.information(
                self, "Успех",
                f"Приказ создан!\n\n"
                f"Файл: {Path(file_path).name}\n"
                f"Папка: {self.generator.output_dir}"
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
            QMessageBox.critical(self, "Ошибка", f"Ошибка генерации: {e}")
        finally:
            self.btn_generate.setEnabled(True)

    def _fix_all_templates(self):
        """Fix all templates by adding {% for listener in listeners %} loop."""
        reply = QMessageBox.question(
            self, "Исправление шаблонов",
            "Будет выполнено автоматическое исправление всех шаблонов:\n\n"
            "• Добавление цикла {% for listener in listeners %} в строки таблиц,\n"
            "  содержащие переменные listener/loop.\n\n"
            "Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        QApplication.processEvents()
        results = self.generator.fix_all_templates()

        if not results:
            QMessageBox.information(
                self, "Информация",
                "В папке templates/ нет шаблонов .docx"
            )
            return

        fixed = [r for r in results if r['status'] == 'fixed']
        already = [r for r in results if r['status'] == 'already_ok']
        no_vars = [r for r in results if r['status'] == 'no_vars']
        errors = [r for r in results if r['status'] == 'error']

        lines = []
        if fixed:
            lines.append(f"✅ Исправлено: {len(fixed)}")
            for r in fixed:
                lines.append(f"   • {r['name']}")
        if already:
            lines.append(f"\nℹ️ Уже содержат цикл: {len(already)}")
            for r in already:
                lines.append(f"   • {r['name']}")
        if no_vars:
            lines.append(f"\n⚠ Без переменных listener/loop: {len(no_vars)}")
            for r in no_vars:
                lines.append(f"   • {r['name']}")
        if errors:
            lines.append(f"\n❌ Ошибки: {len(errors)}")
            for r in errors:
                lines.append(f"   • {r['name']}: {r['message']}")

        msg = "\n".join(lines)
        QMessageBox.information(self, "Результат исправления шаблонов", msg)

        # Refresh templates list
        self._load_templates()

    def _open_output_folder(self):
        """Open the output folder in file manager."""
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
