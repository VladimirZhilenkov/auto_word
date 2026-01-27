"""
Update dialog that checks for updates via GitHub Releases.
"""

from __future__ import annotations

import webbrowser
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
        self.release_url: Optional[str] = None

        self._setup_ui()
        self._check_updates()

    def _setup_ui(self):
        self.setWindowTitle("Проверка обновлений")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)

        self.label_current = QLabel(f"<b>Текущая версия:</b> {self.service.get_current_version()}")
        layout.addWidget(self.label_current)

        self.label_available = QLabel("<b>Доступная версия:</b> —")
        layout.addWidget(self.label_available)

        layout.addWidget(QLabel("<b>Что нового:</b>"))
        self.changelog = QTextEdit()
        self.changelog.setReadOnly(True)
        self.changelog.setPlaceholderText("Здесь будет changelog, если обновление найдено")
        self.changelog.setMinimumHeight(150)
        layout.addWidget(self.changelog)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        btn_layout = QHBoxLayout()
        
        self.btn_github = QPushButton("🔗 Открыть на GitHub")
        self.btn_github.clicked.connect(self._open_github)
        # Кнопка GitHub всегда видна для ручного скачивания
        
        self.btn_update = QPushButton("⬇️ Скачать обновление")
        self.btn_update.clicked.connect(self._on_update)
        self.btn_update.setEnabled(False)

        self.btn_check = QPushButton("🔄 Проверить")
        self.btn_check.clicked.connect(self._check_updates)

        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_github)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_check)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _check_updates(self):
        self.btn_update.setEnabled(False)
        self.label_available.setText("<b>Доступная версия:</b> проверка...")
        self.changelog.clear()
        
        # Force UI update
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        result = self.service.check_for_updates()
        
        if result.get("error"):
            error_msg = result['error']
            self.label_available.setText("<b>Доступная версия:</b> —")
            self.changelog.setPlainText(f"⚠️ {error_msg}\n\nПроверьте подключение к интернету или скачайте обновление вручную с GitHub.")
            return

        self.available_version = result.get("version")
        self.download_url = result.get("download_url")
        self.release_url = result.get("release_url")
        
        self.label_available.setText(f"<b>Доступная версия:</b> {self.available_version}")
        self.changelog.setPlainText(result.get("changelog") or "Нет описания")

        if result.get("available"):
            self.btn_update.setEnabled(True)
            self.btn_github.setVisible(True)
            QMessageBox.information(
                self, "Обновление доступно", 
                f"Доступна новая версия {self.available_version}!\n\n"
                "Вы можете скачать обновление автоматически или открыть страницу релиза на GitHub."
            )
        else:
            QMessageBox.information(self, "Обновление", "У вас установлена последняя версия.")

    def _open_github(self):
        """Open release page in browser."""
        if self.release_url:
            webbrowser.open(self.release_url)
        else:
            webbrowser.open(f"https://github.com/{self.service.GITHUB_REPO}/releases")

    def _on_update(self):
        if not self.download_url:
            return

        self.btn_update.setEnabled(False)
        self.btn_check.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        def _progress(value: int):
            self.progress.setValue(value)
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        try:
            archive_path = self.service.download_update(self.download_url, progress_callback=_progress)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось скачать обновление:\n{exc}")
            self.progress.setVisible(False)
            self.btn_check.setEnabled(True)
            return

        self.progress.setVisible(False)
        
        import subprocess
        import sys
        from pathlib import Path
        
        # Всегда открываем папку с файлом - пользователь сам заменит
        # (автоматическая замена не работает пока программа запущена)
        folder = Path(archive_path).parent
        
        QMessageBox.information(
            self, "Обновление скачано", 
            f"Файл обновления сохранён:\n{archive_path}\n\n"
            "Для установки:\n"
            "1. Закройте эту программу\n"
            "2. Распакуйте архив\n"
            "3. Замените старые файлы новыми\n"
            "4. Запустите программу"
        )
        
        # Открываем папку с файлом
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', str(folder)])
            elif sys.platform == 'win32':
                subprocess.run(['explorer', '/select,', archive_path])
            else:
                subprocess.run(['xdg-open', str(folder)])
        except Exception:
            pass
        
        self.btn_check.setEnabled(True)
