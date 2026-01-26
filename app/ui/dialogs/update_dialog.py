"""
Update dialog that checks for updates and downloads them on demand.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QMessageBox,
)

from ...services.update_service import UpdateService


class UpdateDialog(QDialog):
    def __init__(self, parent=None, current_version: str = "0.0.0"):
        super().__init__(parent)
        self.service = UpdateService(current_version=current_version)
        self.available_version: Optional[str] = None
        self.download_url: Optional[str] = None

        self._setup_ui()
        self._check_updates()

    def _setup_ui(self):
        self.setWindowTitle("Проверка обновлений")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)

        self.label_current = QLabel(f"Текущая версия: {self.service.get_current_version()}")
        layout.addWidget(self.label_current)

        self.label_available = QLabel("Доступная версия: —")
        layout.addWidget(self.label_available)

        layout.addWidget(QLabel("Что нового:"))
        self.changelog = QTextEdit()
        self.changelog.setReadOnly(True)
        self.changelog.setPlaceholderText("Здесь будет changelog, если обновление найдено")
        layout.addWidget(self.changelog)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        btn_layout = QHBoxLayout()
        self.btn_update = QPushButton("Обновить сейчас")
        self.btn_update.clicked.connect(self._on_update)
        self.btn_update.setEnabled(False)

        self.btn_check = QPushButton("Проверить")
        self.btn_check.clicked.connect(self._check_updates)

        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_check)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _check_updates(self):
        self.btn_update.setEnabled(False)
        result = self.service.check_for_updates()
        if result.get("error"):
            QMessageBox.warning(self, "Ошибка", f"Не удалось проверить обновления: {result['error']}")
            self.label_available.setText("Доступная версия: —")
            return

        self.available_version = result.get("version")
        self.download_url = result.get("download_url")
        self.label_available.setText(f"Доступная версия: {self.available_version}")
        self.changelog.setPlainText(result.get("changelog") or "")

        if result.get("available"):
            self.btn_update.setEnabled(True)
            QMessageBox.information(self, "Обновление", "Доступна новая версия приложения.")
        else:
            QMessageBox.information(self, "Обновление", "У вас установлена последняя версия.")

    def _on_update(self):
        if not self.download_url:
            return

        self.btn_update.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        def _progress(value: int):
            self.progress.setValue(value)
            self.progress.repaint()

        try:
            archive_path = self.service.download_update(self.download_url, progress_callback=_progress)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось скачать обновление: {exc}")
            self.progress.setVisible(False)
            return

        ok = self.service.apply_update(archive_path)
        if ok:
            QMessageBox.information(self, "Готово", "Обновление успешно установлено. Перезапустите приложение.")
        else:
            QMessageBox.warning(self, "Внимание", "Не удалось применить обновление автоматически.")

        self.progress.setVisible(False)
