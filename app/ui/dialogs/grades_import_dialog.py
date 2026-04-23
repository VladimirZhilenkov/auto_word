"""
Dialog for importing grades from XLSX into ProgramListener.grade_info.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLabel, QPushButton, QFileDialog, QTextEdit,
    QMessageBox,
)

from ...database.connection import DatabaseSession
from ...database.models import Program
from ...services.grades_import_service import GradesImportService


class GradesImportDialog(QDialog):
    """Select program + XLSX file, parse and apply grades."""

    def __init__(self, parent=None, preselect_program_id: Optional[int] = None):
        super().__init__(parent)
        self.service = GradesImportService()
        self.preselect_program_id = preselect_program_id
        self._xlsx_path: Optional[str] = None
        self._setup_ui()
        self._load_programs()

    def _setup_ui(self):
        self.setWindowTitle("Импорт оценок из XLSX")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.combo_program = QComboBox()
        self.combo_program.setMinimumWidth(360)
        form.addRow("Программа:", self.combo_program)

        file_layout = QHBoxLayout()
        self.lbl_file = QLabel("Файл не выбран")
        self.lbl_file.setStyleSheet("color: gray;")
        self.btn_choose = QPushButton("Выбрать XLSX...")
        self.btn_choose.clicked.connect(self._choose_file)
        file_layout.addWidget(self.lbl_file, stretch=1)
        file_layout.addWidget(self.btn_choose)
        form.addRow("Файл с оценками:", file_layout)

        layout.addLayout(form)

        layout.addWidget(QLabel(
            "Формат файла: столбец C = email слушателя, ячейка H1 = 'Оценка/макс.балл',\n"
            "строки ниже — ФИО/оценка по каждому слушателю. Последняя строка 'Общее среднее' игнорируется."
        ))

        self.report = QTextEdit()
        self.report.setReadOnly(True)
        self.report.setMinimumHeight(180)
        layout.addWidget(self.report)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_apply = QPushButton("Импортировать")
        self.btn_apply.clicked.connect(self._do_import)
        self.btn_clear = QPushButton("Очистить оценки программы")
        self.btn_clear.clicked.connect(self._clear_grades)
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_apply)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

    def _load_programs(self):
        self.combo_program.clear()
        self.combo_program.addItem("-- Выберите программу --", None)
        try:
            with DatabaseSession() as session:
                for p in session.query(Program).order_by(Program.program_name):
                    label = p.program_short_name or (p.program_name[:60] if p.program_name else f'#{p.id}')
                    self.combo_program.addItem(label, p.id)
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить программы: {exc}")
        if self.preselect_program_id:
            idx = self.combo_program.findData(self.preselect_program_id)
            if idx >= 0:
                self.combo_program.setCurrentIndex(idx)

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл с оценками", "", "Excel (*.xlsx *.xlsm)"
        )
        if path:
            self._xlsx_path = path
            self.lbl_file.setText(Path(path).name)
            self.lbl_file.setStyleSheet("")

    def _do_import(self):
        prog_id = self.combo_program.currentData()
        if not prog_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите программу")
            return
        if not self._xlsx_path:
            QMessageBox.warning(self, "Предупреждение", "Выберите файл с оценками")
            return
        try:
            max_grade, grades = self.service.parse_file(self._xlsx_path)
            if max_grade is None or max_grade <= 0:
                QMessageBox.critical(
                    self, "Ошибка",
                    "Не удалось определить максимальный балл из ячейки H1 "
                    "(ожидается формат 'Оценка/15,00')."
                )
                return
            report = self.service.apply_grades_to_program(prog_id, max_grade, grades)

            lines = [f"Макс. балл: {max_grade}", f"Прочитано записей: {len(grades)}", ""]
            if report["matched"]:
                lines.append(f"✅ Сопоставлено ({len(report['matched'])}):")
                lines.extend(f"  • {r}" for r in report["matched"])
            if report["no_email_in_program"]:
                lines.append("")
                lines.append(f"⚠ В программе без email ({len(report['no_email_in_program'])}):")
                lines.extend(f"  • {r}" for r in report["no_email_in_program"])
            if report["unmatched_emails"]:
                lines.append("")
                lines.append(f"⚠ Не сопоставлены ({len(report['unmatched_emails'])}):")
                lines.extend(f"  • {r}" for r in report["unmatched_emails"])
            self.report.setPlainText("\n".join(lines))
            QMessageBox.information(
                self, "Готово",
                f"Импортировано оценок: {len(report['matched'])}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Ошибка импорта: {exc}")

    def _clear_grades(self):
        prog_id = self.combo_program.currentData()
        if not prog_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите программу")
            return
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить оценки у всех слушателей выбранной программы?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            count = self.service.clear_grades_for_program(prog_id)
            QMessageBox.information(self, "Готово", f"Очищено оценок: {count}")
            self.report.append(f"\nОчищено: {count}")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось очистить: {exc}")
