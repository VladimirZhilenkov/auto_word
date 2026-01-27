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

        self.label_date = QLabel("<b>Дата обновления:</b> —")
        layout.addWidget(self.label_date)

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
        
        # Форматируем дату релиза
        published = result.get("published_at", "")
        if published:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                date_str = dt.strftime("%d.%m.%Y %H:%M")
            except:
                date_str = published[:10] if len(published) >= 10 else "—"
        else:
            date_str = "—"
        self.label_date.setText(f"<b>Дата релиза:</b> {date_str}")
        
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
            self.btn_update.setEnabled(True)
            return

        self.progress.setVisible(False)
        
        import subprocess
        import sys
        from pathlib import Path
        
        # На Windows создаём скрипт автообновления
        if sys.platform == 'win32':
            script_path = self.service.create_update_script(archive_path)
            if script_path:
                reply = QMessageBox.question(
                    self, "Обновление скачано",
                    "Обновление скачано и готово к установке.\n\n"
                    "Для установки программа будет закрыта, "
                    "файлы обновлены, и программа запустится снова.\n\n"
                    "Установить обновление сейчас?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    # Запускаем скрипт обновления и закрываем программу
                    subprocess.Popen(
                        ['cmd', '/c', 'start', '', script_path],
                        shell=False,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    # Закрываем приложение
                    from PyQt5.QtWidgets import QApplication
                    QApplication.quit()
                    return
                else:
                    # Пользователь отказался - показываем папку
                    folder = Path(archive_path).parent
                    subprocess.run(['explorer', '/select,', archive_path])
                    QMessageBox.information(
                        self, "Обновление отложено",
                        f"Файл обновления сохранён:\n{archive_path}\n\n"
                        "Вы можете установить его позже вручную."
                    )
        else:
            # На других ОС просто открываем папку
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
            try:
                if sys.platform == 'darwin':
                    subprocess.run(['open', str(folder)])
                else:
                    subprocess.run(['xdg-open', str(folder)])
            except Exception:
                pass
        
        self.btn_check.setEnabled(True)
        self.btn_update.setEnabled(True)
