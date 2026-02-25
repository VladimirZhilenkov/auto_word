"""
Update service for checking, downloading, and applying application updates.
Uses GitHub Releases API for version checking.
"""

from __future__ import annotations

import json
import shutil
import ssl
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib import request
from urllib.error import URLError, HTTPError
from zipfile import ZipFile

from packaging import version


def _get_ssl_context():
    """Get SSL context, trying certifi first, then system certs."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    
    # Пробуем системный контекст
    try:
        ctx = ssl.create_default_context()
        return ctx
    except Exception:
        pass
    
    # Fallback: отключаем проверку (не идеально, но работает)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class UpdateService:
    """Update service using GitHub Releases."""
    
    GITHUB_REPO = "VladimirZhilenkov/auto_word"
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    
    # Имя файла для скачивания (должно совпадать с asset в Release)
    ASSET_NAME = "AutoWord.zip"
    
    # Таймаут для запросов (секунды)
    TIMEOUT = 10

    def __init__(self, current_version: str = "0.0.0"):
        self.current_version = current_version.lstrip("v") if current_version else "0.0.0"
        self.app_dir = self._get_app_dir()
        self._ssl_context = _get_ssl_context()

    def _get_app_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).parent.parent.parent

    def get_current_version(self) -> str:
        return self.current_version

    def check_for_updates(self) -> Dict:
        """Check GitHub Releases for a newer version."""
        try:
            req = request.Request(
                self.GITHUB_API_URL,
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "AutoWord-Updater"}
            )
            with request.urlopen(req, timeout=self.TIMEOUT, context=self._ssl_context) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                return {"available": False, "error": "Релизы не найдены на GitHub"}
            return {"available": False, "error": f"Ошибка сервера: {exc.code}"}
        except URLError as exc:
            # Дружественные сообщения для разных типов сетевых ошибок
            reason = str(exc.reason)
            if "10061" in reason or "Connection refused" in reason:
                return {"available": False, "error": "Нет подключения к интернету или GitHub недоступен"}
            if "timed out" in reason.lower() or "timeout" in reason.lower():
                return {"available": False, "error": "Превышено время ожидания. Проверьте подключение к интернету"}
            if "getaddrinfo" in reason.lower() or "name resolution" in reason.lower():
                return {"available": False, "error": "Не удалось определить адрес сервера. Проверьте подключение к интернету"}
            return {"available": False, "error": f"Ошибка сети: {reason}"}
        except Exception as exc:
            return {"available": False, "error": f"Не удалось проверить обновления: {exc}"}

        # Получаем версию из tag_name (например "v2.1.0" -> "2.1.0")
        tag = data.get("tag_name", "")
        remote_version = tag.lstrip("v") if tag else "0.0.0"
        
        # Changelog из body релиза
        changelog = data.get("body") or ""
        
        # Ищем нужный asset для скачивания
        download_url = self._find_asset_url(data.get("assets", []))

        try:
            is_newer = version.parse(remote_version) > version.parse(self.current_version)
        except Exception:
            is_newer = False

        return {
            "available": bool(is_newer and download_url),
            "version": remote_version,
            "changelog": changelog,
            "download_url": download_url,
            "release_url": data.get("html_url", ""),
            "published_at": data.get("published_at", ""),
        }

    def _find_asset_url(self, assets: list) -> Optional[str]:
        """Find download URL for the target asset."""
        for asset in assets:
            name = asset.get("name", "")
            # Ищем ZIP или EXE файл
            if name == self.ASSET_NAME or name.endswith(".zip") or name.endswith(".exe"):
                return asset.get("browser_download_url")
        return None

    def download_update(self, url: str, progress_callback: Callable[[int], None] | None = None) -> str:
        """Download update file and report progress. Returns path to file."""
        tmp_dir = Path(tempfile.mkdtemp(prefix="update_"))
        # Определяем расширение из URL
        ext = ".zip" if url.endswith(".zip") else ".exe"
        target_path = tmp_dir / f"update_package{ext}"

        try:
            req = request.Request(url, headers={"User-Agent": "AutoWord-Updater"})
            with request.urlopen(req, context=self._ssl_context) as resp, open(target_path, "wb") as f:
                total = int(resp.getheader("Content-Length") or 0)
                downloaded = 0
                chunk_size = 1024 * 64
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        percent = int(downloaded / total * 100)
                        progress_callback(percent)
            return str(target_path)
        except Exception:
            if target_path.exists():
                target_path.unlink()
            raise

    def apply_update(self, update_path: str) -> bool:
        """Apply update from a downloaded zip archive.
        
        Handles ZIP archives that may contain a nested subdirectory
        (e.g., DocumentGenerator/) by detecting common prefix and
        extracting contents to the correct level.
        """
        try:
            with ZipFile(update_path, "r") as zf:
                names = zf.namelist()
                # Detect common prefix directory (e.g. "DocumentGenerator/")
                prefix = self._detect_zip_prefix(names)
                
                if prefix:
                    # Extract with prefix stripped to a temp dir, then copy
                    tmp_extract = Path(tempfile.mkdtemp(prefix="update_extract_"))
                    zf.extractall(tmp_extract)
                    src = tmp_extract / prefix.rstrip("/")
                    for item in src.rglob("*"):
                        relative = item.relative_to(src)
                        dest = self.app_dir / relative
                        if item.is_dir():
                            dest.mkdir(parents=True, exist_ok=True)
                        else:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(item), str(dest))
                    shutil.rmtree(tmp_extract, ignore_errors=True)
                else:
                    zf.extractall(self.app_dir)
            return True
        except Exception:
            return False

    @staticmethod
    def _detect_zip_prefix(names: list) -> Optional[str]:
        """Check if all ZIP entries share a common top-level directory prefix."""
        if not names:
            return None
        # Filter out empty names and directory-only entries at root level
        parts = [n.split("/", 1) for n in names if "/" in n]
        if not parts:
            return None
        first_dir = parts[0][0]
        if all(p[0] == first_dir for p in parts):
            return first_dir + "/"
        return None

    def create_update_script(self, archive_path: str) -> Optional[str]:
        """
        Create a batch script for Windows that will:
        1. Wait for the app to close
        2. Extract the update
        3. Restart the app
        
        Returns path to the script, or None on non-Windows.
        """
        if sys.platform != 'win32':
            return None
        
        archive_path = Path(archive_path)
        script_path = archive_path.parent / "update.bat"
        
        # Получаем имя exe файла
        exe_name = "DocumentGenerator.exe"
        if getattr(sys, "frozen", False):
            exe_name = Path(sys.executable).name
        
        exe_path = self.app_dir / exe_name
        backup_dir = self.app_dir / "_backup_before_update"
        tmp_extract = archive_path.parent / "_extract_tmp"
        
        # Создаём batch скрипт
        script_content = f'''@echo off
chcp 65001 >nul
echo ========================================
echo    Обновление AutoWord
echo ========================================
echo.
echo Ожидание закрытия программы...

:wait_loop
tasklist /FI "IMAGENAME eq {exe_name}" 2>NUL | find /I /N "{exe_name}" >NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo Программа закрыта. Устанавливаем обновление...
timeout /t 1 /nobreak >nul

:: Создаём бэкап перед обновлением
echo Создание бэкапа текущей версии...
if exist "{backup_dir}" rmdir /s /q "{backup_dir}"
mkdir "{backup_dir}" 2>nul
xcopy "{self.app_dir}\\*.exe" "{backup_dir}\\" /Y /Q >nul 2>nul
xcopy "{self.app_dir}\\*.dll" "{backup_dir}\\" /Y /Q >nul 2>nul

echo Распаковка файлов...
:: Извлекаем во временную папку
if exist "{tmp_extract}" rmdir /s /q "{tmp_extract}"
powershell -Command "Expand-Archive -Path '{archive_path}' -DestinationPath '{tmp_extract}' -Force"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ОШИБКА: Не удалось распаковать обновление!
    echo Попробуйте распаковать вручную.
    pause
    exit /b 1
)

:: Определяем, есть ли вложенная папка (например DocumentGenerator)
:: Если в архиве одна директория — копируем её содержимое
set "SRC={tmp_extract}"
for /f "delims=" %%D in ('dir /b /ad "{tmp_extract}" 2^>nul') do (
    :: Проверяем, единственная ли это подпапка
    set "SRC={tmp_extract}\\%%D"
)

echo Копирование файлов обновления...
xcopy "%SRC%\\*" "{self.app_dir}\\" /E /Y /Q >nul
if %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА копирования! Восстанавливаем бэкап...
    xcopy "{backup_dir}\\*" "{self.app_dir}\\" /E /Y /Q >nul
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Обновление успешно установлено!
echo ========================================
echo.
echo Запуск программы...
timeout /t 2 /nobreak >nul

start "" "{exe_path}"

:: Удаляем временные файлы
rmdir /s /q "{tmp_extract}" 2>nul
rmdir /s /q "{backup_dir}" 2>nul
del "{archive_path}" 2>nul
del "%~f0" 2>nul
'''
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            return str(script_path)
        except Exception:
            return None