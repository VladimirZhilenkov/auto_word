"""
Update service for checking, downloading, and applying application updates.
Uses GitHub Releases API for version checking.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib import request
from zipfile import ZipFile

from packaging import version


class UpdateService:
    """Update service using GitHub Releases."""
    
    GITHUB_REPO = "VladimirZhilenkov/auto_word"
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    
    # Имя файла для скачивания (должно совпадать с asset в Release)
    ASSET_NAME = "AutoWord.zip"

    def __init__(self, current_version: str = "0.0.0"):
        self.current_version = current_version.lstrip("v") if current_version else "0.0.0"
        self.app_dir = self._get_app_dir()

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
            with request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return {"available": False, "error": str(exc)}

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
            with request.urlopen(req) as resp, open(target_path, "wb") as f:
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
        """Apply update from a downloaded zip archive."""
        try:
            with ZipFile(update_path, "r") as zf:
                zf.extractall(self.app_dir)
            return True
        except Exception:
            return False

